"""Stage 基类 + AgentPipeline — 可配置的阶段管道"""

import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from backend.app.agents.context.model import AgentContext
from backend.app.chat.sse import SSEEvent, error

logger = logging.getLogger("interface-agent-pipeline")


class Stage(ABC):
    """
    Pipeline 阶段基类。

    每个 Stage 接收 AgentContext，执行一段逻辑，
    通过 yield 产出 SSE 事件，并将中间状态写入 ctx。
    """

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    async def run(self, ctx: AgentContext) -> AsyncGenerator[SSEEvent, None]:
        """执行阶段逻辑，yield SSE 事件"""
        ...
        yield  # type: ignore  # pragma: no cover


class AgentPipeline:
    """
    阶段管道 — 按顺序执行一组 Stage，汇聚 SSE 事件流。

    用法：
        pipeline = AgentPipeline().add(ContextStage()).add(PlanStage()).add(ResolveStage())
        async for event in pipeline.execute(ctx):
            yield event.encode()
    """

    def __init__(self):
        self._stages: list[Stage] = []

    def add(self, stage: Stage) -> "AgentPipeline":
        self._stages.append(stage)
        return self

    async def execute(self, ctx: AgentContext) -> AsyncGenerator[SSEEvent, None]:
        for stage in self._stages:
            logger.info("request_id=%s 进入阶段: %s", ctx.request_id, stage.name)
            try:
                async for event in stage.run(ctx):
                    yield event
            except Exception as exc:
                logger.exception(
                    "request_id=%s 阶段 %s 异常", ctx.request_id, stage.name
                )
                yield error(f"阶段 {stage.name} 执行失败：{exc}")
                return
