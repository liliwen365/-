# -*- coding: utf-8 -*-
"""定时任务调度 — 基于APScheduler 3.x，SQLite持久化。"""
import json
import traceback

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from backend.config import settings
from backend.logger import logger


def _parse_cron(cron_expr: str) -> dict:
    """将5字段cron表达式解析为APScheduler参数。
    格式: 分 时 日 月 周  →  minute, hour, day, month, day_of_week
    """
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"cron表达式需5个字段，实际: {cron_expr}")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


async def _execute_scheduled_task(plugin_name: str, feature_id: str, params_json: str):
    """定时任务触发时调用，通过task_runner执行插件。"""
    from backend.routes.plugins import task_runner
    from backend.app import plugin_manager

    p = plugin_manager.get_plugin(plugin_name)
    if not p:
        logger.error(f"调度执行失败: 插件 {plugin_name} 未找到")
        return

    params = json.loads(params_json)
    params["feature_id"] = feature_id

    try:
        validated = p.validate_params(params)
        task_id = await task_runner.start(p, validated)
        logger.info(f"定时任务已触发: {plugin_name}/{feature_id}, task_id={task_id}")
    except Exception as e:
        logger.error(f"调度执行失败: {plugin_name}/{feature_id}: {e}")


class AppScheduler:
    def __init__(self):
        self._scheduler = AsyncIOScheduler(
            jobstores={
                "default": SQLAlchemyJobStore(
                    url=f"sqlite:///{settings.DB_PATH}",
                    tablename="apscheduler_jobs",
                )
            },
        )

    def start(self):
        self._scheduler.start()
        logger.info("定时调度器已启动")

    def shutdown(self):
        self._scheduler.shutdown(wait=False)
        logger.info("定时调度器已关闭")

    async def add_schedule(self, schedule_id: int, plugin_name: str,
                           feature_id: str, cron_expr: str, params: dict):
        job = self._scheduler.add_job(
            _execute_scheduled_task,
            "cron",
            **_parse_cron(cron_expr),
            args=[plugin_name, feature_id, json.dumps(params, ensure_ascii=False)],
            id=f"schedule_{schedule_id}",
            replace_existing=True,
        )
        logger.info(f"添加定时任务: schedule_{schedule_id}, cron={cron_expr}")
        return job

    def remove_schedule(self, schedule_id: int):
        job_id = f"schedule_{schedule_id}"
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"移除定时任务: {job_id}")
        except Exception:
            pass

    def pause_schedule(self, schedule_id: int):
        self._scheduler.pause_job(f"schedule_{schedule_id}")

    def resume_schedule(self, schedule_id: int):
        self._scheduler.resume_job(f"schedule_{schedule_id}")

    def list_schedules(self) -> list[dict]:
        jobs = self._scheduler.get_jobs()
        return [
            {
                "job_id": j.id,
                "next_run": str(j.next_run_time) if j.next_run_time else None,
                "trigger": str(j.trigger),
            }
            for j in jobs
        ]


app_scheduler = AppScheduler()
