# -*- coding: utf-8 -*-
"""FastAPI应用创建与配置。"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import create_tables
from backend.plugin_manager import PluginManager
from backend.ws_manager import WebSocketManager

plugin_manager = PluginManager()
ws_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    plugin_manager.discover_plugins()
    yield
    plugin_manager.cleanup()


def create_app() -> FastAPI:
    app = FastAPI(
        title="本地自动化平台",
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

    from backend.routes import system, plugins, auth as auth_route
    app.include_router(system.router, prefix="/api/system", tags=["系统"])
    app.include_router(plugins.router, prefix="/api/plugins", tags=["插件"])
    app.include_router(auth_route.router, prefix="/api/auth", tags=["授权"])

    from backend.routes.ws import router as ws_router
    app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])

    # 前端静态文件（生产环境由PyInstaller嵌入）
    frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
    if os.path.isdir(frontend_dist):
        # 挂载静态资源目录（js/css/images等）
        app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="static_assets")

        # SPA catch-all: 非API路由全部返回index.html，让前端router处理
        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            # API和WebSocket路由已被上面的router处理，不会到这里
            file_path = os.path.join(frontend_dist, full_path)
            if full_path and os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(frontend_dist, "index.html"))

    return app


app = create_app()
