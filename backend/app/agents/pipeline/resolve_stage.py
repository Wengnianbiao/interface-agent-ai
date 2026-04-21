"""ResolveStage — Resolve 阶段：按 Plan 步骤逐步执行 LLM 调用，最终汇总输出"""

import logging
from typing import AsyncGenerator

from backend.app.agents.context.model import AgentContext
from backend.app.agents.llm import get_llm
from backend.app.agents.llm_chains import (
    build_resolve_chain,
    build_final_answer_chain,
    parse_resolve_output,
    astream_llm_chunks,
)
from backend.app.agents.pipeline.base import Stage
from backend.app.agents.task_routes import (
    AUTO_CONFIG_ROUTE,
    normalize_task_route,
    normalize_resolve_steps,
    build_fallback_resolved,
)
from backend.app.chat.sse import SSEEvent, thinking, content

logger = logging.getLogger("interface-agent-pipeline")


class ResolveStage(Stage):
    """
    Resolve 阶段。

    职责：
    1. 遍历 plan 中的 resolveSteps，静默执行每个 step
    2. 所有 step 完成后，基于汇总结果调用 LLM 生成最终回答
    3. 最终回答流式推送给前端
    """

    async def run(self, ctx: AgentContext) -> AsyncGenerator[SSEEvent, None]:
        if not ctx.plan:
            return

        llm = get_llm()
        resolved_mode = (
            "mcp" if ctx.task_route == AUTO_CONFIG_ROUTE else "generate"
        )
        ctx.metadata["mode"] = resolved_mode

        steps = normalize_resolve_steps(ctx.plan)
        latest_config: dict | None = None
        latest_need_mcp = False

        # === 1. 静默执行所有步骤，不向前端输出中间结果 ===
        for step in steps:
            step_name = step.get("stepName", "未命名步骤")
            step_no = step.get("stepNo", 0)
            yield thinking(f"执行步骤{step_no}：{step_name}", phase="resolve", step_no=step_no)

            step_mode = resolved_mode
            if bool(step.get("needMcp")):
                step_mode = "mcp"

            try:
                runnable, payload, step_route, need_mcp_default = build_resolve_chain(
                    llm=llm,
                    user_input=ctx.llm_input,
                    mode=step_mode,
                    plan_dict=ctx.plan,
                    system_prompt=ctx.system_prompt,
                    business_context=ctx.business_context,
                    jarvis_params=ctx.jarvis_params,
                    current_step=step,
                    previous_steps=ctx.step_results,
                )
                resolve_full_text = ""
                async for chunk in astream_llm_chunks(runnable, payload):
                    resolve_full_text += chunk

                step_resolved = parse_resolve_output(
                    resolve_full_text, step_route, need_mcp_default
                )
            except Exception as exc:
                logger.exception(
                    "request_id=%s Resolve步骤%d失败: %s",
                    ctx.request_id, step_no, exc,
                )
                step_resolved = build_fallback_resolved(
                    {"taskRoute": step.get("taskRoute", ctx.task_route)}, step_mode
                )

            if not isinstance(step_resolved, dict):
                step_resolved = build_fallback_resolved(
                    {"taskRoute": step.get("taskRoute", ctx.task_route)}, step_mode
                )

            normalized_step_route = normalize_task_route(
                {"taskRoute": step_resolved.get("taskRoute", step.get("taskRoute", ctx.task_route))},
                step_mode,
            )
            step_resolved["taskRoute"] = normalized_step_route

            ctx.step_results.append({
                "stepNo": step_no,
                "stepName": step_name,
                "taskRoute": normalized_step_route,
                "reply": str(step_resolved.get("reply", "")),
                "risk": str(step_resolved.get("risk", "")),
                "config": step_resolved.get("config", {}),
                "needMcp": bool(step_resolved.get("needMcp")),
            })

            yield thinking(f"步骤{step_no}已完成", phase="step_done", step_no=step_no)

            maybe_config = step_resolved.get("config")
            if isinstance(maybe_config, dict) and maybe_config:
                latest_config = maybe_config
                latest_need_mcp = bool(step_resolved.get("needMcp"))
            ctx.task_route = normalized_step_route

        ctx.metadata["latestConfig"] = latest_config
        ctx.metadata["latestNeedMcp"] = latest_need_mcp

        # === 2. 基于所有步骤结果，生成最终回答并流式输出 ===
        yield thinking("正在生成最终回答...", phase="answer")

        runnable, payload = build_final_answer_chain(
            llm=llm,
            user_input=ctx.llm_input,
            system_prompt=ctx.system_prompt,
            plan_dict=ctx.plan,
            step_results=ctx.step_results,
            business_context=ctx.business_context,
        )
        async for chunk in astream_llm_chunks(runnable, payload):
            yield content(chunk)
            ctx.content_fragments.append(chunk)
