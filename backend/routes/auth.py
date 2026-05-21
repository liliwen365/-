# -*- coding: utf-8 -*-
"""授权API路由。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import SecurityManager
from backend.database import get_db, SettingModel

router = APIRouter()
security = SecurityManager()


class ActivateRequest(BaseModel):
    license_code: str


@router.get("/status")
def auth_status(db: Session = Depends(get_db)):
    row = db.query(SettingModel).filter(SettingModel.key == "license_code").first()
    code = row.value if row else ""

    if code:
        valid, msg = security.verify_license(code)
        return {"activated": valid, "message": "已授权" if valid else "授权无效", "machine_id": security.get_machine_id()}
    return {"activated": False, "message": "未激活", "machine_id": security.get_machine_id()}


@router.post("/activate")
def activate(req: ActivateRequest, db: Session = Depends(get_db)):
    valid, msg = security.verify_license(req.license_code)
    if valid:
        row = db.query(SettingModel).filter(SettingModel.key == "license_code").first()
        if row:
            row.value = req.license_code
        else:
            db.add(SettingModel(key="license_code", value=req.license_code))
        db.commit()
    return {"success": valid, "message": msg}


@router.get("/machine-id")
def get_machine_id():
    return {"machine_id": security.get_machine_id()}
