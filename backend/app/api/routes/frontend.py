"""前端静态资源 & SPA fallback 路由"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.app.config import REPO_ROOT

router = APIRouter(tags=["frontend"])

FRONTEND_DIST_DIR = REPO_ROOT / "backend" / "app" / "static"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"


@router.get("/")
async def frontend_index():
    if FRONTEND_INDEX_FILE.exists():
        return FileResponse(FRONTEND_INDEX_FILE)
    raise HTTPException(status_code=404, detail="前端产物不存在，请先执行前端构建")


@router.get("/{full_path:path}")
async def frontend_spa_fallback(full_path: str):
    if full_path.startswith("api") or full_path in {"health", "docs", "redoc", "openapi.json"}:
        raise HTTPException(status_code=404, detail="Not Found")
    file_path = FRONTEND_DIST_DIR / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    if FRONTEND_INDEX_FILE.exists():
        return FileResponse(FRONTEND_INDEX_FILE)
    raise HTTPException(status_code=404, detail="前端产物不存在，请先执行前端构建")
