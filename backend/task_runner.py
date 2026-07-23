# -*- coding: utf-8 -*-
"""插件任务执行引擎 — 异步后台执行 + 进程隔离。

每任务独立 multiprocessing.Process（替代原 ProcessPoolExecutor），支持：
- 取消即强杀（terminate→kill），不再"假取消"
- wall-clock 超时强杀（settings.TASK_TIMEOUT_SEC），防永久卡死/池耗尽
"""
import asyncio
import json
import multiprocessing
import os
import time
import traceback
from datetime import datetime, timezone
from multiprocessing.managers import SyncManager

from backend.config import settings
from backend.database import SessionLocal, TaskHistoryModel
from backend.logger import logger

_manager: SyncManager | None = None


def _get_manager() -> SyncManager:
    global _manager
    if _manager is None:
        _manager = multiprocessing.Manager()
    return _manager


def _subprocess_entry(plugin_module_path, plugin_dir, module_name, class_name,
                      params_json, queue, task_id):
    """在子进程中执行插件。模块级函数，可被pickle。"""
    import importlib.util
    import sys
    # 确保backend包可导入（插件可能import backend.capabilities）
    backend_dir = plugin_module_path
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    # plugin_dir在最前面，使插件内部import优先找到插件目录
    if plugin_dir in sys.path:
        sys.path.remove(plugin_dir)
    sys.path.insert(0, plugin_dir)

    module_file = os.path.join(plugin_dir, f"{module_name}.py")
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

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
    """异步插件任务执行器。每任务独立子进程，可取消（强杀）+ 超时强杀。"""

    def __init__(self, ws_manager=None):
        self._ws_manager = ws_manager
        self._progress_queue: multiprocessing.Queue | None = None
        self._active_tasks: dict[int, asyncio.Task] = {}           # task_id -> 轮询协程
        self._task_processes: dict[int, multiprocessing.Process] = {}  # task_id -> 子进程
        self._poll_task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._results: dict[int, str] = {}      # task_id -> result_json
        self._errors: dict[int, str] = {}       # task_id -> error_traceback

    def _ensure_queue(self):
        if self._progress_queue is None:
            self._progress_queue = _get_manager().Queue()

    @staticmethod
    def _terminate_process(p: multiprocessing.Process):
        """终止子进程：terminate → join(2) → 仍存活则 kill。"""
        try:
            if p.is_alive():
                p.terminate()
                p.join(2)
                if p.is_alive():
                    p.kill()
                    p.join(2)
        except Exception as e:
            logger.error(f"终止子进程失败: {e}")

    async def start(self, plugin_instance, params: dict) -> int:
        """异步启动插件执行，立即返回task_id。"""
        self._ensure_queue()

        # event loop 可能在测试隔离或运行时重建后关闭；若沿用旧 loop 会抛
        # "Event loop is closed"。检测后重新绑定，并废弃挂在旧 loop 上的 poll_task。
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.get_running_loop()
            self._poll_task = None

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
        """启动独立子进程执行插件，等待 完成 / 超时 / 取消。"""
        start_time = time.time()
        manifest = plugin_instance.manifest
        entry = manifest.get("entry", "")
        module_name, class_name = entry.split(":", 1)
        plugin_dir = plugin_instance.plugin_dir

        self._update_task(task_id, status="running", progress_message="执行中...")

        params_json = json.dumps(params, ensure_ascii=False)
        p = multiprocessing.Process(
            target=_subprocess_entry,
            args=(os.path.dirname(os.path.abspath(__file__)),
                  plugin_dir, module_name, class_name,
                  params_json, self._progress_queue, task_id),
        )
        # daemon=True：主进程退出时自动清理子进程，防僵尸。
        # 代价：daemon 进程内不能再 spawn 子进程（当前插件均用线程池，不受影响）。
        p.daemon = True
        p.start()
        self._task_processes[task_id] = p
        logger.info(f"任务 {task_id} 已启动子进程 pid={p.pid}")

        timeout = settings.TASK_TIMEOUT_SEC
        try:
            while p.is_alive():
                await asyncio.sleep(0.3)
                if time.time() - start_time > timeout:
                    logger.warning(
                        f"任务 {task_id} 超时（>{timeout}秒），强制终止 pid={p.pid}"
                    )
                    self._terminate_process(p)
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    self._update_task(
                        task_id, status="error",
                        progress_message=f"执行超时（超过 {timeout} 秒），已强制终止",
                        error_traceback=(
                            f"TaskTimeout: 任务执行超过 {timeout} 秒被强制终止。\n"
                            "常见原因：搜索路径范围过大、网络盘无响应、或插件死循环。"
                        ),
                        duration_ms=elapsed_ms,
                    )
                    return

            # 子进程已结束 —— 给 _poll_progress 一点时间把队列里的 done/error 落到内存字典
            await asyncio.sleep(0.3)
            result_json = self._results.pop(task_id, None)
            error_tb = self._errors.pop(task_id, None)
            elapsed_ms = int((time.time() - start_time) * 1000)

            if error_tb:
                logger.error(f"任务 {task_id} 执行失败:\n{error_tb}")
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
                logger.error(f"任务 {task_id} 无返回结果（子进程退出但未产出结果）")
                self._update_task(
                    task_id, status="error", progress_message="无返回结果",
                    error_traceback="子进程退出但未返回任何结果（可能被外部信号终止）。",
                    duration_ms=elapsed_ms,
                )
        except asyncio.CancelledError:
            # 前端点取消 → cancel() 取消本协程 → 在此强杀子进程并标记已取消
            logger.info(f"任务 {task_id} 被取消，终止子进程 pid={getattr(p, 'pid', '?')}")
            self._terminate_process(p)
            self._update_task(task_id, status="cancelled", progress_message="已取消")
        except Exception as e:
            logger.error(f"任务 {task_id} 执行异常: {e}")
            self._terminate_process(p)
            self._update_task(
                task_id, status="error", progress_message=str(e),
                error_traceback=traceback.format_exc(),
                duration_ms=int((time.time() - start_time) * 1000),
            )
        finally:
            self._task_processes.pop(task_id, None)
            self._active_tasks.pop(task_id, None)

    async def _poll_progress(self):
        """轮询进度队列并推送WebSocket。"""
        while True:
            try:
                while not self._progress_queue.empty():
                    try:
                        task_id, current, total, message, eta = (
                            self._progress_queue.get_nowait()
                        )
                        if message == "__done__":
                            self._results[task_id] = eta
                            continue
                        if message == "__error__":
                            self._errors[task_id] = eta
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
        """取消正在执行的任务：取消协程（触发强杀子进程）+ 进程残留兜底 + 诊断日志。"""
        atask = self._active_tasks.get(task_id)
        p = self._task_processes.get(task_id)
        logger.info(
            f"cancel(task={task_id}): 协程={'有(done)' if atask and atask.done() else '有(running)' if atask else '无'}, "
            f"进程={'有(alive)' if (p and p.is_alive()) else '无/不alive'}"
        )
        if atask and not atask.done():
            # 取消协程 → 触发 _run_in_subprocess 的 CancelledError 分支 → terminate 子进程
            atask.cancel()
            return True
        if p and p.is_alive():
            # 协程已结束但进程残留（异常情况）—— 强制终止并标记
            self._terminate_process(p)
            self._update_task(task_id, status="cancelled",
                              progress_message="已取消（强制终止残留进程）")
            logger.info(f"cancel(task={task_id}): 残留进程已强制终止")
            return True
        # 既无活跃协程也无存活进程 —— 查数据库看任务真实状态（便于诊断"取消失败"原因）
        db = SessionLocal()
        try:
            t = db.query(TaskHistoryModel).get(task_id)
            db_status = t.status if t else "(记录不存在)"
        finally:
            db.close()
        logger.warning(
            f"cancel(task={task_id}) 找不到活跃协程/进程，数据库状态={db_status}"
            f"{'（任务可能已完成，前端进度未刷新）' if db_status in ('success', 'error', 'cancelled') else ''}"
        )
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
                "error_traceback": t.error_traceback or "",
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
        """程序退出时强杀所有存活子进程，防僵尸。"""
        for task_id, p in list(self._task_processes.items()):
            logger.info(f"关闭时终止任务 {task_id} 子进程 pid={getattr(p, 'pid', '?')}")
            self._terminate_process(p)
        self._task_processes.clear()
        self._active_tasks.clear()
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
