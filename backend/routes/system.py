# -*- coding: utf-8 -*-
"""系统API路由。"""
import platform
from fastapi import APIRouter

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
