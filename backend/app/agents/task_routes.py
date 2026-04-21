"""任务路由常量与归一化 — 从 plan_resolve_runner.py 提取"""

QA_ROUTE = "规则问答"
EVALUATION_ROUTE = "可行性评估"
AUTO_CONFIG_ROUTE = "自动化配置"
SPI_ROUTE = "SPI扩展"
CONFIG_OUTPUT_ROUTE = "配置生成"

_VALID_ROUTES = {QA_ROUTE, EVALUATION_ROUTE, AUTO_CONFIG_ROUTE, SPI_ROUTE, CONFIG_OUTPUT_ROUTE}


def normalize_task_route(plan_dict: dict, resolved_mode: str) -> str:
    plan_route = str(plan_dict.get("taskRoute", "")).strip()
    if plan_route in _VALID_ROUTES:
        return plan_route
    if resolved_mode == "mcp":
        return AUTO_CONFIG_ROUTE
    return CONFIG_OUTPUT_ROUTE


def normalize_resolve_steps(plan_dict: dict) -> list[dict]:
    raw_steps = plan_dict.get("resolveSteps")
    normalized: list[dict] = []
    if isinstance(raw_steps, list):
        for idx, item in enumerate(raw_steps):
            if not isinstance(item, dict):
                continue
            normalized.append({
                "stepNo": idx + 1,
                "stepName": str(item.get("stepName") or f"步骤{idx + 1}").strip(),
                "objective": str(item.get("objective") or plan_dict.get("objective") or "完成用户请求").strip(),
                "expectedOutput": str(item.get("expectedOutput") or "给出明确结果").strip(),
                "taskRoute": str(item.get("taskRoute") or plan_dict.get("taskRoute") or CONFIG_OUTPUT_ROUTE).strip(),
                "needMcp": bool(item.get("needMcp")),
            })
    if normalized:
        return normalized
    return [{
        "stepNo": 1,
        "stepName": "输出结果",
        "objective": str(plan_dict.get("objective") or "完成用户请求"),
        "expectedOutput": "给出明确结论",
        "taskRoute": str(plan_dict.get("taskRoute") or CONFIG_OUTPUT_ROUTE),
        "needMcp": bool(plan_dict.get("needMcp")),
    }]


def build_fallback_resolved(plan_dict: dict, resolved_mode: str) -> dict:
    task_route = normalize_task_route(plan_dict, resolved_mode)
    fallback_replies = {
        AUTO_CONFIG_ROUTE: "【结论】\n- 当前请求可继续生成自动化配置。\n\n【说明】\n- 当前返回为兜底结果，请补充更完整的三方入参与返参示例后再生成配置。",
        SPI_ROUTE: "【SPI结论】\n- 该场景可能涉及扩展能力。\n\n【下一步】\n- 请补充协议、鉴权、签名/加解密规则，我将给出完整 SPI 方案。",
        QA_ROUTE: "【规则问答】\n- 我会优先解释框架规则与参数映射方式。\n\n【建议】\n- 如需输出配置 JSON，请补充具体业务场景与三方入参/返参样例。",
        EVALUATION_ROUTE: "【可行性评估】\n- 我会先判定可配置化、SPI扩展或不支持。\n\n【建议】\n- 请补充三方接口文档或完整出入参样例，评估会更准确。",
    }
    reply = fallback_replies.get(task_route, "【结论】\n- 这是配置生成场景。\n\n【说明】\n- 我会输出结构化 JSON 配置，并给出校验建议。")
    return {
        "shouldDisplay": True,
        "taskRoute": task_route,
        "reply": reply,
        "needMcp": False,
        "config": {},
        "risk": "兜底结果，建议补充完整接口样例后再次生成。",
    }
