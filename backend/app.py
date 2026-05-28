# -*- coding: utf-8 -*-
"""FastAPI应用创建与配置。"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
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

    from backend.scheduler import app_scheduler

    app_scheduler.start()
    await _restore_schedules()

    yield

    from backend.scheduler import app_scheduler as sched

    sched.shutdown()
    plugin_manager.cleanup()
    from backend.routes.plugins import task_runner

    task_runner.shutdown()


async def _restore_schedules():
    """启动时从数据库恢复已启用的定时任务。"""
    from backend.database import SessionLocal, ScheduleModel
    from backend.scheduler import app_scheduler
    import json

    db = SessionLocal()
    try:
        rows = db.query(ScheduleModel).filter(ScheduleModel.enabled == True).all()
        for r in rows:
            try:
                params = json.loads(r.params_json) if r.params_json else {}
                await app_scheduler.add_schedule(
                    r.id, r.plugin_name, r.feature_id, r.cron_expr, params
                )
            except Exception as e:
                from backend.logger import logger

                logger.error(f"恢复调度 schedule_{r.id} 失败: {e}")
    finally:
        db.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="本地自动化平台",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://localhost:{settings.PORT}",
            f"http://127.0.0.1:{settings.PORT}",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def token_auth(request: Request, call_next):
        path = request.url.path
        # 不需要认证的路径
        if (
            path.startswith("/docs")
            or path.startswith("/redoc")
            or path == "/openapi.json"
        ):
            return await call_next(request)
        if path.startswith("/assets") or path.startswith("/ws/"):
            return await call_next(request)
        # API路径验证token
        if path.startswith("/api/"):
            # 公开端点：不需要认证
            public_paths = [
                "/api/system/info",
                "/api/system/token",
                "/api/system/health",
                "/api/auth/activate",
            ]
            if path in public_paths:
                return await call_next(request)
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if token != settings.API_TOKEN:
                query_token = request.query_params.get("token", "")
                if query_token != settings.API_TOKEN:
                    return Response(status_code=401, content="Unauthorized")
        return await call_next(request)

    from backend.routes import system, plugins, auth as auth_route

    app.include_router(system.router, prefix="/api/system", tags=["系统"])
    app.include_router(plugins.router, prefix="/api/plugins", tags=["插件"])
    app.include_router(auth_route.router, prefix="/api/auth", tags=["授权"])

    from backend.routes.schedules import router as schedules_router

    app.include_router(schedules_router, prefix="/api/schedules", tags=["定时调度"])

    from backend.routes.ws import router as ws_router

    app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])

    # 前端静态文件（生产环境由PyInstaller嵌入）
    from backend.utils.resource_path import resource_path

    frontend_dist = resource_path("frontend/dist")
    if os.path.isdir(frontend_dist):
        # 挂载静态资源目录（js/css/images等）
        app.mount(
            "/assets",
            StaticFiles(directory=os.path.join(frontend_dist, "assets")),
            name="static_assets",
        )

        # SPA catch-all: 非API路由全部返回index.html，让前端router处理
        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            # API和WebSocket路由已被上面的router处理，不会到这里
            file_path = os.path.join(frontend_dist, full_path)
            if full_path and os.path.isfile(file_path):
                resp = FileResponse(file_path)
            else:
                resp = FileResponse(os.path.join(frontend_dist, "index.html"))
            resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp

    return app


app = create_app()
