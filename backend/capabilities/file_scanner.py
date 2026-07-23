# -*- coding: utf-8 -*-
"""文件扫描能力 - 目录遍历 + fnmatch 模式匹配 + 并行扫描"""
import os
import fnmatch
import glob
import datetime
import concurrent.futures

from backend.logger import logger
from backend.config import settings
from backend.capabilities.progress import ParallelProgress


class ScanResult:
    """单个扫描到的文件。"""
    __slots__ = ('path', 'name', 'size', 'mtime')

    def __init__(self, path, name, size=0, mtime=""):
        self.path = path
        self.name = name
        self.size = size
        self.mtime = mtime


class ScanReport:
    """一次扫描的结果。"""
    def __init__(self, files=None, error=None):
        self.files = files or []
        self.error = error  # None 或错误消息字符串


def scan_directory(search_paths_str, filename_pattern,
                   path_builder=None, pattern_builder=None,
                   max_files=None, max_depth=None, on_progress=None):
    """扫描目录，查找匹配文件名模式的文件。

    Args:
        search_paths_str: 分号分隔的搜索路径（支持 glob 通配符）
        filename_pattern: fnmatch 文件名模式，支持分号分隔的多个模式
        path_builder: 可选，对每个展开路径做进一步替换
        pattern_builder: 可选，对文件名模式做进一步替换
        max_files: 最多收集文件数（默认 settings.SCAN_MAX_FILES），防 OOM/无限递归
        max_depth: os.walk 最大递归深度（默认 settings.SCAN_MAX_DEPTH），防扫整盘
        on_progress: 可选回调 (current_dir, scanned_count)，每处理一个目录触发

    Returns: ScanReport
    """
    if not search_paths_str or not filename_pattern:
        return ScanReport(error="路径或模式为空")

    if max_files is None:
        max_files = settings.SCAN_MAX_FILES
    if max_depth is None:
        max_depth = settings.SCAN_MAX_DEPTH

    path_patterns = [p.strip() for p in str(search_paths_str).split(';') if p.strip()]
    expanded = [
        p for pattern in path_patterns
        for p in (glob.glob(pattern) if any(c in pattern for c in '*?[') else [pattern])
    ]

    # 支持分号分隔的多个文件名模式
    raw_patterns = [p.strip() for p in str(filename_pattern).split(';') if p.strip()]
    if pattern_builder:
        final_patterns = [pattern_builder(p) for p in raw_patterns]
    else:
        final_patterns = raw_patterns

    all_files = []
    truncated = False
    for base_path in expanded:
        if path_builder:
            base_path = path_builder(base_path)
        if not os.path.isdir(base_path):
            logger.warning(f"搜索路径不存在或不可访问: {base_path}")
            continue
        logger.info(f"开始扫描 {base_path}（深度上限 {max_depth}, 文件上限 {max_files}）")
        base_depth = base_path.rstrip(os.sep).count(os.sep)
        for root, dirs, files in os.walk(base_path):
            # 深度剪枝：超过 max_depth 不再下钻子目录
            cur_depth = root.rstrip(os.sep).count(os.sep) - base_depth
            if cur_depth >= max_depth:
                dirs[:] = []
            # 进度回调：每个目录触发一次，让上层/前端知道在扫哪里
            if on_progress:
                try:
                    on_progress(root, len(all_files))
                except Exception:
                    pass
            for name in files:
                if any(fnmatch.fnmatch(name, pat) for pat in final_patterns):
                    fpath = os.path.join(root, name)
                    try:
                        fsize = os.path.getsize(fpath)
                        fmtime = datetime.datetime.fromtimestamp(
                            os.path.getmtime(fpath)
                        ).strftime('%Y-%m-%d %H:%M')
                    except OSError:
                        fsize, fmtime = 0, ""
                    all_files.append(ScanResult(fpath, name, fsize, fmtime))
                    if len(all_files) >= max_files:
                        truncated = True
                        break
            if truncated:
                break
        if truncated:
            break

    if truncated:
        logger.warning(f"达到文件上限 {max_files}，扫描已截断（搜索路径范围可能过大）")

    # 去重
    seen = set()
    unique = []
    for f in all_files:
        if f.path not in seen:
            seen.add(f.path)
            unique.append(f)

    logger.info(f"扫描完成: 匹配 {len(unique)} 个文件" + ("（已截断）" if truncated else ""))
    if not unique:
        return ScanReport(error="未找到匹配的文件")
    return ScanReport(files=unique)


def scan_directories_parallel(items, on_progress=None, max_workers=None):
    """并行扫描多个目录规格。

    Args:
        items: [dict] 每个含 scan_directory 所需参数
        on_progress: 回调 (current, total, item_id, eta_str)
        max_workers: 默认 min(32, cpu_count+4)

    Returns: list[ScanReport]
    """
    if not items:
        return []

    if max_workers is None:
        max_workers = min(32, (os.cpu_count() or 1) + 4)

    results = [None] * len(items)
    tracker = ParallelProgress(total=len(items), on_progress=on_progress)

    def _scan_one(item):
        return scan_directory(**item)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(_scan_one, item): i
            for i, item in enumerate(items)
        }
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as exc:
                results[idx] = ScanReport(error=str(exc))
            tracker.record(str(idx))

    return results
