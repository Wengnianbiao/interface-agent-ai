"""聊天业务编排层：构建 AgentContext → 执行 Pipeline → 持久化"""

import logging
import uuid
from typing import AsyncGenerator

from backend.app.auth import AUTH_ENABLED, AuthUser
from backend.app.chat.history import append_chat_pair
from backend.app.chat.sse import SSEEvent
from backend.app.agents.context.model import AgentContext
from backend.app.agents.plan_resolve_runner import PlanResolveAgent
from backend.app.agents.tools.base import ToolRegistry
from backend.app.agents.tools.mcp_client import MCPTool

logger = logging.getLogger("interface-agent-api")

# 应用级单例：ToolRegistry 启动时组装一次，所有请求共享
_tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry().register(MCPTool())
    return _tool_registry


def resolve_session_id(session_id: str | None) -> str:
    return session_id or str(uuid.uuid4())


async def execute_chat_stream(
    request_id: str,
    prompt: str,
    session_id: str,
    current_user: AuthUser,
) -> AsyncGenerator[str, None]:
    """
    核心业务编排：
    1. 构建 AgentContext
    2. Agent Pipeline 产出 SSE 事件流 → 编码为 SSE 协议文本
    3. 流结束后持久化
    """
    ctx = AgentContext(
        request_id=request_id,
        session_id=session_id,
        user_id=current_user.userId,
        user_input=prompt,
    )

    agent = PlanResolveAgent(get_tool_registry())

    async for event in agent.run(ctx):
        yield event.encode()

    if AUTH_ENABLED and current_user.userId > 0:
        full_response = "".join(ctx.content_fragments).strip()
        if full_response:
            append_chat_pair(current_user.userId, session_id, prompt, full_response)
