# -*- coding: utf-8 -*-
"""并行进度追踪能力 - 从 engine.py 提取的通用进度工具"""
import time


def format_eta(seconds):
    """格式化剩余时间为中文可读字符串。"""
    if seconds <= 0:
        return ""
    minutes, secs = divmod(int(seconds), 60)
    if minutes > 0:
        return f"{minutes}分{secs}秒"
    return f"{secs}秒"


class ParallelProgress:
    """并行任务进度追踪器。

    用法:
        tracker = ParallelProgress(total=100, on_progress=callback)
        # 在 as_completed 循环中:
        tracker.record(item_id)
    """

    def __init__(self, total, on_progress=None):
        self.total = total
        self.on_progress = on_progress
        self._start_time = time.time()
        self._completed = 0

    def record(self, item_id=""):
        """记录一个完成的任务，触发进度回调。"""
        self._completed += 1
        if self.on_progress:
            elapsed = time.time() - self._start_time
            avg = elapsed / self._completed if self._completed > 0 else 0
            eta = format_eta(avg * (self.total - self._completed))
            self.on_progress(self._completed, self.total, item_id, eta)
