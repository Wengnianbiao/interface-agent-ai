import json
import os
import re
from typing import Optional
from rich.console import Console
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


def get_llm(console: Console):
    api_key = os.getenv("LLM_API_KEY")
    model_id = os.getenv("LLM_MODEL_ID", "qwen3.5-plus")
    base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    if not api_key:
        console.print("[red]❌ 错误：LLM_API_KEY 未设置[/red]")
        return None
    return ChatOpenAI(
        model=model_id,
        base_url=base_url,
        api_key=api_key,
        temperature=0.2,
        max_tokens=4000,
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

