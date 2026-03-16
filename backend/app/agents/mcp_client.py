import json
from typing import Optional, List, Any
import urllib.request
from backend.app.config import MCP_BASE_URL
from backend.app.agents.core import parse_json


def request_mcp(method: str, path: str, body: Optional[dict]) -> dict:
    url = f"{MCP_BASE_URL}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        text = response.read().decode("utf-8")
    parsed, _ = parse_json(text)
    return parsed if parsed is not None else {"raw": text}


def normalize_param_mappings(param_mappings: Any) -> List[dict]:
    if isinstance(param_mappings, list):
        return param_mappings
    if isinstance(param_mappings, dict):
        return [param_mappings]
    return []


def execute_mcp_sync(config: dict) -> dict:
    results = {"nodes": [], "paramMappings": [], "workflow": None}
    nodes = config.get("nodes", [])
    created_node_ids = []
    for node in nodes:
        result = request_mcp("POST", "/v1/ai/mcp/workflow-node/create", node)
        results["nodes"].append(result)
        created_node_ids.append(result.get("rsp"))
    for mapping in normalize_param_mappings(config.get("paramMappings")):
        node_id = mapping.get("nodeId")
        if not node_id and len(created_node_ids) == 1:
            node_id = created_node_ids[0]
        if node_id:
            mapping = dict(mapping)
            mapping["nodeId"] = node_id
        result = request_mcp("POST", "/v1/ai/mcp/node-param-config/import", mapping)
        results["paramMappings"].append(result)
    workflow = config.get("workflow")
    if isinstance(workflow, dict):
        workflow_payload = dict(workflow)
        if not workflow_payload.get("firstFlowNodes") and created_node_ids:
            workflow_payload["firstFlowNodes"] = created_node_ids
        results["workflow"] = request_mcp("POST", "/v1/ai/mcp/workflow/create", workflow_payload)
    return results
