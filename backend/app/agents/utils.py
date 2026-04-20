"""Agent通用工具函数"""

import json
import re
from typing import Optional


def extract_json_text(text: str) -> str:
    """从LLM响应中提取JSON文本（剥离markdown代码块包裹）"""
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if json_match:
        return json_match.group(1).strip()
    return text.strip()


def parse_json(text: str) -> tuple[Optional[dict], Optional[str]]:
    """安全JSON解析，失败返回 (None, error_msg)"""
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, str(exc)
