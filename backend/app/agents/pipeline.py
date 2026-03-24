import json
import re
import sys
import logging
from typing import Any, Callable
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from backend.app.agents.llm import extract_json_text, parse_json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("interface-agent-llm")


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


def _stream_llm_text(runnable, payload: dict, on_chunk: Callable[[str], None] | None = None) -> str:
    fragments: list[str] = []
    for chunk in runnable.stream(payload):
        text_chunk = _stringify_stream_content(getattr(chunk, "content", ""))
        if not text_chunk:
            continue
        fragments.append(text_chunk)
        if on_chunk:
            on_chunk(text_chunk)
    return "".join(fragments)


def plan_task(
    llm,
    user_input: str,
    catalog: list[dict],
    debug_prompt: bool = False,
    on_chunk: Callable[[str], None] | None = None,
) -> dict:
    catalog_text = "\n".join(
        [f"- {item['businessName']} | {item['interfaceUri']} | {item['fileName']}" for item in catalog]
    )
    planner_prompt = ChatPromptTemplate(
        messages=[
            SystemMessagePromptTemplate.from_template(
                "你是 Plan 阶段规划器。"
                "请根据用户输入识别任务路由和业务场景。"
                "只输出严格JSON，不要输出其他文字。"
                "JSON必须包含这些键："
                "taskRoute, scenarioName, businessFile, objective, needMcp, shouldAskUser, resolveSteps。"
                "其中 resolveSteps 必须是数组，至少包含1个步骤。"
                "每个步骤必须包含 stepName, objective, expectedOutput, taskRoute, needMcp。"
            ),
            HumanMessagePromptTemplate.from_template(
                "候选场景列表:\n{catalog}\n\n用户输入:\n{input}\n\n请输出规划JSON。"
            ),
        ]
    )
    plan_input = {
        "catalog": catalog_text,
        "input": user_input,
    }
    if debug_prompt:
        formatted_messages = planner_prompt.format_messages(**plan_input)
        print("=== PLAN_PROMPT_START ===", file=sys.stderr)
        for message in formatted_messages:
            print(f"[{getattr(message, 'type', 'unknown')}]", file=sys.stderr)
            print(message.content, file=sys.stderr)
            print("", file=sys.stderr)
        print("=== PLAN_PROMPT_END ===", file=sys.stderr)
    planner_runnable = planner_prompt | llm
    try:
        response_content = _stream_llm_text(planner_runnable, plan_input, on_chunk=on_chunk)
    except Exception as exc:
        logger.info("LLM plan 调用失败: %s", exc)
        raise
    logger.info("LLM plan 响应=%s", response_content)
    parsed, _ = parse_json(extract_json_text(response_content))
    if parsed:
        return parsed
    return {
        "taskRoute": "配置生成",
        "scenarioName": "待判定场景",
        "businessFile": "",
        "objective": "完成用户请求",
        "needMcp": False,
        "shouldAskUser": False,
        "resolveSteps": [
            {
                "stepName": "生成结果",
                "objective": "完成用户请求",
                "expectedOutput": "给出明确结论",
                "taskRoute": "配置生成",
                "needMcp": False,
            }
        ],
    }


def resolve_task(
    llm,
    user_input: str,
    mode: str,
    plan: dict,
    system_prompt: str,
    business_context: str,
    jarvis_params: dict,
    current_step: dict,
    previous_steps: list[dict],
    on_chunk: Callable[[str], None] | None = None,
) -> dict:
    expected_route = str(plan.get("taskRoute", ""))
    step_route = str(current_step.get("taskRoute", expected_route))
    need_mcp_default = bool(current_step.get("needMcp")) or mode == "mcp" or step_route == "自动化配置"
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
    resolve_input = {
        "system_prompt": system_prompt,
        "business_context": business_context,
        "plan": json.dumps(plan, ensure_ascii=False),
        "current_step": json.dumps(current_step, ensure_ascii=False),
        "previous_steps": json.dumps(previous_steps, ensure_ascii=False),
        "jarvis_input": json.dumps(jarvis_params.get("input"), ensure_ascii=False),
        "jarvis_output": json.dumps(jarvis_params.get("output"), ensure_ascii=False),
        "mode": mode,
        "input": user_input,
    }
    resolver_runnable = resolver_prompt | llm
    try:
        response_content = _stream_llm_text(resolver_runnable, resolve_input, on_chunk=on_chunk)
    except Exception as exc:
        logger.exception("LLM resolve 调用失败: %s", exc)
        raise
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
            if {"shouldDisplay", "taskRoute", "reply", "needMcp", "config", "risk"}.issubset(set(maybe_config.keys())):
                return maybe_config
            parsed_config = maybe_config
            break
    fallback_payload: dict[str, Any] = {
        "shouldDisplay": True,
        "taskRoute": step_route,
        "reply": response_content.strip(),
        "needMcp": need_mcp_default,
        "config": parsed_config,
        "risk": "",
    }
    return fallback_payload
