import json
import re
import sys
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from backend.app.agents.core import extract_json_text, parse_json


def plan_task(llm, user_input: str, catalog: list[dict], debug_prompt: bool = False) -> dict:
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
                "taskRoute, scenarioName, businessFile, objective, needMcp, shouldAskUser。"
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
    response = (planner_prompt | llm).invoke(plan_input)
    parsed, _ = parse_json(extract_json_text(response.content))
    if parsed:
        return parsed
    return {
        "taskRoute": "配置生成",
        "scenarioName": "待判定场景",
        "businessFile": "",
        "objective": "完成用户请求",
        "needMcp": False,
        "shouldAskUser": False,
    }


def resolve_task(
    llm,
    user_input: str,
    mode: str,
    plan: dict,
    system_prompt: str,
    business_context: str,
    jarvis_params: dict,
) -> dict:
    expected_route = str(plan.get("taskRoute", ""))
    need_mcp_default = mode == "mcp" or expected_route == "自动化配置"
    resolver_prompt = ChatPromptTemplate(
        messages=[
            SystemMessagePromptTemplate.from_template(
                "你是 Resolve 阶段执行器。"
                "你必须遵守任务路由与输出模板。"
                "优先输出面向用户的文字说明。"
                "如果需要给出配置，必须在单独的 ```json 代码块中输出配置对象。"
                "不要输出与任务无关的解释。"
            ),
            HumanMessagePromptTemplate.from_template(
                "系统上下文:\n{system_prompt}\n\n"
                "业务场景上下文:\n{business_context}\n\n"
                "Plan结果:\n{plan}\n\n"
                "Jarvis入参示例:\n{jarvis_input}\n\n"
                "Jarvis出参示例:\n{jarvis_output}\n\n"
                "运行模式:{mode}\n"
                "用户输入:\n{input}\n\n"
                "请先输出结论与依据，再按需输出配置JSON代码块。"
            ),
        ]
    )
    response = (resolver_prompt | llm).invoke(
        {
            "system_prompt": system_prompt,
            "business_context": business_context,
            "plan": json.dumps(plan, ensure_ascii=False),
            "jarvis_input": json.dumps(jarvis_params.get("input"), ensure_ascii=False),
            "jarvis_output": json.dumps(jarvis_params.get("output"), ensure_ascii=False),
            "mode": mode,
            "input": user_input,
        }
    )
    parsed, _ = parse_json(extract_json_text(response.content))
    if parsed and isinstance(parsed, dict) and "reply" in parsed:
        return parsed
    json_blocks = re.findall(r"```json\s*([\s\S]*?)```", response.content)
    parsed_config = {}
    for block in json_blocks:
        maybe_config, _ = parse_json(block.strip())
        if isinstance(maybe_config, dict):
            if {"shouldDisplay", "taskRoute", "reply", "needMcp", "config", "risk"}.issubset(set(maybe_config.keys())):
                return maybe_config
            parsed_config = maybe_config
            break
    return {
        "shouldDisplay": True,
        "taskRoute": expected_route,
        "reply": response.content.strip(),
        "needMcp": need_mcp_default,
        "config": parsed_config,
        "risk": "",
    }
