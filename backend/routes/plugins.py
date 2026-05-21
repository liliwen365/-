# -*- coding: utf-8 -*-
"""插件API路由 — 异步执行 + 状态查询。"""
import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app import plugin_manager, ws_manager
from backend.database import SessionLocal, TaskHistoryModel, SettingModel
from backend.logger import logger
from backend.task_runner import TaskRunner

router = APIRouter()

task_runner = TaskRunner(ws_manager=ws_manager)


class ExecuteRequest(BaseModel):
    feature_id: str = ""
    params: dict = {}


class ConfigUpdate(BaseModel):
    config: dict


# --- 插件列表与详情 ---

@router.get("/installed")
def list_plugins():
    return {"plugins": plugin_manager.list_plugins()}


@router.get("/{name}/info")
def plugin_info(name: str):
    mf = plugin_manager.get_manifest(name)
    if not mf:
        raise HTTPException(404, f"插件 {name} 未安装")
    return mf.get_info()


# --- 插件配置 ---

@router.get("/{name}/config")
def get_config(name: str):
    db = SessionLocal()
    try:
        key = f"plugin_config_{name}"
        row = db.query(SettingModel).filter(SettingModel.key == key).first()
        if row and row.value:
            return json.loads(row.value)
        mf = plugin_manager.get_manifest(name)
        if mf:
            return _default_config(mf.get_info())
        return {}
    finally:
        db.close()


@router.put("/{name}/config")
def save_config(name: str, body: ConfigUpdate):
    db = SessionLocal()
    try:
        key = f"plugin_config_{name}"
        row = db.query(SettingModel).filter(SettingModel.key == key).first()
        value = json.dumps(body.config, ensure_ascii=False)
        if row:
            row.value = value
        else:
            db.add(SettingModel(key=key, value=value))
        db.commit()
    finally:
        db.close()
    return {"success": True}


# --- 模板 ---

@router.get("/{name}/templates/{template}")
def load_template(name: str, template: str):
    mf = plugin_manager.get_manifest(name)
    if not mf:
        raise HTTPException(404, f"插件 {name} 未安装")
    data = mf.get_template(template)
    if not data:
        raise HTTPException(404, f"模板 {template} 不存在")
    return data


# --- 异步执行 ---

@router.post("/{name}/execute")
async def execute_plugin(name: str, body: ExecuteRequest):
    p = plugin_manager.get_plugin(name)
    if not p:
        raise HTTPException(404, f"插件 {name} 未安装")

    validated = p.validate_params(body.params)
    params = {**validated, "feature_id": body.feature_id}

    try:
        task_id = await task_runner.start(p, params)
    except Exception as e:
        logger.error(f"启动插件 {name} 执行失败: {e}")
        raise HTTPException(500, f"启动执行失败: {e}")

    return {"task_id": task_id, "status": "pending"}


@router.get("/{name}/status")
def task_status(name: str, task_id: int):
    result = task_runner.get_status(task_id)
    if not result:
        raise HTTPException(404, f"任务 {task_id} 不存在")
    return result


@router.post("/{name}/cancel")
async def cancel_task(name: str, task_id: int):
    cancelled = await task_runner.cancel(task_id)
    if not cancelled:
        raise HTTPException(400, f"任务 {task_id} 无法取消（可能已完成）")
    return {"success": True, "task_id": task_id}


# --- 历史记录 ---

@router.get("/{name}/history")
def plugin_history(name: str, limit: int = 20):
    db = SessionLocal()
    try:
        rows = (
            db.query(TaskHistoryModel)
            .filter(TaskHistoryModel.plugin_name == name)
            .order_by(TaskHistoryModel.created_at.desc())
            .limit(limit)
            .all()
        )
        return {"history": [
            {
                "id": r.id, "status": r.status,
                "summary": r.progress_message or "",
                "duration_ms": r.duration_ms,
                "created_at": str(r.created_at),
                "finished_at": str(r.finished_at) if r.finished_at else "",
            }
            for r in rows
        ]}
    finally:
        db.close()


# --- 辅助 ---

def _default_config(info: dict) -> dict:
    config = {}
    for param in info.get("params", []):
        if param.get("type") == "table":
            config[param["name"]] = []
        else:
            config[param["name"]] = param.get("default", "")
    return config
