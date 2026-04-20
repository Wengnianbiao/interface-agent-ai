"""uvicorn 启动入口"""

import logging
import os
import socket
import sys
from pathlib import Path

import uvicorn

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[3]))

from backend.app.api.app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("interface-agent-api")

app = create_app()


def _detect_lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        lan_ip = sock.getsockname()[0]
        sock.close()
        return lan_ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", "8001"))
    llm_model_id = os.getenv("LLM_MODEL_ID", "qwen3.5-plus")
    lan_ip = _detect_lan_ip()

    logger.info("启动 API 服务 url=http://127.0.0.1:%s", api_port)
    logger.info("启动 API 服务 url=http://%s:%s", lan_ip, api_port)
    logger.info("当前大模型配置 LLM_MODEL_ID=%s", llm_model_id)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    uvicorn.run(app, host=api_host, port=api_port, log_level="warning")
