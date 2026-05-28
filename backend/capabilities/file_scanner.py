# -*- coding: utf-8 -*-
"""文件扫描能力 - 目录遍历 + fnmatch 模式匹配 + 并行扫描"""
import os
import fnmatch
import glob
import concurrent.futures

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
                   path_builder=None, pattern_builder=None):
    """扫描目录，查找匹配文件名模式的文件。

    Args:
        search_paths_str: 分号分隔的搜索路径（支持 glob 通配符）
        filename_pattern: fnmatch 文件名模式，支持分号分隔的多个模式
        path_builder: 可选，对每个展开路径做进一步替换
        pattern_builder: 可选，对文件名模式做进一步替换

    Returns: ScanReport
    """
    if not search_paths_str or not filename_pattern:
        return ScanReport(error="路径或模式为空")

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
    for base_path in expanded:
        if path_builder:
            base_path = path_builder(base_path)
        if not os.path.isdir(base_path):
            continue
        for root, _, files in os.walk(base_path):
            for name in files:
                if any(fnmatch.fnmatch(name, pat) for pat in final_patterns):
                    fpath = os.path.join(root, name)
                    try:
                        import datetime
                        fsize = os.path.getsize(fpath)
                        fmtime = datetime.datetime.fromtimestamp(
                            os.path.getmtime(fpath)
                        ).strftime('%Y-%m-%d %H:%M')
                    except OSError:
                        fsize, fmtime = 0, ""
                    all_files.append(ScanResult(fpath, name, fsize, fmtime))

    # 去重
    seen = set()
    unique = []
    for f in all_files:
        if f.path not in seen:
            seen.add(f.path)
            unique.append(f)

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
