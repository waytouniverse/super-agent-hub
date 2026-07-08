"""FastAPI 应用 + WebSocket 服务器"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .routes.engines import router as engines_router
from .routes.projects import router as projects_router
from .routes.sessions import router as sessions_router
from .routes.stats import router as stats_router
from .routes.files import router as files_router
from .routes.chat_ws import router as chat_ws_router
from .routes.team_ws import router as team_ws_router
from .session_store import init_db
from .config import load


if getattr(sys, "frozen", False):
    FRONTEND_DIR = Path(sys._MEIPASS) / "frontend" / "dist"
else:
    FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Agent Hub",
    description="统一 AI Agent 工作台 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(engines_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(team_ws_router)
app.include_router(chat_ws_router)

# 前端静态资源
HAS_FRONTEND = FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists()

if HAS_FRONTEND:
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

    @app.get("/")
    async def serve_root():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        # 不拦截 API 和 WebSocket 路由
        if path.startswith("api/") or path.startswith("ws/"):
            raise HTTPException(status_code=404)
        # 尝试直接返回静态文件
        file_path = FRONTEND_DIR / path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # SPA fallback
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        raise HTTPException(status_code=404)


def create_app() -> FastAPI:
    return app
