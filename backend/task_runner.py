# -*- coding: utf-8 -*-
"""插件任务执行引擎 — 异步后台执行 + 进程隔离。"""
import asyncio
import json
import multiprocessing
import os
import time
import traceback
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

from backend.database import SessionLocal, TaskHistoryModel
from backend.logger import logger


def _subprocess_entry(plugin_module_path, plugin_dir, module_name, class_name,
                      params_json, queue, task_id):
    """在子进程中执行插件。模块级函数，可被pickle。"""
    import sys
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    module = __import__(module_name)
    plugin_class = getattr(module, class_name)
    instance = plugin_class()
    instance.plugin_dir = plugin_dir

    params = json.loads(params_json)

    def progress_cb(current, total, message="", eta=""):
        try:
            queue.put((task_id, int(current), int(total), str(message), str(eta)))
        except Exception:
            pass

    try:
        result = instance.execute(params, progress_callback=progress_cb)
        queue.put((task_id, -1, -1, "__done__", json.dumps(result, ensure_ascii=False)))
    except Exception as e:
        queue.put((task_id, -1, -1, "__error__", traceback.format_exc()))


class TaskRunner:
    """异步插件任务执行器。"""

    def __init__(self, ws_manager=None):
        self._ws_manager = ws_manager
        self._executor: ProcessPoolExecutor | None = None
        self._progress_queue: multiprocessing.Queue | None = None
        self._active_tasks: dict[int, asyncio.Task] = {}
        self._poll_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _ensure_executor(self):
        if self._executor is None:
            self._executor = ProcessPoolExecutor(max_workers=2)
            self._progress_queue = multiprocessing.Queue()

    async def start(self, plugin_instance, params: dict) -> int:
        """异步启动插件执行，立即返回task_id。"""
        self._ensure_executor()

        if self._loop is None:
            self._loop = asyncio.get_running_loop()

        if self._poll_task is None or self._poll_task.done():
            self._poll_task = self._loop.create_task(self._poll_progress())

        db = SessionLocal()
        try:
            task = TaskHistoryModel(
                plugin_name=plugin_instance.manifest.get("name", ""),
                feature_id=params.get("feature_id", ""),
                status="pending",
                params_json=json.dumps(params, ensure_ascii=False),
                progress_percent=0,
                progress_message="排队中...",
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            task_id = task.id
        finally:
            db.close()

        atask = self._loop.create_task(
            self._run_in_subprocess(plugin_instance, params, task_id)
        )
        self._active_tasks[task_id] = atask

        return task_id

    async def _run_in_subprocess(self, plugin_instance, params: dict, task_id: int):
        """在子进程中执行插件并跟踪结果。"""
        start_time = time.time()
        manifest = plugin_instance.manifest
        entry = manifest.get("entry", "")
        module_name, class_name = entry.split(":", 1)
        plugin_dir = plugin_instance.plugin_dir

        self._update_task(task_id, status="running", progress_message="执行中...")

        try:
            params_json = json.dumps(params, ensure_ascii=False)
            future = self._executor.submit(
                _subprocess_entry,
                os.path.dirname(os.path.abspath(__file__)),
                plugin_dir, module_name, class_name,
                params_json, self._progress_queue, task_id,
            )

            while not future.done():
                await asyncio.sleep(0.3)

            result_json = None
            error_tb = None
            try:
                future.result()
                # 从队列尾部取结果
                result_json = self._drain_result(task_id)
            except Exception as e:
                error_tb = traceback.format_exc()
                logger.error(f"任务 {task_id} 执行异常: {e}")

            elapsed_ms = int((time.time() - start_time) * 1000)

            if error_tb:
                self._update_task(
                    task_id, status="error",
                    progress_message="执行失败",
                    error_traceback=error_tb,
                    duration_ms=elapsed_ms,
                )
            elif result_json:
                result = json.loads(result_json)
                self._update_task(
                    task_id, status=result.get("status", "success"),
                    result_json=result_json,
                    progress_percent=100,
                    progress_message=result.get("summary", "完成"),
                    duration_ms=elapsed_ms,
                )
            else:
                self._update_task(task_id, status="error", progress_message="无返回结果",
                                  duration_ms=elapsed_ms)

        except asyncio.CancelledError:
            self._update_task(task_id, status="cancelled", progress_message="已取消")
        except Exception as e:
            self._update_task(task_id, status="error", progress_message=str(e),
                              error_traceback=traceback.format_exc())

        self._active_tasks.pop(task_id, None)

    def _drain_result(self, task_id: int) -> str | None:
        """从队列中取指定task_id的完成结果。"""
        result = None
        while not self._progress_queue.empty():
            try:
                tid, cur, total, msg, eta = self._progress_queue.get_nowait()
                if tid == task_id and msg == "__done__":
                    result = eta
                elif tid == task_id and msg == "__error__":
                    return None
            except Exception:
                break
        return result

    async def _poll_progress(self):
        """轮询进度队列并推送WebSocket。"""
        while True:
            try:
                while not self._progress_queue.empty():
                    try:
                        task_id, current, total, message, eta = (
                            self._progress_queue.get_nowait()
                        )
                        if message in ("__done__", "__error__"):
                            continue
                        percent = round(current / total * 100, 1) if total > 0 else 0
                        self._update_task(
                            task_id,
                            progress_percent=percent,
                            progress_message=message,
                        )
                        if self._ws_manager and self._loop:
                            try:
                                await self._ws_manager.send_progress(
                                    "", current, total, message, eta
                                )
                            except Exception:
                                pass
                    except Exception:
                        break
            except Exception:
                pass
            await asyncio.sleep(0.2)

    async def cancel(self, task_id: int) -> bool:
        """取消正在执行的任务。"""
        atask = self._active_tasks.get(task_id)
        if atask and not atask.done():
            atask.cancel()
            return True
        return False

    def get_status(self, task_id: int) -> dict | None:
        """查询任务当前状态。"""
        db = SessionLocal()
        try:
            t = db.query(TaskHistoryModel).get(task_id)
            if not t:
                return None
            return {
                "task_id": t.id,
                "status": t.status,
                "progress_percent": t.progress_percent,
                "progress_message": t.progress_message,
                "summary": "",
                "result": json.loads(t.result_json) if t.result_json else None,
                "created_at": str(t.created_at),
                "finished_at": str(t.finished_at) if t.finished_at else None,
                "duration_ms": t.duration_ms,
            }
        finally:
            db.close()

    def _update_task(self, task_id: int, **kwargs):
        """更新数据库中的任务记录。"""
        db = SessionLocal()
        try:
            t = db.query(TaskHistoryModel).get(task_id)
            if not t:
                return
            for k, v in kwargs.items():
                if hasattr(t, k):
                    setattr(t, k, v)
            if kwargs.get("status") in ("success", "error", "cancelled"):
                t.finished_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as e:
            logger.error(f"更新任务 {task_id} 状态失败: {e}")
        finally:
            db.close()

    def shutdown(self):
        if self._executor:
            self._executor.shutdown(wait=False)
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
