from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_DIR = REPO_ROOT / "backend" / "app" / "prompts"
VENV_PYTHON = REPO_ROOT / "venv" / "bin" / "python"
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://localhost:8099")
