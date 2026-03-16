import json
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import typer
from rich.console import Console
from backend.app.agents.core import get_llm
from backend.app.agents.context_loader import (
    load_system_prompts,
    build_business_catalog,
    load_business_context_by_file,
)
from backend.app.agents.pipeline import plan_task, resolve_task
from backend.app.agents.mcp_client import execute_mcp_sync


QA_ROUTE = "规则问答"
EVALUATION_ROUTE = "可行性评估"
AUTO_CONFIG_ROUTE = "自动化配置"
SPI_ROUTE = "SPI 扩展"
CONFIG_OUTPUT_ROUTE = "配置生成"


def run_with_progress(console: Console, stream: bool, stage: str, fn):
    if not stream:
        return fn()
    start = time.time()
    heartbeat = 0
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        while not future.done():
            time.sleep(1)
            elapsed = int(time.time() - start)
            if elapsed >= heartbeat + 5:
                heartbeat = elapsed
                console.print(f"⏳ {stage}处理中，已等待 {elapsed}s...", markup=False, highlight=False)
        return future.result()


def build_fallback_plan(_input_text: str, resolved_mode: str, _catalog: list[dict]) -> dict:
    return {
        "taskRoute": CONFIG_OUTPUT_ROUTE,
        "scenarioName": "兜底模式",
        "businessFile": "",
        "objective": "返回稳定兜底结果",
        "needMcp": resolved_mode == "mcp",
        "shouldAskUser": False,
    }


def normalize_task_route(plan: dict, resolved_mode: str) -> str:
    plan_route = str(plan.get("taskRoute", "")).strip()
    if plan_route in {QA_ROUTE, EVALUATION_ROUTE, AUTO_CONFIG_ROUTE, SPI_ROUTE, CONFIG_OUTPUT_ROUTE}:
        return plan_route
    if resolved_mode == "mcp":
        return AUTO_CONFIG_ROUTE
    return CONFIG_OUTPUT_ROUTE


def build_fallback_resolved(_user_input: str, plan: dict, resolved_mode: str) -> dict:
    task_route = normalize_task_route(plan, resolved_mode)
    if task_route == AUTO_CONFIG_ROUTE:
        reply = (
            "【结论】\n- 当前请求可继续生成自动化配置。\n\n"
            "【说明】\n- 当前返回为兜底结果，请补充更完整的三方入参与返参示例后再生成配置。"
        )
    elif task_route == SPI_ROUTE:
        reply = (
            "【SPI结论】\n- 该场景可能涉及扩展能力。\n\n"
            "【下一步】\n- 请补充协议、鉴权、签名/加解密规则，我将给出完整 SPI 方案。"
        )
    elif task_route == QA_ROUTE:
        reply = (
            "【规则问答】\n- 我会优先解释框架规则与参数映射方式。\n\n"
            "【建议】\n- 如需输出配置 JSON，请补充具体业务场景与三方入参/返参样例。"
        )
    elif task_route == EVALUATION_ROUTE:
        reply = (
            "【可行性评估】\n- 我会先判定可配置化、SPI扩展或不支持。\n\n"
            "【建议】\n- 请补充三方接口文档或完整出入参样例，评估会更准确。"
        )
    else:
        reply = (
            "【结论】\n- 这是配置生成场景。\n\n"
            "【说明】\n- 我会输出结构化 JSON 配置，并给出校验建议。"
        )
    return {
        "shouldDisplay": True,
        "taskRoute": task_route,
        "reply": reply,
        "needMcp": False,
        "config": {},
        "risk": "兜底结果，建议补充完整接口样例后再次生成。",
    }


def run_planning_stage(
    console: Console,
    llm,
    input_text: str,
    stream: bool,
) -> tuple[dict, str, str, dict, Optional[str]]:
    resolved_mode = "generate"
    catalog = build_business_catalog()
    if stream:
        console.print("🔎 正在识别任务与业务场景...", markup=False, highlight=False)
    plan = run_with_progress(
        console=console,
        stream=stream,
        stage="任务规划",
        fn=lambda: plan_task(llm, input_text, catalog, debug_prompt=True),
    )
    if not isinstance(plan, dict):
        plan = build_fallback_plan(input_text, resolved_mode, catalog)
    normalized_route = normalize_task_route(plan, resolved_mode)
    plan["taskRoute"] = normalized_route
    if stream:
        console.print(
            f"✅ 规划完成：任务={plan.get('taskRoute', '未知')} | 场景={plan.get('scenarioName', '未知')} | 文档={plan.get('businessFile', '无')}",
            markup=False,
            highlight=False,
        )
    if normalized_route == AUTO_CONFIG_ROUTE:
        resolved_mode = "mcp"
    business_file = None if normalized_route == QA_ROUTE else plan.get("businessFile")
    business_context, jarvis_params, business_file_path = load_business_context_by_file(business_file)
    return plan, resolved_mode, business_context, jarvis_params, business_file_path


def run_execution_stage(
    console: Console,
    llm,
    input_text: str,
    stream: bool,
    plan: dict,
    resolved_mode: str,
    system_prompt: str,
    business_context: str,
    jarvis_params: dict,
) -> tuple[dict, dict | None, dict | None, str, str]:
    if stream:
        console.print("🧠 正在生成最终结果...", markup=False, highlight=False)
    resolved = run_with_progress(
        console=console,
        stream=stream,
        stage="结果生成",
        fn=lambda: resolve_task(
            llm=llm,
            user_input=input_text,
            mode=resolved_mode,
            plan=plan,
            system_prompt=system_prompt,
            business_context=business_context,
            jarvis_params=jarvis_params,
        ),
    )
    if not isinstance(resolved, dict):
        resolved = build_fallback_resolved(input_text, plan, resolved_mode)
    config = resolved.get("config") if isinstance(resolved, dict) else None
    need_mcp = bool(resolved.get("needMcp")) if isinstance(resolved, dict) else False
    task_route = plan.get("taskRoute", "")
    if isinstance(resolved, dict):
        task_route = normalize_task_route({"taskRoute": resolved.get("taskRoute", task_route)}, resolved_mode)
        resolved["taskRoute"] = task_route
    mcp_results = None
    if isinstance(config, dict) and (need_mcp or resolved_mode == "mcp" or task_route == AUTO_CONFIG_ROUTE):
        try:
            mcp_results = execute_mcp_sync(config)
        except Exception as exc:
            mcp_results = {"error": str(exc)}
    should_display = bool(resolved.get("shouldDisplay", True)) if isinstance(resolved, dict) else True
    reply = resolved.get("reply", "") if isinstance(resolved, dict) else ""
    if not reply:
        reply = "【结果】\n- 已完成任务执行，但未生成可展示内容。"
    if not should_display:
        reply = "【结果】\n- 当前结果不建议直接展示给用户，请补充输入信息后重试。"
    if mcp_results:
        reply = f"{reply}\n\n【MCP执行结果】\n```json\n{json.dumps(mcp_results, ensure_ascii=False, indent=2)}\n```"
    if stream:
        console.print(reply, markup=False, highlight=False)
    return resolved, config, mcp_results, task_route, reply


def run_plan_execute(console: Console, input_text: str, stream: bool) -> dict:
    llm = get_llm(console)
    if not llm:
        raise typer.Exit(1)
    system_prompt = load_system_prompts()
    plan, resolved_mode, business_context, jarvis_params, business_file_path = run_planning_stage(
        console=console,
        llm=llm,
        input_text=input_text,
        stream=stream,
    )
    resolved, config, mcp_results, task_route, reply = run_execution_stage(
        console=console,
        llm=llm,
        input_text=input_text,
        stream=stream,
        plan=plan,
        resolved_mode=resolved_mode,
        system_prompt=system_prompt,
        business_context=business_context,
        jarvis_params=jarvis_params,
    )
    return {
        "mode": resolved_mode,
        "taskRoute": task_route,
        "plan": plan,
        "businessFile": business_file_path,
        "resolved": resolved,
        "config": config,
        "mcpResults": mcp_results,
        "display": reply,
    }
