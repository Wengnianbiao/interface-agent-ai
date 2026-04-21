"""PlanResolveAgent — 上下文构建 → 思考流程 → 工具调用"""

import logging
from typing import AsyncGenerator

from backend.app.agents.context.builder import ContextBuilder
from backend.app.agents.context.model import AgentContext
from backend.app.agents.pipeline import AgentPipeline, PlanStage, ResolveStage
from backend.app.agents.task_routes import AUTO_CONFIG_ROUTE
from backend.app.agents.tools.base import ToolRegistry
from backend.app.chat.sse import SSEEvent, thinking, tool_call, done

logger = logging.getLogger("interface-agent")


class PlanResolveAgent:
    """
    Plan-and-Resolve Agent。

    三个职责分明的阶段：
    1. ContextBuilder — 准备上下文（prompt、历史、未来的 RAG/记忆）
    2. Pipeline(Plan → Resolve) — 核心思考流程
    3. ToolRegistry — Resolve 产出配置后按需调用工具（MCP、Terminal 等）
    """

    def __init__(self, tool_registry: ToolRegistry):
        self._context_builder = ContextBuilder()
        self._pipeline = (
            AgentPipeline()
            .add(PlanStage())
            .add(ResolveStage())
        )
        self._tools = tool_registry

    async def run(self, ctx: AgentContext) -> AsyncGenerator[SSEEvent, None]:
        # === 1. 构建上下文 ===
        yield thinking("正在分析您的需求...", phase="context")
        await self._context_builder.build(ctx)

        # === 2. 思考流程：Plan → Resolve ===
        async for event in self._pipeline.execute(ctx):
            yield event

        # === 3. 工具调用（基于 Resolve 的产出决定是否调用） ===
        async for event in self._execute_tools(ctx):
            yield event

        # === 4. 完成 ===
        yield done({
            "mode": ctx.metadata.get("mode", "generate"),
            "taskRoute": ctx.task_route,
            "businessFile": ctx.metadata.get("businessFile"),
        })

    async def _execute_tools(self, ctx: AgentContext) -> AsyncGenerator[SSEEvent, None]:
        """根据 Resolve 阶段的输出判断是否需要调用工具"""
        config = ctx.metadata.get("latestConfig")
        need_mcp = ctx.metadata.get("latestNeedMcp", False)
        mode = ctx.metadata.get("mode", "generate")

        should_call = (
            isinstance(config, dict)
            and config
            and (need_mcp or mode == "mcp" or ctx.task_route == AUTO_CONFIG_ROUTE)
        )
        if not should_call:
            return

        yield thinking("正在调用 MCP 工具...", phase="tool")
        result = await self._tools.execute("mcp", config)
        ctx.tool_results.append({
            "tool": "mcp",
            "payload": config,
            "result": result,
        })
        yield tool_call("mcp", config, result)
