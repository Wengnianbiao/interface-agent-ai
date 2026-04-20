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
        """编码为SSE协议格式: event: xxx\ndata: xxx\n\n"""
        if isinstance(self.data, (dict, list)):
            data_str = json.dumps(self.data, ensure_ascii=False)
        else:
            data_str = str(self.data)
        return f"event: {self.event.value}\ndata: {data_str}\n\n"

def thinking(message: str) -> SSEEvent:
    return SSEEvent(SSEEventType.THINKING, {"message": message})

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
