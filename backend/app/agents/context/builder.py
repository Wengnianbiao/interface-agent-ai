"""ContextBuilder — 构建 AgentContext 的上下文数据，不是流水线阶段"""

import logging

from backend.app.auth import AUTH_ENABLED
from backend.app.chat.history import get_session_history
from backend.app.agents.context.loader import load_plan_system_prompts
from backend.app.agents.context.model import AgentContext, Message

logger = logging.getLogger("interface-agent-context")

MAX_HISTORY_MESSAGES = 10


class ContextBuilder:
    """
    上下文构造器。

    负责在 Agent 执行前将所有"已知信息"填充到 AgentContext 上：
    - 系统提示词
    - 对话历史

    它不是 Pipeline 的一个 Stage，而是 Agent.run() 的前置准备步骤。
    未来加 RAG / 长期记忆，在这里追加即可。
    """

    async def build(self, ctx: AgentContext) -> None:
        ctx.system_prompt = load_plan_system_prompts()

        if AUTH_ENABLED and ctx.user_id > 0:
            rows = get_session_history(ctx.user_id, ctx.session_id, MAX_HISTORY_MESSAGES)
            for row in rows:
                ctx.messages.append(Message(role=row["role"], content=row["content"]))

        logger.info(
            "request_id=%s 上下文构建完成: system_prompt=%d字, history=%d条",
            ctx.request_id, len(ctx.system_prompt), len(ctx.messages),
        )
