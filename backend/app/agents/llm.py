import os
import logging
from langchain_openai import ChatOpenAI

logger = logging.getLogger("interface-agent-llm")


class LLMConfigError(Exception):
    """LLM配置错误"""
    pass


def get_llm() -> ChatOpenAI:
    """
    构造LLM客户端。
    配置来源：环境变量。配置非法时抛出 LLMConfigError。
    """
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise LLMConfigError("LLM_API_KEY 未设置")

    model_id = os.getenv("LLM_MODEL_ID", "qwen3.5-plus")
    base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    try:
        output_max_tokens = int(os.getenv("LLM_OUTPUT_MAX_TOKENS", "16384"))
    except ValueError:
        output_max_tokens = 16384
    try:
        provider_max_output_tokens = int(os.getenv("LLM_PROVIDER_MAX_OUTPUT_TOKENS", "64000"))
    except ValueError:
        provider_max_output_tokens = 64000

    if output_max_tokens <= 0:
        output_max_tokens = 16384
    if provider_max_output_tokens <= 0:
        provider_max_output_tokens = 64000
    if output_max_tokens > provider_max_output_tokens:
        logger.warning(
            "LLM_OUTPUT_MAX_TOKENS=%d 超过模型输出上限，自动下调为 %d",
            output_max_tokens, provider_max_output_tokens,
        )
        output_max_tokens = provider_max_output_tokens

    try:
        timeout_seconds = int(os.getenv("LLM_TIMEOUT_SECONDS", "180"))
    except ValueError:
        timeout_seconds = 180
    try:
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))
    except ValueError:
        max_retries = 2

    return ChatOpenAI(
        model=model_id,
        base_url=base_url,
        api_key=api_key,
        temperature=0.2,
        max_tokens=output_max_tokens,
        timeout=timeout_seconds,
        max_retries=max_retries,
    )
