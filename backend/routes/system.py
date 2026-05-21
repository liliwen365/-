# -*- coding: utf-8 -*-
"""系统API路由。"""
import os
import platform
import subprocess
from fastapi import APIRouter
from pydantic import BaseModel as PydanticModel

from backend.config import settings
from backend.auth import SecurityManager
from backend.database import SessionLocal, TaskHistoryModel

router = APIRouter()
security = SecurityManager()


@router.get("/info")
def system_info():
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "platform": platform.system(),
        "machine_id": security.get_machine_id(),
        "data_dir": settings.DATA_DIR,
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
