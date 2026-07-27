# -*- coding: utf-8 -*-
"""系统API路由。"""
import os
import platform
import subprocess
from fastapi import APIRouter
from pydantic import BaseModel as PydanticModel

from backend.config import settings, BUILD_COMMIT, BUILD_TIME
from backend.auth import SecurityManager
from backend.database import SessionLocal, TaskHistoryModel

router = APIRouter()
security = SecurityManager()


@router.get("/info")
def system_info():
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "build_commit": BUILD_COMMIT,
        "build_time": BUILD_TIME,
        "platform": platform.system(),
        "machine_id": security.get_machine_id(),
        "data_dir": settings.DATA_DIR,
        "log_dir": os.path.join(settings.DATA_DIR, "logs"),
    }


@router.get("/token")
def get_token():
    """前端首次加载时获取API token（仅限本地访问）。"""
    return {"token": settings.API_TOKEN}


class BrowseRequest(PydanticModel):
    path: str = ""
    type: str = "directory"  # directory | file


@router.post("/browse")
def browse_path(req: BrowseRequest):
    """返回指定路径下的目录内容，供前端路径选择器使用。"""
    target = req.path or os.path.expanduser("~")
    if not os.path.isdir(target):
        target = os.path.dirname(target) or os.path.expanduser("~")

    entries = []
    try:
        for name in sorted(os.listdir(target)):
            full = os.path.join(target, name)
            try:
                is_dir = os.path.isdir(full)
                if req.type == "directory" and not is_dir:
                    continue
                entries.append({
                    "name": name,
                    "path": full,
                    "is_dir": is_dir,
                })
            except PermissionError:
                continue
    except PermissionError:
        pass

    return {
        "current": target,
        "parent": os.path.dirname(target) if os.path.dirname(target) != target else None,
        "entries": entries,
    }


class OpenPathRequest(PydanticModel):
    path: str


@router.get("/health")
def health_check():
    import time as _time
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "platform": platform.system(),
        "machine_id": security.get_machine_id(),
    }


@router.get("/stats")
def system_stats():
    """仪表板统计数据。"""
    db = SessionLocal()
    try:
        from datetime import datetime, timezone, timedelta
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        total = db.query(TaskHistoryModel).count()
        today = db.query(TaskHistoryModel).filter(TaskHistoryModel.created_at >= today_start).count()
        success = db.query(TaskHistoryModel).filter(TaskHistoryModel.status == "success").count()
        failed = db.query(TaskHistoryModel).filter(TaskHistoryModel.status == "error").count()
        return {
            "total_tasks": total,
            "today_tasks": today,
            "success_count": success,
            "failed_count": failed,
            "success_rate": round(success / total * 100, 1) if total > 0 else 0,
        }
    finally:
        db.close()


@router.get("/diagnostic")
def diagnostic():
    """系统诊断信息 — 供"复制诊断信息"使用,报障时贴给开发者快速定位环境;
    同时保留插件加载诊断字段,供浏览器直接访问调试。"""
    from backend.app import plugin_manager
    import sys as _sys

    pm = plugin_manager
    loaded = list(pm._plugins.keys())
    manifests = {}
    load_errors = getattr(pm, '_load_errors', [])

    for name, mf in pm._manifests.items():
        manifests[name] = {
            "dir": mf.plugin_dir,
            "dir_exists": os.path.isdir(mf.plugin_dir),
            "files": os.listdir(mf.plugin_dir) if os.path.isdir(mf.plugin_dir) else [],
        }

    plugin_modules = {k: str(v) for k, v in _sys.modules.items() if '_plugin_' in k}

    # 最近 10 条任务,排查"扫不到/失败"时定位上下文
    recent_tasks = []
    db = SessionLocal()
    try:
        rows = db.query(TaskHistoryModel).order_by(TaskHistoryModel.id.desc()).limit(10).all()
        for r in rows:
            recent_tasks.append({
                "id": r.id,
                "plugin": r.plugin_name,
                "feature": r.feature_id or "",
                "status": r.status,
                "created": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                "duration_ms": r.duration_ms,
                "error": (r.error_traceback or "")[:200],
            })
    finally:
        db.close()

    return {
        # 版本与环境(报障对齐用)
        "version": settings.APP_VERSION,
        "build_commit": BUILD_COMMIT,
        "build_time": BUILD_TIME,
        "platform": platform.system(),
        "log_dir": os.path.join(settings.DATA_DIR, "logs"),
        "recent_tasks": recent_tasks,
        # 插件加载诊断(原有,保留)
        "plugins_loaded": loaded,
        "plugins_count": len(loaded),
        "plugins_dir": settings.PLUGINS_DIR,
        "plugins_dir_exists": os.path.isdir(settings.PLUGINS_DIR),
        "plugins_dir_contents": os.listdir(settings.PLUGINS_DIR) if os.path.isdir(settings.PLUGINS_DIR) else [],
        "manifests": manifests,
        "plugin_modules_in_sys": plugin_modules,
        "load_errors": load_errors,
        "data_dir": settings.DATA_DIR,
        "python_path_0": _sys.path[0] if _sys.path else "",
    }


@router.post("/open-folder")
def open_folder(req: OpenPathRequest):
    """在系统文件管理器中打开指定文件夹。"""
    path = req.path
    if not path or not os.path.isdir(path):
        return {"success": False, "message": f"路径不存在: {path}"}
    try:
        sys_plat = platform.system().lower()
        if sys_plat == "darwin":
            subprocess.Popen(["open", path])
        elif sys_plat == "windows":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}
