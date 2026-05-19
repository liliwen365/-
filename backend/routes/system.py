# -*- coding: utf-8 -*-
"""系统API路由。"""
import os
import platform
import subprocess
from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import settings
from backend.auth import SecurityManager

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


class OpenPathRequest(BaseModel):
    path: str


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
