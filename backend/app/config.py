from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_DIR = REPO_ROOT / "backend" / "app" / "prompts"
VENV_PYTHON = REPO_ROOT / "venv" / "bin" / "python"
MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://localhost:8099")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://biao@127.0.0.1:5432/postgres")
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "interface-agent-dev-secret")
ACCESS_TOKEN_EXPIRE_SECONDS = int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "86400"))
