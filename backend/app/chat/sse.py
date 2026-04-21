"""SSE事件定义 - Server-Sent Events 协议格式"""

from dataclasses import dataclass
from enum import Enum
import json
from typing import Any


class SSEEventType(str, Enum):
    """SSE事件类型"""
    THINKING = "thinking"       # 阶段状态通知（规划中、执行中...）
    PLAN = "plan"               # 规划结果
    CONTENT = "content"         # 大模型内容chunk（逐字输出）
    TOOL_CALL = "tool_call"     # 工具调用（MCP等）
    ERROR = "error"             # 错误
    DONE = "done"               # 完成


@dataclass
class SSEEvent:
    """单个SSE事件"""
    event: SSEEventType
    data: Any

    def encode(self) -> str:
        """编码为SSE协议格式，多行 data 按规范每行加 data: 前缀"""
        if isinstance(self.data, (dict, list)):
            data_str = json.dumps(self.data, ensure_ascii=False)
        else:
            data_str = str(self.data)
        data_lines = data_str.split("\n")
        data_part = "\n".join(f"data: {line}" for line in data_lines)
        return f"event: {self.event.value}\n{data_part}\n\n"

def thinking(message: str, phase: str = "init", step_no: int | None = None) -> SSEEvent:
    data: dict[str, Any] = {"message": message, "phase": phase}
    if step_no is not None:
        data["stepNo"] = step_no
    return SSEEvent(SSEEventType.THINKING, data)

def plan(plan_data: dict) -> SSEEvent:
    return SSEEvent(SSEEventType.PLAN, plan_data)

def content(text: str) -> SSEEvent:
    return SSEEvent(SSEEventType.CONTENT, text)

def tool_call(tool_name: str, payload: dict, result: dict | None = None) -> SSEEvent:
    return SSEEvent(SSEEventType.TOOL_CALL, {
        "tool": tool_name,
        "payload": payload,
        "result": result,
    })


def error(message: str) -> SSEEvent:
    return SSEEvent(SSEEventType.ERROR, {"message": message})


def done(metadata: dict | None = None) -> SSEEvent:
    return SSEEvent(SSEEventType.DONE, metadata or {})
