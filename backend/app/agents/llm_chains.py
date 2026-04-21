"""LLM Chain 构建与输出解析 — Plan / Resolve 阶段的 prompt 模板和解析逻辑"""

import json
import re
import logging
from typing import Any, AsyncGenerator

from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

from backend.app.agents.utils import extract_json_text, parse_json

logger = logging.getLogger("interface-agent-llm")

PLAN_REQUIRED_KEYS = {
    "taskRoute", "scenarioName", "businessFile",
    "objective", "needMcp", "shouldAskUser", "resolveSteps",
}


def _stringify_stream_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
                continue
            if isinstance(item, dict):
                maybe_text = item.get("text")
                if isinstance(maybe_text, str):
                    text_parts.append(maybe_text)
        return "".join(text_parts)
    return ""


async def astream_llm_chunks(runnable, payload: dict) -> AsyncGenerator[str, None]:
    async for chunk in runnable.astream(payload):
        text_chunk = _stringify_stream_content(getattr(chunk, "content", ""))
        if text_chunk:
            yield text_chunk


def extract_plan_output(response_content: str) -> dict:
    candidates: list[str] = []
    extracted = extract_json_text(response_content)
    if extracted:
        candidates.append(extracted)
    json_blocks = re.findall(r"```json\s*([\s\S]*?)```", response_content)
    candidates.extend([block.strip() for block in json_blocks if block.strip()])
    for candidate in candidates:
        parsed, _ = parse_json(candidate)
        if not isinstance(parsed, dict):
            continue
        if not PLAN_REQUIRED_KEYS.issubset(set(parsed.keys())):
            continue
        if not isinstance(parsed.get("resolveSteps"), list):
            continue
        return parsed
    raise ValueError("Plan 输出解析失败：未提取到完整的规划 JSON")


def build_plan_chain(llm, user_input: str, system_prompt: str) -> tuple:
    planner_prompt = ChatPromptTemplate(
        messages=[
            SystemMessagePromptTemplate.from_template(
                "{system_prompt}\n\n"
                "你当前处于 Plan 阶段。"
                "你的任务是根据用户输入判定任务路由并拆解执行步骤。"
                "本阶段不要展开业务文档内容。"
                "只输出严格JSON，不要输出其他文字。"
                "JSON必须包含这些键："
                "taskRoute, scenarioName, businessFile, objective, needMcp, shouldAskUser, resolveSteps。"
                "其中 resolveSteps 必须是数组，至少包含1个步骤。"
                "每个步骤必须包含 stepName, objective, expectedOutput, taskRoute, needMcp。"
            ),
            HumanMessagePromptTemplate.from_template(
                "用户输入:\n{input}\n\n请输出规划JSON。"
            ),
        ]
    )
    payload = {
        "system_prompt": system_prompt,
        "input": user_input,
    }
    formatted_messages = planner_prompt.format_messages(**payload)
    for message in formatted_messages:
        logger.info(
            "[Plan Prompt][%s] %s",
            getattr(message, "type", "unknown"),
            message.content[:500],
        )
    return planner_prompt | llm, payload


def build_resolve_chain(
    llm,
    user_input: str,
    mode: str,
    plan_dict: dict,
    system_prompt: str,
    business_context: str,
    jarvis_params: dict,
    current_step: dict,
    previous_steps: list[dict],
) -> tuple:
    expected_route = str(plan_dict.get("taskRoute", ""))
    step_route = str(current_step.get("taskRoute", expected_route))
    need_mcp_default = (
        bool(current_step.get("needMcp"))
        or mode == "mcp"
        or step_route == "自动化配置"
    )
    resolver_prompt = ChatPromptTemplate(
        messages=[
            SystemMessagePromptTemplate.from_template(
                "你是 Resolve 阶段执行器。"
                "你必须只解决当前步骤，不要跨步骤执行。"
                "你必须遵守任务路由与输出模板。"
                "只输出严格JSON，不要输出其他文字。"
                "JSON必须包含这些键：shouldDisplay, taskRoute, reply, needMcp, config, risk。"
                "reply 必须是面向用户的结果说明。"
                "如果当前步骤不需要配置，config 输出 {{}}。"
            ),
            HumanMessagePromptTemplate.from_template(
                "系统上下文:\n{system_prompt}\n\n"
                "业务场景上下文:\n{business_context}\n\n"
                "Plan结果:\n{plan}\n\n"
                "当前步骤:\n{current_step}\n\n"
                "已完成步骤结果摘要:\n{previous_steps}\n\n"
                "Jarvis入参示例:\n{jarvis_input}\n\n"
                "Jarvis出参示例:\n{jarvis_output}\n\n"
                "运行模式:{mode}\n"
                "用户输入:\n{input}\n\n"
                "请输出当前步骤的执行结果JSON。"
            ),
        ]
    )
    payload = {
        "system_prompt": system_prompt,
        "business_context": business_context,
        "plan": json.dumps(plan_dict, ensure_ascii=False),
        "current_step": json.dumps(current_step, ensure_ascii=False),
        "previous_steps": json.dumps(previous_steps, ensure_ascii=False),
        "jarvis_input": json.dumps(jarvis_params.get("input"), ensure_ascii=False),
        "jarvis_output": json.dumps(jarvis_params.get("output"), ensure_ascii=False),
        "mode": mode,
        "input": user_input,
    }
    return resolver_prompt | llm, payload, step_route, need_mcp_default


def build_final_answer_chain(
    llm,
    user_input: str,
    system_prompt: str,
    plan_dict: dict,
    step_results: list[dict],
    business_context: str,
) -> tuple:
    """基于所有步骤的执行结果，生成面向用户的最终回答（流式自然语言）"""
    answer_prompt = ChatPromptTemplate(
        messages=[
            SystemMessagePromptTemplate.from_template(
                "{system_prompt}\n\n"
                "你现在处于最终回答阶段。"
                "前面的 Plan 和 Resolve 步骤已经全部完成，下面提供了所有步骤的执行结果。"
                "请你根据这些结果，给用户一个完整、清晰、结构化的最终回答。"
                "直接用自然语言回答，不要输出 JSON。"
                "回答要专业、有条理，可以使用 Markdown 格式（标题、列表、代码块等）。"
                "如果步骤结果中包含配置 JSON，请在回答中以代码块形式展示。"
                "如果有风险提示，也一并说明。"
            ),
            HumanMessagePromptTemplate.from_template(
                "业务场景上下文:\n{business_context}\n\n"
                "任务规划:\n{plan}\n\n"
                "各步骤执行结果:\n{step_results}\n\n"
                "用户原始问题:\n{input}\n\n"
                "请给出最终回答。"
            ),
        ]
    )
    payload = {
        "system_prompt": system_prompt,
        "business_context": business_context,
        "plan": json.dumps(plan_dict, ensure_ascii=False),
        "step_results": json.dumps(step_results, ensure_ascii=False),
        "input": user_input,
    }
    return answer_prompt | llm, payload


def parse_resolve_output(
    response_content: str, step_route: str, need_mcp_default: bool
) -> dict:
    logger.info("LLM resolve 响应=%s", response_content)
    parsed, _ = parse_json(extract_json_text(response_content))
    if parsed and isinstance(parsed, dict) and "reply" in parsed:
        if "taskRoute" not in parsed:
            parsed["taskRoute"] = step_route
        if "needMcp" not in parsed:
            parsed["needMcp"] = need_mcp_default
        if "config" not in parsed:
            parsed["config"] = {}
        if "risk" not in parsed:
            parsed["risk"] = ""
        if "shouldDisplay" not in parsed:
            parsed["shouldDisplay"] = True
        return parsed

    json_blocks = re.findall(r"```json\s*([\s\S]*?)```", response_content)
    parsed_config = {}
    for block in json_blocks:
        maybe_config, _ = parse_json(block.strip())
        if isinstance(maybe_config, dict):
            if {"shouldDisplay", "taskRoute", "reply", "needMcp", "config", "risk"}.issubset(
                set(maybe_config.keys())
            ):
                return maybe_config
            parsed_config = maybe_config
            break

    return {
        "shouldDisplay": True,
        "taskRoute": step_route,
        "reply": response_content.strip(),
        "needMcp": need_mcp_default,
        "config": parsed_config,
        "risk": "",
    }
