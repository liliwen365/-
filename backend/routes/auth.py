# -*- coding: utf-8 -*-
"""授权API路由。"""
from fastapi import APIRouter
from pydantic import BaseModel

from backend.auth import SecurityManager
from backend.database import SessionLocal, SettingModel

router = APIRouter()
security = SecurityManager()


class ActivateRequest(BaseModel):
    license_code: str


@router.get("/status")
def auth_status():
    db = SessionLocal()
    try:
        row = db.query(SettingModel).filter(SettingModel.key == "license_code").first()
        code = row.value if row else ""
    finally:
        db.close()

    if code:
        valid, msg = security.verify_license(code)
        return {"activated": valid, "message": msg, "machine_id": security.get_machine_id()}
    return {"activated": False, "message": "未激活", "machine_id": security.get_machine_id()}


@router.post("/activate")
def activate(req: ActivateRequest):
    valid, msg = security.verify_license(req.license_code)
    if valid:
        db = SessionLocal()
        try:
            row = db.query(SettingModel).filter(SettingModel.key == "license_code").first()
            if row:
                row.value = req.license_code
            else:
                db.add(SettingModel(key="license_code", value=req.license_code))
            db.commit()
        finally:
            db.close()
    return {"success": valid, "message": msg}


@router.get("/machine-id")
def get_machine_id():
    return {"machine_id": security.get_machine_id()}
