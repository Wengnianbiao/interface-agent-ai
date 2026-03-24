import json
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import typer
from rich.console import Console
from backend.app.agents.llm import get_llm
from backend.app.agents.context_loader import (
    load_plan_system_prompts,
    build_business_catalog,
    load_business_context_by_file,
)
from backend.app.agents.pipeline import plan_task, resolve_task
from backend.app.agents.mcp_client import execute_mcp_sync


QA_ROUTE = "规则问答"
EVALUATION_ROUTE = "可行性评估"
AUTO_CONFIG_ROUTE = "自动化配置"
SPI_ROUTE = "SPI 扩展"
CONFIG_OUTPUT_ROUTE = "配置生成"


def run_with_progress(console: Console, stream: bool, stage: str, fn):
    if not stream:
        return fn()
    start = time.time()
    heartbeat = 0
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        while not future.done():
            time.sleep(1)
            elapsed = int(time.time() - start)
            if elapsed >= heartbeat + 5:
                heartbeat = elapsed
                console.print(f"⏳ {stage}处理中，已等待 {elapsed}s...", markup=False, highlight=False)
        return future.result()


def build_fallback_plan(_input_text: str, resolved_mode: str, _catalog: list[dict]) -> dict:
    return {
        "taskRoute": CONFIG_OUTPUT_ROUTE,
        "scenarioName": "兜底模式",
        "businessFile": "",
        "objective": "返回稳定兜底结果",
        "needMcp": resolved_mode == "mcp",
        "shouldAskUser": False,
        "resolveSteps": [
            {
                "stepName": "输出兜底结论",
                "objective": "返回稳定兜底结果",
                "expectedOutput": "给出明确下一步建议",
                "taskRoute": CONFIG_OUTPUT_ROUTE,
                "needMcp": False,
            }
        ],
    }


def normalize_task_route(plan: dict, resolved_mode: str) -> str:
    plan_route = str(plan.get("taskRoute", "")).strip()
    if plan_route in {QA_ROUTE, EVALUATION_ROUTE, AUTO_CONFIG_ROUTE, SPI_ROUTE, CONFIG_OUTPUT_ROUTE}:
        return plan_route
    if resolved_mode == "mcp":
        return AUTO_CONFIG_ROUTE
    return CONFIG_OUTPUT_ROUTE


def normalize_resolve_steps(plan: dict) -> list[dict]:
    raw_steps = plan.get("resolveSteps")
    normalized_steps: list[dict] = []
    if isinstance(raw_steps, list):
        for idx, item in enumerate(raw_steps):
            if not isinstance(item, dict):
                continue
            step_name = str(item.get("stepName") or f"步骤{idx + 1}").strip()
            objective = str(item.get("objective") or plan.get("objective") or "完成用户请求").strip()
            expected_output = str(item.get("expectedOutput") or "给出明确结果").strip()
            step_route = str(item.get("taskRoute") or plan.get("taskRoute") or CONFIG_OUTPUT_ROUTE).strip()
            normalized_steps.append(
                {
                    "stepNo": idx + 1,
                    "stepName": step_name,
                    "objective": objective,
                    "expectedOutput": expected_output,
                    "taskRoute": step_route,
                    "needMcp": bool(item.get("needMcp")),
                }
            )
    if normalized_steps:
        return normalized_steps
    return [
        {
            "stepNo": 1,
            "stepName": "输出结果",
            "objective": str(plan.get("objective") or "完成用户请求"),
            "expectedOutput": "给出明确结论",
            "taskRoute": str(plan.get("taskRoute") or CONFIG_OUTPUT_ROUTE),
            "needMcp": bool(plan.get("needMcp")),
        }
    ]


def build_fallback_resolved(_user_input: str, plan: dict, resolved_mode: str) -> dict:
    task_route = normalize_task_route(plan, resolved_mode)
    if task_route == AUTO_CONFIG_ROUTE:
        reply = (
            "【结论】\n- 当前请求可继续生成自动化配置。\n\n"
            "【说明】\n- 当前返回为兜底结果，请补充更完整的三方入参与返参示例后再生成配置。"
        )
    elif task_route == SPI_ROUTE:
        reply = (
            "【SPI结论】\n- 该场景可能涉及扩展能力。\n\n"
            "【下一步】\n- 请补充协议、鉴权、签名/加解密规则，我将给出完整 SPI 方案。"
        )
    elif task_route == QA_ROUTE:
        reply = (
            "【规则问答】\n- 我会优先解释框架规则与参数映射方式。\n\n"
            "【建议】\n- 如需输出配置 JSON，请补充具体业务场景与三方入参/返参样例。"
        )
    elif task_route == EVALUATION_ROUTE:
        reply = (
            "【可行性评估】\n- 我会先判定可配置化、SPI扩展或不支持。\n\n"
            "【建议】\n- 请补充三方接口文档或完整出入参样例，评估会更准确。"
        )
    else:
        reply = (
            "【结论】\n- 这是配置生成场景。\n\n"
            "【说明】\n- 我会输出结构化 JSON 配置，并给出校验建议。"
        )
    return {
        "shouldDisplay": True,
        "taskRoute": task_route,
        "reply": reply,
        "needMcp": False,
        "config": {},
        "risk": "兜底结果，建议补充完整接口样例后再次生成。",
    }


def run_planning_stage(
    console: Console,
    llm,
    input_text: str,
    stream: bool,
) -> tuple[dict, str, str, dict, Optional[str]]:
    resolved_mode = "generate"
    catalog = build_business_catalog()
    planning_stream_started = False

    def on_planning_chunk(_: str):
        nonlocal planning_stream_started
        if stream and not planning_stream_started:
            planning_stream_started = True
            console.print("🫧 任务规划模型流式输出中...", markup=False, highlight=False)

    if stream:
        console.print("🔎 正在识别任务与业务场景...", markup=False, highlight=False)
    plan = run_with_progress(
        console=console,
        stream=stream,
        stage="任务规划",
        fn=lambda: plan_task(llm, input_text, catalog, debug_prompt=True, on_chunk=on_planning_chunk),
    )
    if not isinstance(plan, dict):
        plan = build_fallback_plan(input_text, resolved_mode, catalog)
    normalized_route = normalize_task_route(plan, resolved_mode)
    plan["taskRoute"] = normalized_route
    plan["resolveSteps"] = normalize_resolve_steps(plan)
    if stream:
        console.print(
            f"✅ 规划完成：任务={plan.get('taskRoute', '未知')} | 场景={plan.get('scenarioName', '未知')} | 子任务数={len(plan.get('resolveSteps', []))}",
            markup=False,
            highlight=False,
        )
    if normalized_route == AUTO_CONFIG_ROUTE:
        resolved_mode = "mcp"
    business_file = None if normalized_route == QA_ROUTE else plan.get("businessFile")
    business_context, jarvis_params, business_file_path = load_business_context_by_file(business_file)
    return plan, resolved_mode, business_context, jarvis_params, business_file_path


def run_execution_stage(
    console: Console,
    llm,
    input_text: str,
    stream: bool,
    plan: dict,
    resolved_mode: str,
    system_prompt: str,
    business_context: str,
    jarvis_params: dict,
) -> tuple[dict, dict | None, dict | None, str, str]:
    steps = normalize_resolve_steps(plan)
    step_results: list[dict] = []
    latest_config: dict | None = None
    latest_need_mcp = False
    task_route = str(plan.get("taskRoute", ""))
    if stream:
        console.print("🧠 正在按计划逐步执行...", markup=False, highlight=False)
    for step in steps:
        step_name = step.get("stepName", "未命名步骤")
        resolve_stream_started = False

        def on_resolve_chunk(_: str):
            nonlocal resolve_stream_started
            if stream and not resolve_stream_started:
                resolve_stream_started = True
                console.print(f"🫧 步骤{step.get('stepNo')}模型流式输出中...", markup=False, highlight=False)

        if stream:
            console.print(f"➡️ 执行步骤 {step.get('stepNo')}：{step_name}", markup=False, highlight=False)
        step_mode = resolved_mode
        if bool(step.get("needMcp")):
            step_mode = "mcp"
        step_resolved = run_with_progress(
            console=console,
            stream=stream,
            stage=f"步骤{step.get('stepNo')}执行",
            fn=lambda current_step=step: resolve_task(
                llm=llm,
                user_input=input_text,
                mode=step_mode,
                plan=plan,
                system_prompt=system_prompt,
                business_context=business_context,
                jarvis_params=jarvis_params,
                current_step=current_step,
                previous_steps=step_results,
                on_chunk=on_resolve_chunk,
            ),
        )
        if not isinstance(step_resolved, dict):
            step_resolved = build_fallback_resolved(input_text, {"taskRoute": step.get("taskRoute", task_route)}, step_mode)
        normalized_step_route = normalize_task_route({"taskRoute": step_resolved.get("taskRoute", step.get("taskRoute", task_route))}, step_mode)
        step_resolved["taskRoute"] = normalized_step_route
        step_result_summary = {
            "stepNo": step.get("stepNo"),
            "stepName": step_name,
            "taskRoute": normalized_step_route,
            "reply": str(step_resolved.get("reply", "")),
            "risk": str(step_resolved.get("risk", "")),
        }
        step_results.append(step_result_summary)
        maybe_config = step_resolved.get("config")
        if isinstance(maybe_config, dict) and maybe_config:
            latest_config = maybe_config
            latest_need_mcp = bool(step_resolved.get("needMcp"))
        task_route = normalized_step_route
    if not step_results:
        resolved = build_fallback_resolved(input_text, plan, resolved_mode)
    else:
        step_lines = [f"{item['stepNo']}. {item['stepName']}" for item in steps]
        reply_parts = ["【执行计划】", *step_lines, "", "【分步结果】"]
        for item in step_results:
            reply_parts.append(
                f"步骤{item['stepNo']}（{item['stepName']}）\n{item['reply']}"
            )
        resolved = {
            "shouldDisplay": True,
            "taskRoute": task_route,
            "reply": "\n\n".join(reply_parts).strip(),
            "needMcp": latest_need_mcp,
            "config": latest_config or {},
            "risk": "；".join([item["risk"] for item in step_results if item.get("risk")]),
            "stepResults": step_results,
        }
    config = resolved.get("config") if isinstance(resolved, dict) else None
    need_mcp = bool(resolved.get("needMcp")) if isinstance(resolved, dict) else False
    mcp_results = None
    if isinstance(config, dict) and (need_mcp or resolved_mode == "mcp" or task_route == AUTO_CONFIG_ROUTE):
        try:
            mcp_results = execute_mcp_sync(config)
        except Exception as exc:
            mcp_results = {"error": str(exc)}
    should_display = bool(resolved.get("shouldDisplay", True)) if isinstance(resolved, dict) else True
    reply = resolved.get("reply", "") if isinstance(resolved, dict) else ""
    if not reply:
        reply = "【结果】\n- 已完成任务执行，但未生成可展示内容。"
    if not should_display:
        reply = "【结果】\n- 当前结果不建议直接展示给用户，请补充输入信息后重试。"
    if mcp_results:
        reply = f"{reply}\n\n【MCP执行结果】\n```json\n{json.dumps(mcp_results, ensure_ascii=False, indent=2)}\n```"
    if stream:
        console.print(reply, markup=False, highlight=False)
    return resolved, config, mcp_results, task_route, reply


def run_plan_and_resolve(console: Console, input_text: str, stream: bool) -> dict:
    llm = get_llm(console)
    if not llm:
        raise typer.Exit(1)
    system_prompt = load_plan_system_prompts()
    plan, resolved_mode, business_context, jarvis_params, business_file_path = run_planning_stage(
        console=console,
        llm=llm,
        input_text=input_text,
        stream=stream,
    )
    if stream:
        plan_payload = {
            "taskRoute": str(plan.get("taskRoute", "")),
            "scenarioName": str(plan.get("scenarioName", "")),
            "objective": str(plan.get("objective", "")),
            "resolveSteps": plan.get("resolveSteps", []),
        }
        console.print(
            f"<<<PLAN_JSON>>>{json.dumps(plan_payload, ensure_ascii=False)}<<<END_PLAN_JSON>>>",
            markup=False,
            highlight=False,
        )
    resolved, config, mcp_results, task_route, reply = run_execution_stage(
        console=console,
        llm=llm,
        input_text=input_text,
        stream=stream,
        plan=plan,
        resolved_mode=resolved_mode,
        system_prompt=system_prompt,
        business_context=business_context,
        jarvis_params=jarvis_params,
    )
    return {
        "mode": resolved_mode,
        "taskRoute": task_route,
        "plan": plan,
        "businessFile": business_file_path,
        "resolved": resolved,
        "config": config,
        "mcpResults": mcp_results,
        "display": reply,
    }
