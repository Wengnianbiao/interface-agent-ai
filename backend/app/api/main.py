"""FastAPI 后端服务"""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
import logging
import uuid
import os
import socket
import threading
from queue import Queue
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import uvicorn
from rich.console import Console

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[3]))

from backend.app.config import REPO_ROOT
from backend.app.auth import (
    AUTH_ENABLED,
    AuthUser,
    BootstrapAdminRequest,
    CreateUserRequest,
    LoginRequest,
    RegisterRequest,
    VALID_ROLES,
    count_users,
    create_user,
    get_user_by_username,
    get_current_user,
    init_auth_schema,
    login_with_password,
    require_permission,
)
from backend.app.chat import (
    append_chat_pair,
    get_session_history,
    get_session_messages,
    init_chat_schema,
    list_user_sessions,
)
from backend.app.agents.plan_resolve_runner import run_plan_and_resolve

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("interface-agent-api")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    if AUTH_ENABLED:
        init_auth_schema()
        init_chat_schema()
    yield


app = FastAPI(title="Interface-Agent AI API", lifespan=lifespan)
FRONTEND_DIST_DIR = REPO_ROOT / "backend" / "app" / "static"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"
MAX_REQUEST_HISTORY = 12

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


class ChatResponse(BaseModel):
    response: str
    success: bool


def detect_lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        lan_ip = sock.getsockname()[0]
        sock.close()
        return lan_ip
    except Exception:
        return "127.0.0.1"


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
async def chat(
    request: ChatRequest,
    current_user: AuthUser = Depends(require_permission("chat:use")),
):
    """
    处理用户聊天请求 - 流式输出
    
    Args:
        request: 包含用户输入的 prompt
        
    Returns:
        流式的 AI 生成内容
    """
    request_id = str(uuid.uuid4())[:8]
    session_id = request.sessionId or str(uuid.uuid4())
    session_history = []
    if AUTH_ENABLED and current_user.userId > 0:
        session_history = get_session_history(current_user.userId, session_id, MAX_REQUEST_HISTORY)
    logger.info("request_id=%s 收到请求", request_id)
    logger.info("request_id=%s session_id=%s 输入预览=%s", request_id, session_id, request.prompt[:1000].replace("\n", " "))

    input_text = build_contextual_input(request.prompt, session_history)
    
    try:
        logger.info("request_id=%s 用户输出=%s", request_id, input_text.replace("\n", " "))

        async def generate_response():
            try:
                response_fragments: list[str] = []
                stream_queue: Queue[str | None] = Queue()
                error_holder: dict[str, str] = {}

                class QueueWriter:
                    def write(self, text: str):
                        if text:
                            stream_queue.put(text)
                        return len(text)

                    def flush(self):
                        return None

                def run_agent_sync():
                    try:
                        stream_console = Console(
                            file=QueueWriter(),
                            force_terminal=False,
                            color_system=None,
                        )
                        run_plan_and_resolve(stream_console, input_text, True)
                    except Exception as exc:
                        logger.exception("request_id=%s Agent执行异常", request_id)
                        error_holder["message"] = str(exc)
                    finally:
                        stream_queue.put(None)

                worker = threading.Thread(target=run_agent_sync, daemon=True)
                worker.start()
                while True:
                    text_chunk = await asyncio.to_thread(stream_queue.get)
                    if text_chunk is None:
                        break
                    response_fragments.append(text_chunk)
                    yield text_chunk
                worker.join(timeout=1)

                if error_holder:
                    lowered_error = error_holder["message"].lower()
                    if "arrearage" in lowered_error or "overdue-payment" in lowered_error or "access denied" in lowered_error:
                        fallback = "\n\n❌ 模型服务当前不可用（账户欠费或权限受限），请先恢复模型服务后重试。"
                    else:
                        fallback = f"\n\n❌ AI 生成失败：{error_holder['message']}"
                    existing_text = "".join(response_fragments)
                    if "❌" not in existing_text:
                        yield fallback
                        response_fragments.append(fallback)
                full_response = "".join(response_fragments).strip()
                if AUTH_ENABLED and current_user.userId > 0:
                    append_chat_pair(current_user.userId, session_id, request.prompt, full_response)
            except Exception as e:
                logger.exception("request_id=%s 流式读取异常", request_id)
                yield f"\n\n❌ 错误：{str(e)}"
        
        response = StreamingResponse(generate_response(), media_type="text/plain")
        response.headers["X-Session-Id"] = session_id
        return response
    
    except Exception as e:
        logger.exception("request_id=%s 请求处理失败", request_id)
        raise HTTPException(status_code=500, detail=f"服务器错误：{str(e)}")


@app.get("/api/chat/sessions")
async def chat_sessions(current_user: AuthUser = Depends(require_permission("chat:use"))):
    sessions = list_user_sessions(current_user.userId, limit=50)
    return {"sessions": sessions}


@app.get("/api/chat/sessions/{session_id}/messages")
async def chat_session_messages(
    session_id: str,
    current_user: AuthUser = Depends(require_permission("chat:use")),
):
    messages = get_session_messages(current_user.userId, session_id, limit=300)
    return {"sessionId": session_id, "messages": messages}


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "interface-agent-ai", "authEnabled": AUTH_ENABLED}


@app.post("/api/auth/bootstrap-admin")
async def bootstrap_admin(request: BootstrapAdminRequest):
    if count_users() > 0:
        raise HTTPException(status_code=400, detail="系统已初始化用户，不能重复引导")
    if request.username.strip() == "" or request.password.strip() == "":
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    created = create_user(request.username.strip(), request.password, "admin")
    return {"success": True, "userId": created["user_id"], "username": created["username"], "role": created["role"]}


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    return login_with_password(request.username.strip(), request.password)


@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    username = request.username.strip()
    password = request.password.strip()
    if username == "" or password == "":
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6位")
    existing = get_user_by_username(username)
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")
    create_user(username, request.password, "operator")
    return login_with_password(username, request.password)


@app.get("/api/auth/me")
async def me(current_user: AuthUser = Depends(get_current_user)):
    return current_user


@app.post("/api/auth/users")
async def create_user_api(
    request: CreateUserRequest,
    _current_user: AuthUser = Depends(require_permission("user:manage")),
):
    role = request.role.strip()
    if role not in set(VALID_ROLES):
        raise HTTPException(status_code=400, detail="角色不合法")
    username = request.username.strip()
    if username == "" or request.password.strip() == "":
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    existing = get_user_by_username(username)
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")
    created = create_user(username, request.password, role)
    return {"success": True, "userId": created["user_id"], "username": created["username"], "role": created["role"]}


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
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", "8001"))
    llm_model_id = os.getenv("LLM_MODEL_ID", "qwen3.5-plus")
    lan_ip = detect_lan_ip()
    logger.info("启动 API 服务 url=http://127.0.0.1:%s", api_port)
    logger.info("启动 API 服务 url=http://%s:%s", lan_ip, api_port)
    logger.info("当前大模型配置 LLM_MODEL_ID=%s", llm_model_id)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    uvicorn.run(app, host=api_host, port=api_port, log_level="warning")
