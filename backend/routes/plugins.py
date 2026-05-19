# -*- coding: utf-8 -*-
"""插件API路由。"""
import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app import plugin_manager, ws_manager
from backend.database import SessionLocal, TaskHistoryModel, SettingModel
from backend.logger import logger

router = APIRouter()


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
    p = plugin_manager.get_plugin(name)
    if not p:
        raise HTTPException(404, f"插件 {name} 未安装")
    return p.get_info()


# --- 插件配置 ---

@router.get("/{name}/config")
def get_config(name: str):
    db = SessionLocal()
    try:
        key = f"plugin_config_{name}"
        row = db.query(SettingModel).filter(SettingModel.key == key).first()
        if row and row.value:
            return json.loads(row.value)
        # 返回默认值
        p = plugin_manager.get_plugin(name)
        if p:
            return _default_config(p.get_info())
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
    p = plugin_manager.get_plugin(name)
    if not p:
        raise HTTPException(404, f"插件 {name} 未安装")
    data = p.get_template(template)
    if not data:
        raise HTTPException(404, f"模板 {template} 不存在")
    return data


# --- 执行 ---

@router.post("/{name}/execute")
async def execute_plugin(name: str, body: ExecuteRequest):
    p = plugin_manager.get_plugin(name)
    if not p:
        raise HTTPException(404, f"插件 {name} 未安装")

    validated = p.validate_params(body.params)

    # 记录任务
    db = SessionLocal()
    task = TaskHistoryModel(
        plugin_name=name, feature_id=body.feature_id,
        status="running", params_json=json.dumps(body.params, ensure_ascii=False),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    task_id = task.id
    db.close()

    # 进度回调（engine同步调用，4个参数: current, total, message/id, eta）
    def on_progress(current, total, message="", eta=""):
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(
                    ws_manager.send_progress(name, current, total, str(message), str(eta))
                )
            else:
                loop.run_until_complete(
                    ws_manager.send_progress(name, current, total, str(message), str(eta))
                )
        except Exception:
            pass

    # 执行（同步，后续改为子进程）
    try:
        result = p.execute(validated, progress_callback=on_progress)
        status = result.get("status", "success")
        summary = result.get("summary", "")
    except Exception as e:
        logger.error(f"插件 {name} 执行异常: {e}")
        status, summary, result = "error", str(e), {}

    # 更新任务
    db = SessionLocal()
    t = db.query(TaskHistoryModel).get(task_id)
    if t:
        t.status = status
        t.result_json = json.dumps(result, ensure_ascii=False)
        if status != "running":
            from datetime import datetime, timezone
            t.finished_at = datetime.now(timezone.utc)
        db.commit()
    db.close()

    return {"task_id": task_id, "status": status, "summary": summary, "result": result}


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
                "id": r.id, "status": r.status, "summary": r.result_json[:200] if r.result_json else "",
                "created_at": str(r.created_at), "finished_at": str(r.finished_at) if r.finished_at else "",
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
