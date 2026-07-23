# -*- coding: utf-8 -*-
"""文件操作能力 - 复制/移动/重命名（带重试和并行执行）"""
import os
import shutil
import time
import concurrent.futures

from backend.logger import logger
from backend.capabilities.progress import ParallelProgress


class CopyResult:
    """单文件操作结果。"""
    __slots__ = ('source', 'dest', 'status', 'message')

    def __init__(self, source, dest, status, message=""):
        self.source = source
        self.dest = dest
        self.status = status  # "success" | "failure" | "skipped"
        self.message = message


def copy_file(source, dest, retry_attempts=3, retry_delay=1.0):
    """复制单个文件，自动创建目标目录，支持重试。

    Returns: CopyResult
    """
    for attempt in range(retry_attempts):
        try:
            if not source or not dest:
                return CopyResult(source, dest, "failure", "路径为空")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(source, dest)
            return CopyResult(source, dest, "success", dest)
        except PermissionError:
            if attempt < retry_attempts - 1:
                time.sleep(retry_delay)
            else:
                return CopyResult(source, dest, "failure", "文件被占用，多次尝试后失败")
        except Exception as e:
            return CopyResult(source, dest, "failure", str(e))


def copy_files_parallel(items, on_progress=None, retry_attempts=3, retry_delay=1.0, max_workers=None):
    """并行复制多个文件。

    Args:
        items: [(source, dest), ...] 列表
        on_progress: 回调 (current, total, filename, eta_str)
        max_workers: 默认 min(32, cpu_count+4)

    Returns: list[CopyResult]
    """
    if not items:
        return []

    if max_workers is None:
        max_workers = min(32, (os.cpu_count() or 1) + 4)

    logger.info(f"开始复制 {len(items)} 个文件")

    results = [None] * len(items)
    tracker = ParallelProgress(total=len(items), on_progress=on_progress)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(copy_file, src, dst, retry_attempts, retry_delay): i
            for i, (src, dst) in enumerate(items)
        }
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                src, dst = items[idx]
                results[idx] = CopyResult(src, dst, "failure", str(exc))
            tracker.record(os.path.basename(str(items[idx][0])))

    logger.info(f"复制完成: {len(items)} 个文件")
    return results


def move_file(source, dest, retry_attempts=3, retry_delay=1.0):
    """移动单个文件，带重试。"""
    for attempt in range(retry_attempts):
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(source, dest)
            return CopyResult(source, dest, "success", dest)
        except PermissionError:
            if attempt < retry_attempts - 1:
                time.sleep(retry_delay)
            else:
                return CopyResult(source, dest, "failure", "文件被占用，多次尝试后失败")
        except Exception as e:
            return CopyResult(source, dest, "failure", str(e))
