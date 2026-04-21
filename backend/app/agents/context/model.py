"""AgentContext — 贯穿一次请求完整生命周期的上下文对象"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Message:
    """结构化消息，替代原来的字符串拼接"""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class AgentContext:
    """
    一次 Agent 请求的完整上下文。

    从请求进入到响应结束只有这一个对象在传递，
    每个 Stage 往里面填充自己负责的部分。
    """

    # --- 请求身份 ---
    request_id: str
    session_id: str
    user_id: int
    user_input: str
    created_at: datetime = field(default_factory=datetime.utcnow)

    # --- 上下文（ContextStage 填充） ---
    system_prompt: str = ""
    messages: list[Message] = field(default_factory=list)

    # --- Plan 阶段填充 ---
    task_route: str = ""
    plan: dict | None = None
    business_file: str | None = None
    business_context: str = ""
    jarvis_params: dict = field(default_factory=lambda: {"input": None, "output": None})

    # --- Resolve 阶段积累 ---
    step_results: list[dict] = field(default_factory=list)
    content_fragments: list[str] = field(default_factory=list)

    # --- Tool 调用记录 ---
    tool_results: list[dict] = field(default_factory=list)

    # --- 元信息（各阶段可自由写入，最终随 done 事件下发） ---
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def llm_input(self) -> str:
        """构建 LLM 输入：历史消息 + 当前问题（纯文本形式）"""
        if not self.messages:
            return self.user_input
        lines = ["以下是最近对话历史，请结合上下文回答："]
        for msg in self.messages:
            label = "用户" if msg.role == "user" else "助手"
            lines.append(f"{label}: {msg.content}")
        lines.append("")
        lines.append(f"当前用户问题: {self.user_input}")
        return "\n".join(lines)
