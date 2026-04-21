"""MCP 工具 — 通过 httpx 异步调用 interface-agent 框架的 MCP 服务"""

import logging
from typing import Any

import httpx

from backend.app.config import MCP_BASE_URL
from backend.app.agents.tools.base import AgentTool
from backend.app.agents.utils import parse_json

logger = logging.getLogger("interface-agent-mcp")

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


async def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{MCP_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        if method == "GET":
            resp = await client.get(url)
        else:
            resp = await client.request(
                method, url, json=body,
                headers={"Content-Type": "application/json"},
            )
        resp.raise_for_status()
        parsed, _ = parse_json(resp.text)
        return parsed if parsed is not None else {"raw": resp.text}


def _normalize_param_mappings(param_mappings: Any) -> list[dict]:
    if isinstance(param_mappings, list):
        return param_mappings
    if isinstance(param_mappings, dict):
        return [param_mappings]
    return []


class MCPTool(AgentTool):
    """
    MCP 工具 — 调用 interface-agent 框架的 MCP 服务完成自动化配置。

    职责：创建节点、导入参数映射、创建工作流。
    """

    def __init__(self):
        super().__init__(
            name="mcp",
            description="调用 interface-agent 框架 MCP 服务，执行节点创建、参数映射导入、工作流创建等自动化配置操作",
        )

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        results: dict[str, Any] = {"nodes": [], "paramMappings": [], "workflow": None}

        nodes = parameters.get("nodes", [])
        created_node_ids: list = []
        for node in nodes:
            result = await _request("POST", "/v1/ai/mcp/workflow-node/create", node)
            results["nodes"].append(result)
            created_node_ids.append(result.get("rsp"))

        for mapping in _normalize_param_mappings(parameters.get("paramMappings")):
            node_id = mapping.get("nodeId")
            if not node_id and len(created_node_ids) == 1:
                node_id = created_node_ids[0]
            if node_id:
                mapping = dict(mapping)
                mapping["nodeId"] = node_id
            result = await _request("POST", "/v1/ai/mcp/node-param-config/import", mapping)
            results["paramMappings"].append(result)

        workflow = parameters.get("workflow")
        if isinstance(workflow, dict):
            workflow_payload = dict(workflow)
            if not workflow_payload.get("firstFlowNodes") and created_node_ids:
                workflow_payload["firstFlowNodes"] = created_node_ids
            results["workflow"] = await _request(
                "POST", "/v1/ai/mcp/workflow/create", workflow_payload
            )

        return results
