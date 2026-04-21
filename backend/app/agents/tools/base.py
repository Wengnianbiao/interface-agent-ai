"""AgentTool 基类 + ToolRegistry — Agent 的可插拔能力层"""

from abc import ABC, abstractmethod
from typing import Any
import logging

logger = logging.getLogger("interface-agent-tools")


class AgentTool(ABC):
    """
    Agent 工具基类。

    每个 Tool 代表 Agent 的一种外部交互能力：
    MCP 配置、Terminal 执行、未来的 RAG 检索等。
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """执行工具，返回结构化结果"""
        ...

    def __str__(self) -> str:
        return f"Tool({self.name})"

    def __repr__(self) -> str:
        return self.__str__()


class ToolRegistry:
    """
    工具注册表 — 管理所有可用的 AgentTool。

    应用启动时注册一次，所有请求共享。
    """

    def __init__(self):
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> "ToolRegistry":
        logger.info("注册工具: %s — %s", tool.name, tool.description)
        self._tools[tool.name] = tool
        return self

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)

    async def execute(self, name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"未找到工具: {name}"}
        try:
            return await tool.execute(parameters)
        except Exception as exc:
            logger.exception("工具 %s 执行失败", name)
            return {"error": str(exc)}

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_descriptions(self) -> str:
        if not self._tools:
            return "暂无可用工具"
        return "\n".join(
            f"- {t.name}: {t.description}" for t in self._tools.values()
        )
