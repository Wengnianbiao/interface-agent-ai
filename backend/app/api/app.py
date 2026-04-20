"""FastAPI 应用工厂 — 组装 app 实例、中间件、路由"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.auth import AUTH_ENABLED, init_auth_schema
from backend.app.chat import init_chat_schema
from backend.app.config import REPO_ROOT

from backend.app.api.routes import auth, chat, frontend

logger = logging.getLogger("interface-agent-api")

FRONTEND_DIST_DIR = REPO_ROOT / "backend" / "app" / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if AUTH_ENABLED:
        init_auth_schema()
        init_chat_schema()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Interface-Agent AI API", lifespan=lifespan)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应通过环境变量限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- 健康检查 (无前缀，直接挂在 app 上) ----
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": "interface-agent-ai", "authEnabled": AUTH_ENABLED}

    # ---- 业务路由 ----
    app.include_router(auth.router)
    app.include_router(chat.router)

    # ---- 静态资源 ----
    if (FRONTEND_DIST_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets"), name="frontend-assets")

    # frontend SPA fallback 放最后，避免吞掉 API 路由
    app.include_router(frontend.router)

    return app
