"""聊天业务编排层：上下文构建、Agent调用、历史持久化"""

import logging
import uuid
from typing import AsyncGenerator

from backend.app.auth import AUTH_ENABLED, AuthUser
from backend.app.chat.history import append_chat_pair, get_session_history
from backend.app.chat.sse import SSEEvent, SSEEventType
from backend.app.agents.plan_resolve_runner import PlanResolveAgent

logger = logging.getLogger("interface-agent-api")

MAX_REQUEST_HISTORY = 10


def resolve_session_id(session_id: str | None) -> str:
    return session_id or str(uuid.uuid4())


def load_history(user: AuthUser, session_id: str) -> list[dict[str, str]]:
    """加载会话历史（认证关闭或匿名用户时返回空）"""
    if AUTH_ENABLED and user.userId > 0:
        return get_session_history(user.userId, session_id, MAX_REQUEST_HISTORY)
    return []


def build_contextual_input(prompt: str, history: list[dict[str, str]]) -> str:
    """将最近对话历史拼接为上下文输入"""
    if not history:
        return prompt
    lines = ["以下是最近对话历史，请结合上下文回答："]
    for item in history:
        role_text = "用户" if item["role"] == "user" else "助手"
        lines.append(f"{role_text}: {item['content']}")
    lines.append("")
    lines.append(f"当前用户问题: {prompt}")
    return "\n".join(lines)


async def execute_chat_stream(
    request_id: str,
    prompt: str,
    session_id: str,
    current_user: AuthUser,
) -> AsyncGenerator[str, None]:
    """
    核心业务编排：
    1. 加载历史 → 拼接上下文
    2. Agent 产出 SSE 事件流 → 编码为 SSE 协议文本
    3. 收集 content 事件用于持久化
    """
    history = load_history(current_user, session_id)
    input_text = build_contextual_input(prompt, history)

    logger.info("request_id=%s 用户输入=%s", request_id, input_text.replace("\n", " ")[:200])

    agent = PlanResolveAgent()
    content_fragments: list[str] = []

    async for event in agent.run(input_text):
        # 收集 content 事件用于持久化
        if event.event == SSEEventType.CONTENT:
            content_fragments.append(str(event.data))

        # 编码为 SSE 协议文本发送给前端
        yield event.encode()

    # 流结束，持久化
    if AUTH_ENABLED and current_user.userId > 0:
        full_response = "".join(content_fragments).strip()
        if full_response:
            append_chat_pair(current_user.userId, session_id, prompt, full_response)
