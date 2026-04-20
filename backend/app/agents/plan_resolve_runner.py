"""Plan-and-Resolve Agent - 产出 SSE 事件流的 async generator"""

import json
import logging
from typing import AsyncGenerator

from backend.app.agents.llm import get_llm
from backend.app.agents.context import (
    load_plan_system_prompts,
    load_business_context_by_file,
)
from backend.app.agents.pipeline import (
    build_plan_chain,
    build_resolve_chain,
    extract_plan_output,
    parse_resolve_output,
    astream_llm_chunks,
)
from backend.app.agents.tools import execute_mcp_sync
from backend.app.chat.sse import SSEEvent, thinking, plan, content, tool_call, error, done

logger = logging.getLogger("interface-agent")

# 路由常量
QA_ROUTE = "规则问答"
EVALUATION_ROUTE = "可行性评估"
AUTO_CONFIG_ROUTE = "自动化配置"
SPI_ROUTE = "SPI扩展"
CONFIG_OUTPUT_ROUTE = "配置生成"


def normalize_task_route(plan_dict: dict, resolved_mode: str) -> str:
    plan_route = str(plan_dict.get("taskRoute", "")).strip()
    if plan_route in {QA_ROUTE, EVALUATION_ROUTE, AUTO_CONFIG_ROUTE, SPI_ROUTE, CONFIG_OUTPUT_ROUTE}:
        return plan_route
    if resolved_mode == "mcp":
        return AUTO_CONFIG_ROUTE
    return CONFIG_OUTPUT_ROUTE


def normalize_resolve_steps(plan_dict: dict) -> list[dict]:
    raw_steps = plan_dict.get("resolveSteps")
    normalized: list[dict] = []
    if isinstance(raw_steps, list):
        for idx, item in enumerate(raw_steps):
            if not isinstance(item, dict):
                continue
            normalized.append({
                "stepNo": idx + 1,
                "stepName": str(item.get("stepName") or f"步骤{idx + 1}").strip(),
                "objective": str(item.get("objective") or plan_dict.get("objective") or "完成用户请求").strip(),
                "expectedOutput": str(item.get("expectedOutput") or "给出明确结果").strip(),
                "taskRoute": str(item.get("taskRoute") or plan_dict.get("taskRoute") or CONFIG_OUTPUT_ROUTE).strip(),
                "needMcp": bool(item.get("needMcp")),
            })
    if normalized:
        return normalized
    return [{
        "stepNo": 1,
        "stepName": "输出结果",
        "objective": str(plan_dict.get("objective") or "完成用户请求"),
        "expectedOutput": "给出明确结论",
        "taskRoute": str(plan_dict.get("taskRoute") or CONFIG_OUTPUT_ROUTE),
        "needMcp": bool(plan_dict.get("needMcp")),
    }]


def build_fallback_resolved(plan_dict: dict, resolved_mode: str) -> dict:
    task_route = normalize_task_route(plan_dict, resolved_mode)
    fallback_replies = {
        AUTO_CONFIG_ROUTE: "【结论】\n- 当前请求可继续生成自动化配置。\n\n【说明】\n- 当前返回为兜底结果，请补充更完整的三方入参与返参示例后再生成配置。",
        SPI_ROUTE: "【SPI结论】\n- 该场景可能涉及扩展能力。\n\n【下一步】\n- 请补充协议、鉴权、签名/加解密规则，我将给出完整 SPI 方案。",
        QA_ROUTE: "【规则问答】\n- 我会优先解释框架规则与参数映射方式。\n\n【建议】\n- 如需输出配置 JSON，请补充具体业务场景与三方入参/返参样例。",
        EVALUATION_ROUTE: "【可行性评估】\n- 我会先判定可配置化、SPI扩展或不支持。\n\n【建议】\n- 请补充三方接口文档或完整出入参样例，评估会更准确。",
    }
    reply = fallback_replies.get(task_route, "【结论】\n- 这是配置生成场景。\n\n【说明】\n- 我会输出结构化 JSON 配置，并给出校验建议。")
    return {
        "shouldDisplay": True,
        "taskRoute": task_route,
        "reply": reply,
        "needMcp": False,
        "config": {},
        "risk": "兜底结果，建议补充完整接口样例后再次生成。",
    }


class PlanResolveAgent:
    """Plan-and-Resolve Agent，async generator 产出 SSE 事件流"""

    def __init__(self):
        self.llm = get_llm()
        self.system_prompt = load_plan_system_prompts()

    async def run(self, input_text: str) -> AsyncGenerator[SSEEvent, None]:
        """对外唯一入口，yield SSE 事件"""
        # === Plan 阶段（JSON输出，静默收集，不流式给前端） ===
        yield thinking("正在分析任务...")

        try:
            runnable, payload = build_plan_chain(self.llm, input_text, self.system_prompt)
            plan_full_text = ""
            async for chunk in astream_llm_chunks(runnable, payload):
                plan_full_text += chunk
            logger.info("LLM plan 响应=%s", plan_full_text)
            plan_result = extract_plan_output(plan_full_text)
            normalized_route = normalize_task_route(plan_result, "generate")
            plan_result["taskRoute"] = normalized_route
            plan_result["resolveSteps"] = normalize_resolve_steps(plan_result)
        except Exception as exc:
            logger.exception("Plan阶段失败: %s", exc)
            yield error(f"任务规划失败：{exc}")
            yield done()
            return

        # 发送 plan 事件
        plan_payload = {
            "taskRoute": str(plan_result.get("taskRoute", "")),
            "scenarioName": str(plan_result.get("scenarioName", "")),
            "objective": str(plan_result.get("objective", "")),
            "resolveSteps": plan_result.get("resolveSteps", []),
        }
        yield plan(plan_payload)

        # === Resolve 阶段（JSON输出，收集完解析后只把 reply 流式给前端） ===
        resolved_mode = "mcp" if str(plan_result.get("taskRoute", "")).strip() == AUTO_CONFIG_ROUTE else "generate"
        business_file = None if str(plan_result.get("taskRoute", "")).strip() == QA_ROUTE else plan_result.get("businessFile")
        business_context, jarvis_params, business_file_path = load_business_context_by_file(business_file)

        steps = normalize_resolve_steps(plan_result)
        step_results: list[dict] = []
        latest_config: dict | None = None
        latest_need_mcp = False
        task_route = str(plan_result.get("taskRoute", ""))

        for step in steps:
            step_name = step.get("stepName", "未命名步骤")
            step_no = step.get("stepNo", 0)
            yield thinking(f"执行步骤{step_no}：{step_name}")

            step_mode = resolved_mode
            if bool(step.get("needMcp")):
                step_mode = "mcp"

            try:
                runnable, payload, step_route, need_mcp_default = build_resolve_chain(
                    llm=self.llm,
                    user_input=input_text,
                    mode=step_mode,
                    plan=plan_result,
                    system_prompt=self.system_prompt,
                    business_context=business_context,
                    jarvis_params=jarvis_params,
                    current_step=step,
                    previous_steps=step_results,
                )
                resolve_full_text = ""
                async for chunk in astream_llm_chunks(runnable, payload):
                    resolve_full_text += chunk
                step_resolved = parse_resolve_output(resolve_full_text, step_route, need_mcp_default)
                # 只把解析后的 reply 发送给前端
                reply_text = str(step_resolved.get("reply", ""))
                if reply_text:
                    yield content(reply_text)
            except Exception as exc:
                logger.exception("Resolve步骤%d失败: %s", step_no, exc)
                step_resolved = build_fallback_resolved(
                    {"taskRoute": step.get("taskRoute", task_route)}, step_mode
                )

            if not isinstance(step_resolved, dict):
                step_resolved = build_fallback_resolved(
                    {"taskRoute": step.get("taskRoute", task_route)}, step_mode
                )

            normalized_step_route = normalize_task_route(
                {"taskRoute": step_resolved.get("taskRoute", step.get("taskRoute", task_route))},
                step_mode,
            )
            step_resolved["taskRoute"] = normalized_step_route

            step_result_summary = {
                "stepNo": step_no,
                "stepName": step_name,
                "taskRoute": normalized_step_route,
                "reply": str(step_resolved.get("reply", "")),
                "risk": str(step_resolved.get("risk", "")),
            }
            step_results.append(step_result_summary)

            maybe_config = step_resolved.get("config")
            if isinstance(maybe_config, dict) and maybe_config:
                latest_config = maybe_config
                latest_need_mcp = bool(step_resolved.get("needMcp"))
            task_route = normalized_step_route

        # === MCP 工具调用 ===
        resolved = self._build_final_reply(steps, step_results, plan_result, resolved_mode, task_route, latest_config, latest_need_mcp)
        config = resolved.get("config") if isinstance(resolved, dict) else None
        need_mcp = bool(resolved.get("needMcp")) if isinstance(resolved, dict) else False
        if isinstance(config, dict) and (need_mcp or resolved_mode == "mcp" or task_route == AUTO_CONFIG_ROUTE):
            yield thinking("正在调用MCP工具...")
            try:
                mcp_results = execute_mcp_sync(config)
            except Exception as exc:
                mcp_results = {"error": str(exc)}
            yield tool_call("mcp", config, mcp_results)

        # === 完成 ===
        yield done({
            "mode": resolved_mode,
            "taskRoute": task_route,
            "businessFile": business_file_path if business_file else None,
        })

    @staticmethod
    def _build_final_reply(
        steps: list[dict], step_results: list[dict], plan_result: dict,
        resolved_mode: str, task_route: str,
        latest_config: dict | None, latest_need_mcp: bool,
    ) -> dict:
        """组装最终结果 dict（用于 MCP 判断等）"""
        if not step_results:
            return build_fallback_resolved(plan_result, resolved_mode)
        return {
            "shouldDisplay": True,
            "taskRoute": task_route,
            "needMcp": latest_need_mcp,
            "config": latest_config or {},
            "risk": "；".join([r["risk"] for r in step_results if r.get("risk")]),
            "stepResults": step_results,
        }
