"""FastAPI 后端服务"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess
import logging
import uuid
import select
import os
from collections import deque
from pathlib import Path
import sys
import threading
import uvicorn

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[3]))

from backend.app.config import REPO_ROOT, VENV_PYTHON

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("interface-agent-api")

app = FastAPI(title="Interface-Agent AI API")
AGENT_ENTRY = REPO_ROOT / "backend" / "app" / "agents" / "main.py"
FRONTEND_DIST_DIR = REPO_ROOT / "backend" / "app" / "static"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"
MAX_SESSION_HISTORY = 20
MAX_REQUEST_HISTORY = 12
session_histories: dict[str, deque[dict[str, str]]] = {}
session_lock = threading.Lock()

# 允许 CORS (前端跨域访问)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    prompt: str
    sessionId: str | None = None
    history: list[dict[str, str]] | None = None


class ChatResponse(BaseModel):
    response: str
    success: bool


def normalize_history(history: list[dict[str, str]] | None) -> list[dict[str, str]]:
    if not history:
        return []
    normalized: list[dict[str, str]] = []
    for item in history[-MAX_REQUEST_HISTORY:]:
        role = (item.get("role") or "").strip()
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content[:1200]})
    return normalized


def get_session_history(session_id: str) -> list[dict[str, str]]:
    with session_lock:
        session_deque = session_histories.get(session_id)
        if not session_deque:
            return []
        return list(session_deque)[-MAX_REQUEST_HISTORY:]


def update_session_history(session_id: str, role: str, content: str):
    cleaned = content.strip()
    if not cleaned:
        return
    with session_lock:
        if session_id not in session_histories:
            session_histories[session_id] = deque(maxlen=MAX_SESSION_HISTORY)
        session_histories[session_id].append({"role": role, "content": cleaned[:1200]})


def build_contextual_input(prompt: str, history: list[dict[str, str]]) -> str:
    if not history:
        return prompt
    lines = ["以下是最近对话历史，请结合上下文回答："]
    for item in history:
        role_text = "用户" if item["role"] == "user" else "助手"
        lines.append(f"{role_text}: {item['content']}")
    lines.append("")
    lines.append(f"当前用户问题: {prompt}")
    return "\n".join(lines)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    处理用户聊天请求 - 流式输出
    
    Args:
        request: 包含用户输入的 prompt
        
    Returns:
        流式的 AI 生成内容
    """
    request_id = str(uuid.uuid4())[:8]
    session_id = request.sessionId or str(uuid.uuid4())
    request_history = normalize_history(request.history)
    session_history = get_session_history(session_id)
    merged_history = (session_history + request_history)[-MAX_REQUEST_HISTORY:]
    logger.info("request_id=%s 收到请求", request_id)
    logger.info("request_id=%s session_id=%s 输入预览=%s", request_id, session_id, request.prompt[:100].replace("\n", " "))

    input_text = build_contextual_input(request.prompt, merged_history)
    
    try:
        command = [
            str(VENV_PYTHON),
            "-u",
            str(AGENT_ENTRY),
            "plan-execute",
            "--stream",
        ]
        logger.info("request_id=%s 启动Agent命令=%s", request_id, " ".join(command))
        process = subprocess.Popen(
            [
                *command
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            bufsize=0,
            cwd=str(REPO_ROOT)
        )
        logger.info("request_id=%s Agent进程已启动 pid=%s", request_id, process.pid)
        
        process.stdin.write(input_text.encode("utf-8"))
        process.stdin.close()
        
        async def generate_response():
            try:
                line_buffer = ""
                stderr_buffer = ""
                response_fragments: list[str] = []
                while True:
                    ready, _, _ = select.select([process.stdout, process.stderr], [], [], 0.2)
                    if ready:
                        if process.stdout in ready:
                            chunk = os.read(process.stdout.fileno(), 1024)
                            if chunk:
                                text_chunk = chunk.decode("utf-8", errors="replace")
                                response_fragments.append(text_chunk)
                                yield text_chunk
                                line_buffer += text_chunk
                                while "\n" in line_buffer:
                                    line, line_buffer = line_buffer.split("\n", 1)
                                    logger.info("request_id=%s 流式片段=%s", request_id, line[:120])
                        if process.stderr in ready:
                            error_chunk = os.read(process.stderr.fileno(), 1024)
                            if error_chunk:
                                error_text = error_chunk.decode("utf-8", errors="replace")
                                stderr_buffer += error_text
                                for error_line in error_text.splitlines():
                                    if "PLAN_PROMPT_" in error_line or error_line.startswith("[system]") or error_line.startswith("[human]"):
                                        logger.info("request_id=%s Agent调试片段=%s", request_id, error_line[:200])
                                    else:
                                        logger.error("request_id=%s Agent错误片段=%s", request_id, error_line[:200])
                    if process.poll() is not None:
                        tail = process.stdout.read()
                        if tail:
                            tail_text = tail.decode("utf-8", errors="replace")
                            response_fragments.append(tail_text)
                            yield tail_text
                            logger.info("request_id=%s 流式尾部=%s", request_id, tail_text[:120].replace("\n", "\\n"))
                        error_tail = process.stderr.read()
                        if error_tail:
                            error_tail_text = error_tail.decode("utf-8", errors="replace")
                            stderr_buffer += error_tail_text
                            for error_line in error_tail_text.splitlines():
                                if "PLAN_PROMPT_" in error_line or error_line.startswith("[system]") or error_line.startswith("[human]"):
                                    logger.info("request_id=%s Agent调试尾部=%s", request_id, error_line[:200])
                                else:
                                    logger.error("request_id=%s Agent错误尾部=%s", request_id, error_line[:200])
                        break
                process.stdout.close()
                process.stderr.close()
                return_code = process.wait()
                logger.info("request_id=%s Agent进程退出 code=%s", request_id, return_code)
                
                if return_code != 0:
                    logger.error("request_id=%s Agent异常退出 code=%s", request_id, return_code)
                    lowered_error = stderr_buffer.lower()
                    if "arrearage" in lowered_error or "overdue-payment" in lowered_error or "access denied" in lowered_error:
                        fallback = "\n\n❌ 模型服务当前不可用（账户欠费或权限受限），请先恢复模型服务后重试。"
                    else:
                        fallback = f"\n\n❌ AI 生成失败：Agent异常退出，退出码 {return_code}"
                    existing_text = "".join(response_fragments)
                    if "❌" not in existing_text:
                        yield fallback
                        response_fragments.append(fallback)
                full_response = "".join(response_fragments).strip()
                update_session_history(session_id, "user", request.prompt)
                update_session_history(session_id, "assistant", full_response)
            except Exception as e:
                logger.exception("request_id=%s 流式读取异常", request_id)
                yield f"\n\n❌ 错误：{str(e)}"
        
        response = StreamingResponse(generate_response(), media_type="text/plain")
        response.headers["X-Session-Id"] = session_id
        return response
    
    except Exception as e:
        logger.exception("request_id=%s 请求处理失败", request_id)
        raise HTTPException(status_code=500, detail=f"服务器错误：{str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "interface-agent-ai"}


if (FRONTEND_DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets"), name="frontend-assets")


@app.get("/")
async def frontend_index():
    if FRONTEND_INDEX_FILE.exists():
        return FileResponse(FRONTEND_INDEX_FILE)
    raise HTTPException(status_code=404, detail="前端产物不存在，请先执行前端构建")


@app.get("/{full_path:path}")
async def frontend_spa_fallback(full_path: str):
    if full_path.startswith("api") or full_path in {"health", "docs", "redoc", "openapi.json"}:
        raise HTTPException(status_code=404, detail="Not Found")
    file_path = FRONTEND_DIST_DIR / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    if FRONTEND_INDEX_FILE.exists():
        return FileResponse(FRONTEND_INDEX_FILE)
    raise HTTPException(status_code=404, detail="前端产物不存在，请先执行前端构建")


if __name__ == "__main__":
    api_host = os.getenv("API_HOST", "127.0.0.1")
    api_port = int(os.getenv("API_PORT", "8001"))
    display_host = api_host if api_host != "0.0.0.0" else os.getenv("API_DISPLAY_HOST", "127.0.0.1")
    logger.info("启动 API 服务 url=http://%s:%s", display_host, api_port)
    uvicorn.run(app, host=api_host, port=api_port)
