"""PlanStage — Plan 阶段：调用 LLM 生成任务规划 JSON"""

import logging
from typing import AsyncGenerator

from backend.app.agents.context.model import AgentContext
from backend.app.agents.context.loader import load_business_context_by_file
from backend.app.agents.llm import get_llm
from backend.app.agents.llm_chains import build_plan_chain, extract_plan_output, astream_llm_chunks
from backend.app.agents.pipeline.base import Stage
from backend.app.agents.task_routes import (
    QA_ROUTE, AUTO_CONFIG_ROUTE,
    normalize_task_route, normalize_resolve_steps,
)
from backend.app.chat.sse import SSEEvent, plan, thinking, error

logger = logging.getLogger("interface-agent-pipeline")


class PlanStage(Stage):
    """
    Plan 阶段。

    职责：
    1. 调用 LLM 生成任务规划 JSON（静默收集，不流式给前端）
    2. 解析 plan 输出，填充 ctx.plan / ctx.task_route
    3. 加载对应业务场景的上下文文档
    4. 向前端发送 plan 事件
    """

    async def run(self, ctx: AgentContext) -> AsyncGenerator[SSEEvent, None]:
        yield thinking("正在制定执行计划...", phase="plan")
        llm = get_llm()

        try:
            runnable, payload = build_plan_chain(llm, ctx.llm_input, ctx.system_prompt)
            plan_full_text = ""
            async for chunk in astream_llm_chunks(runnable, payload):
                plan_full_text += chunk

            logger.info("request_id=%s LLM plan 响应=%s", ctx.request_id, plan_full_text[:500])
            plan_result = extract_plan_output(plan_full_text)

            normalized_route = normalize_task_route(plan_result, "generate")
            plan_result["taskRoute"] = normalized_route
            plan_result["resolveSteps"] = normalize_resolve_steps(plan_result)
        except Exception as exc:
            logger.exception("request_id=%s Plan阶段失败: %s", ctx.request_id, exc)
            yield error(f"任务规划失败：{exc}")
            return

        ctx.plan = plan_result
        ctx.task_route = str(plan_result.get("taskRoute", ""))

        # 加载业务场景上下文
        business_file = (
            None if ctx.task_route == QA_ROUTE
            else plan_result.get("businessFile")
        )
        ctx.business_file = business_file
        ctx.business_context, ctx.jarvis_params, business_file_path = (
            load_business_context_by_file(business_file)
        )
        if business_file_path:
            ctx.metadata["businessFile"] = business_file_path

        yield plan({
            "taskRoute": ctx.task_route,
            "scenarioName": str(plan_result.get("scenarioName", "")),
            "objective": str(plan_result.get("objective", "")),
            "resolveSteps": plan_result.get("resolveSteps", []),
        })
