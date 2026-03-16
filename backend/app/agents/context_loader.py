import re
from backend.app.config import PROMPT_DIR
from backend.app.agents.core import parse_json


def read_prompt_file(filename: str) -> str:
    file_path = PROMPT_DIR / filename
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8")


def load_system_prompts() -> str:
    core_files = ["agent_bootstrap.md", "project_knowledge.md"]
    system_content = []
    for filename in core_files:
        content = read_prompt_file(filename)
        if content:
            system_content.append(f"=== {filename} ===\n{content}")
    return "\n\n".join(system_content)


def build_business_catalog() -> list[dict]:
    bootstrap = read_prompt_file("agent_bootstrap.md")
    catalog = []
    for line in bootstrap.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if "./business/" not in stripped:
            continue
        columns = [col.strip() for col in stripped.strip("|").split("|")]
        if len(columns) < 3:
            continue
        doc_column = columns[2]
        doc_start = doc_column.find("[")
        doc_mid = doc_column.find("](")
        doc_end = doc_column.find(")")
        if doc_start < 0 or doc_mid < 0 or doc_end < 0:
            continue
        doc_name = doc_column[doc_start + 1:doc_mid].strip()
        doc_path = doc_column[doc_mid + 2:doc_end].strip()
        if not doc_path.startswith("./business/"):
            continue
        catalog.append(
            {
                "businessName": columns[0],
                "interfaceUri": columns[1],
                "docName": doc_name,
                "fileName": doc_path.replace("./business/", "", 1),
            }
        )
    return catalog


def load_business_context_by_file(file_name: str | None) -> tuple[str, dict, str | None]:
    business_dir = PROMPT_DIR / "business"
    if not file_name:
        return "", {"input": None, "output": None}, None
    target_file = business_dir / file_name
    if not target_file.exists():
        return "", {"input": None, "output": None}, None
    content = target_file.read_text(encoding="utf-8")
    jarvis_params = {"input": None, "output": None}
    json_blocks = re.findall(r"```json\s*([\s\S]*?)```", content)
    if len(json_blocks) >= 1:
        parsed, _ = parse_json(json_blocks[0].strip())
        jarvis_params["input"] = parsed
    if len(json_blocks) >= 2:
        parsed, _ = parse_json(json_blocks[1].strip())
        jarvis_params["output"] = parsed
    context = f"=== {target_file.name} ===\n{content}"
    return context, jarvis_params, str(target_file)
