import json
import os
import re
import logging
from typing import Optional
from rich.console import Console
from langchain_openai import ChatOpenAI


def get_llm(console: Console):
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    api_key = os.getenv("LLM_API_KEY")
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
        console.print(
            f"[yellow]⚠️ LLM_OUTPUT_MAX_TOKENS={output_max_tokens} 超过模型输出上限，自动下调为 {provider_max_output_tokens}[/yellow]"
        )
        output_max_tokens = provider_max_output_tokens
    if not api_key:
        console.print("[red]❌ 错误：LLM_API_KEY 未设置[/red]")
        return None
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


def extract_json_text(text: str) -> str:
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if json_match:
        return json_match.group(1).strip()
    return text.strip()


def parse_json(text: str) -> tuple[Optional[dict], Optional[str]]:
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, str(exc)
