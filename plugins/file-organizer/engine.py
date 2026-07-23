# -*- coding: utf-8 -*-
"""扫描与复制引擎 - 编排平台原子能力"""
import os
import datetime
import concurrent.futures

import pandas as pd

from rules import build_search_path, build_filename_pattern
from backend.capabilities.file_scanner import scan_directory, ScanReport
from backend.capabilities.file_ops import copy_file, CopyResult
from backend.capabilities.progress import ParallelProgress

from backend.logger import logger


def _scan_one_task(task_row, active_rules, on_dir_progress=None):
    """扫描单个任务的所有规则，返回 (plan_records, task_update_info)。"""
    task_id = task_row['task_id']
    dest_root = task_row['dest_root']
    keywords = task_row.get('keywords', {})
    if isinstance(keywords, str):
        import json
        keywords = json.loads(keywords) if keywords else {}
    override_path = task_row.get('override_path')

    # 提取 _default 组的路径关键词（兼容原始脚本"不带冒号"写法）
    default_path_kw = []
    default_group = keywords.get('_default', {})
    if isinstance(default_group, dict):
        default_path_kw = default_group.get('path', [])
    elif isinstance(default_group, str):
        default_path_kw = [default_group]

    plan_records = []

    for _, rule_row in active_rules.iterrows():
        doc_type = rule_row['doc_type']
        rule_path_template = rule_row['search_path']

        type_keywords = keywords.get(doc_type, {})
        if isinstance(type_keywords, str):
            import json
            type_keywords = json.loads(type_keywords)

        file_kw_list = type_keywords.get('file', [])
        # 优先用当前分类的路径关键词，无则回退到 _default 组
        path_kw_list = type_keywords.get('path', []) or default_path_kw

        if not file_kw_list:
            continue
        if not path_kw_list:
            path_kw_list = [None]

        for path_keyword in path_kw_list:
            for filename_keyword in file_kw_list:
                final_search_path = build_search_path(rule_path_template, path_keyword, override_path)
                report = scan_directory(
                    final_search_path, rule_row['filename_pattern'],
                    pattern_builder=lambda p, _kw=filename_keyword, _dt=doc_type:
                        build_filename_pattern(p, _kw, _dt),
                    on_progress=on_dir_progress,
                )

                base_record = {
                    'task_id': task_id,
                    'doc_type': doc_type,
                    'rule_desc': f"路径: {path_keyword or '无'}, 文件: {filename_keyword}",
                    'user_action': ''
                }

                if report.error:
                    plan_records.append({**base_record, 'find_status': "查找失败", 'error_msg': report.error})
                else:
                    for f in report.files:
                        dest_sub = rule_row.get('dest_subfolder', '')
                        dest_dir = (
                            os.path.join(str(dest_root), str(task_id), str(dest_sub))
                            if pd.notna(dest_sub) and str(dest_sub).strip()
                            else os.path.join(str(dest_root), str(task_id))
                        )
                        plan_records.append({
                            **base_record,
                            'find_status': "已找到",
                            'copy_status': "待复制",
                            'source_path': f.path,
                            'dest_path': os.path.join(dest_dir, f.name),
                            'file_size': f.size,
                            'file_mtime': f.mtime,
                        })

    return plan_records, {
        'status': '规划完成待执行',
        'summary': f"于 {datetime.datetime.now().strftime('%H:%M')} 完成扫描"
    }


def scan_tasks(tasks_df, rules_df, on_progress=None):
    """扫描所有标记为执行的任务，生成执行计划。

    Args:
        tasks_df: 任务清单DataFrame
        rules_df: 规则库DataFrame
        on_progress: 回调函数 on_progress(current, total, task_id, eta_str)

    Returns: (updated_tasks_df, plan_df)
    """
    tasks_df = tasks_df.copy()
    scan_col = 'enabled_scan' if 'enabled_scan' in tasks_df.columns else 'enabled'
    tasks_to_scan = tasks_df[tasks_df[scan_col].apply(
        lambda x: str(x).upper() in ('Y', 'TRUE', '1') if pd.notna(x) else False
    )]
    active_rules = rules_df[rules_df['enabled'].apply(
        lambda x: str(x).upper() in ('Y', 'TRUE', '1') if pd.notna(x) else False
    )]

    if tasks_to_scan.empty or active_rules.empty:
        logger.info("没有需要扫描的任务或没有启用的规则")
        return tasks_df, pd.DataFrame()

    plan_records = []
    total_tasks = len(tasks_to_scan)
    logger.info(f"开始扫描 {total_tasks} 个任务，启用规则 {len(active_rules)} 条")
    max_workers = min(32, (os.cpu_count() or 1) + 4)

    task_items = list(tasks_to_scan.iterrows())

    # 目录级进度回调（节流：每50个目录报一次），让前端扫描中能看到进度，不"假卡住"
    dir_progress_cb = None
    if on_progress:
        _cnt = [0]
        def dir_progress_cb(root, scanned):
            _cnt[0] += 1
            if _cnt[0] % 50 == 0:
                try:
                    on_progress(0, 0, f"扫描中… 已比对 {scanned} 个文件", "")
                except Exception:
                    pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(_scan_one_task, row, active_rules, dir_progress_cb): (idx, row['task_id'])
            for idx, (_, row) in enumerate(task_items)
        }
        tracker = ParallelProgress(total=total_tasks, on_progress=on_progress)
        for future in concurrent.futures.as_completed(future_to_idx):
            df_idx, task_id = future_to_idx[future]
            tracker.record(task_id)
            try:
                records, update_info = future.result()
                plan_records.extend(records)
                real_idx = task_items[df_idx][0]
                tasks_df.loc[real_idx, ['status', 'scan_summary']] = (
                    update_info['status'], update_info['summary']
                )
            except Exception as exc:
                logger.error(f"任务 {task_id} 处理异常: {exc}")

    plan_df = pd.DataFrame(plan_records) if plan_records else pd.DataFrame()
    logger.info(f"扫描完成: 共生成 {len(plan_df)} 条执行计划")
    return tasks_df, plan_df


def execute_copy(tasks_df, plan_df, on_progress=None, retry_attempts=3, retry_delay=1):
    """执行文件复制。

    Args:
        tasks_df: 任务清单DataFrame
        plan_df: 执行计划DataFrame
        on_progress: 回调函数 on_progress(current, total, filename, eta_str)

    Returns: (updated_tasks_df, updated_plan_df)
    """
    tasks_df = tasks_df.copy()
    plan_df = plan_df.copy()

    plan_df['user_action'] = plan_df['user_action'].fillna('').astype(str).str.upper().str.strip()
    skip_mask = (plan_df['copy_status'] == '待复制') & (plan_df['user_action'].isin(['SKIP', '跳过']))
    plan_df.loc[skip_mask, ['copy_status', 'error_msg']] = '用户跳过', '用户手动选择跳过'

    items_to_copy = plan_df[plan_df['copy_status'] == '待复制']

    if not items_to_copy.empty:
        from backend.capabilities.file_ops import copy_files_parallel

        copy_items = [(row['source_path'], row['dest_path']) for _, row in items_to_copy.iterrows()]
        copy_indices = list(items_to_copy.index)

        results = copy_files_parallel(
            copy_items, on_progress=on_progress,
            retry_attempts=retry_attempts, retry_delay=retry_delay,
        )

        for i, result in enumerate(results):
            idx = copy_indices[i]
            plan_df.loc[idx, 'dest_path'] = result.message if result.status == "success" else ""
            plan_df.loc[idx, 'copy_status'] = '已复制' if result.status == "success" else '复制失败'
            plan_df.loc[idx, 'error_msg'] = result.message if result.status != "success" else ""

    # 更新任务状态
    tasks_df = tasks_df.set_index('task_id')
    for task_id, group in plan_df.groupby('task_id'):
        copied = (group['copy_status'] == '已复制').sum()
        status = "执行出错"
        if (copied + (group['copy_status'] == '用户跳过').sum()) == len(group):
            status = "已完成" if copied > 0 else "已跳过"
        elif copied > 0:
            status = "部分完成"
        scan_summary = f"执行于 {datetime.datetime.now().strftime('%H:%M')}, {copied}/{len(group)} 文件成功。"

        if task_id in tasks_df.index:
            tasks_df.loc[task_id, ['status', 'scan_summary']] = status, scan_summary
            if status == "已完成":
                for col in ['enabled_scan', 'enabled_copy', 'enabled']:
                    if col in tasks_df.columns:
                        tasks_df.loc[task_id, col] = False

    tasks_df = tasks_df.reset_index()

    copied_count = len(plan_df[plan_df['copy_status'] == '已复制'])
    failed_count = len(plan_df[plan_df['copy_status'] == '复制失败'])
    skipped_count = skip_mask.sum()
    logger.info(f"复制完成: 成功{copied_count}, 失败{failed_count}, 跳过{skipped_count}")

    return tasks_df, plan_df
