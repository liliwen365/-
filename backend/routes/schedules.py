# -*- coding: utf-8 -*-
"""定时调度API路由。"""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app import plugin_manager
from backend.database import SessionLocal, ScheduleModel, TaskHistoryModel
from backend.logger import logger
from backend.scheduler import app_scheduler

router = APIRouter()


class ScheduleCreate(BaseModel):
    plugin_name: str
    feature_id: str = ""
    cron_expr: str
    params: dict = {}


@router.get("")
def list_schedules():
    db = SessionLocal()
    try:
        rows = db.query(ScheduleModel).order_by(ScheduleModel.created_at.desc()).all()
        aps_jobs = {j["job_id"]: j for j in app_scheduler.list_schedules()}
        return {"schedules": [
            {
                "id": r.id,
                "plugin_name": r.plugin_name,
                "feature_id": r.feature_id,
                "cron_expr": r.cron_expr,
                "params": json.loads(r.params_json) if r.params_json else {},
                "enabled": r.enabled,
                "last_run_at": str(r.last_run_at) if r.last_run_at else None,
                "next_run": aps_jobs.get(f"schedule_{r.id}", {}).get("next_run"),
                "created_at": str(r.created_at),
            }
            for r in rows
        ]}
    finally:
        db.close()


@router.post("")
async def create_schedule(body: ScheduleCreate):
    p = plugin_manager.get_plugin(body.plugin_name)
    if not p:
        raise HTTPException(404, f"插件 {body.plugin_name} 未安装")

    db = SessionLocal()
    try:
        sched = ScheduleModel(
            plugin_name=body.plugin_name,
            feature_id=body.feature_id,
            cron_expr=body.cron_expr,
            params_json=json.dumps(body.params, ensure_ascii=False),
        )
        db.add(sched)
        db.commit()
        db.refresh(sched)
        sched_id = sched.id
    finally:
        db.close()

    await app_scheduler.add_schedule(
        sched_id, body.plugin_name, body.feature_id, body.cron_expr, body.params
    )

    return {"id": sched_id, "status": "created"}


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int):
    db = SessionLocal()
    try:
        sched = db.query(ScheduleModel).get(schedule_id)
        if not sched:
            raise HTTPException(404, f"调度 {schedule_id} 不存在")
        db.delete(sched)
        db.commit()
    finally:
        db.close()

    app_scheduler.remove_schedule(schedule_id)
    return {"success": True}


@router.put("/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int):
    db = SessionLocal()
    try:
        sched = db.query(ScheduleModel).get(schedule_id)
        if not sched:
            raise HTTPException(404, f"调度 {schedule_id} 不存在")
        sched.enabled = not sched.enabled
        db.commit()
        enabled = sched.enabled
        cron_expr = sched.cron_expr
        plugin_name = sched.plugin_name
        feature_id = sched.feature_id
        params = json.loads(sched.params_json) if sched.params_json else {}
    finally:
        db.close()

    if enabled:
        await app_scheduler.add_schedule(
            schedule_id, plugin_name, feature_id, cron_expr, params
        )
    else:
        app_scheduler.pause_schedule(schedule_id)

    return {"enabled": enabled}


@router.get("/{schedule_id}/runs")
def schedule_runs(schedule_id: int, limit: int = 10):
    db = SessionLocal()
    try:
        sched = db.query(ScheduleModel).get(schedule_id)
        if not sched:
            raise HTTPException(404, f"调度 {schedule_id} 不存在")
        rows = (
            db.query(TaskHistoryModel)
            .filter(TaskHistoryModel.plugin_name == sched.plugin_name)
            .order_by(TaskHistoryModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return {"runs": [
            {
                "id": r.id, "status": r.status,
                "message": r.progress_message,
                "duration_ms": r.duration_ms,
                "created_at": str(r.created_at),
            }
            for r in rows
        ]}
    finally:
        db.close()
