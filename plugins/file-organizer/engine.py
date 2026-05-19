# -*- coding: utf-8 -*-
"""扫描与复制引擎 - 核心业务逻辑"""
import os
import time
import shutil
import fnmatch
import glob
import datetime
import concurrent.futures

import pandas as pd

from rules import build_search_path, build_filename_pattern
import logging
logger = logging.getLogger(__name__)


def format_eta(seconds):
    """格式化剩余时间。"""
    if seconds <= 0:
        return ""
    minutes, secs = divmod(int(seconds), 60)
    if minutes > 0:
        return f"{minutes}分{secs}秒"
    return f"{secs}秒"


def find_matching_files(search_paths_str, filename_patterns_str, primary_keyword, doc_type):
    """在搜索路径中查找匹配文件名模式的文件。

    Returns: (found_files_list, error_message_or_None)
    """
    if pd.isna(search_paths_str) or pd.isna(filename_patterns_str):
        return [], "规则配置错误"

    all_found_files = []
    path_patterns = [p.strip() for p in str(search_paths_str).split(';') if p.strip()]
    expanded_search_paths = [
        p for pattern in path_patterns
        for p in (glob.glob(pattern) if any(c in pattern for c in '*?[') else [pattern])
    ]
    filename_patterns = [p.strip() for p in str(filename_patterns_str).split(';') if p.strip()]

    for base_path in expanded_search_paths:
        if not os.path.isdir(base_path):
            continue
        for pattern in filename_patterns:
            final_pattern = build_filename_pattern(pattern, primary_keyword, doc_type)
            for root, _, files in os.walk(base_path):
                for file_name in files:
                    if fnmatch.fnmatch(file_name, final_pattern):
                        all_found_files.append(os.path.join(root, file_name))

    if not all_found_files:
        return [], "未找到匹配的文件。"
    return list(set(all_found_files)), None


def process_single_task(task_index, task_row, active_rules):
    """处理单个任务：遍历规则，搜索文件，生成执行计划记录。

    keywords格式: {"发票": {"path": ["kw1"], "file": ["fk1"]}, ...}
    """
    task_id = task_row['task_id']
    dest_root = task_row['dest_root']
    keywords = task_row.get('keywords', {})
    if isinstance(keywords, str):
        import json
        keywords = json.loads(keywords) if keywords else {}
    override_path = task_row.get('override_path')
    local_plan_records = []

    for _, rule_row in active_rules.iterrows():
        doc_type = rule_row['doc_type']
        rule_path_template = rule_row['search_path']

        type_keywords = keywords.get(doc_type, {})
        if isinstance(type_keywords, str):
            import json
            type_keywords = json.loads(type_keywords)

        file_kw_list = type_keywords.get('file', [])
        path_kw_list = type_keywords.get('path', [])

        if not file_kw_list:
            continue

        if not path_kw_list:
            path_kw_list = [None]

        for path_keyword in path_kw_list:
            for filename_keyword in file_kw_list:
                final_search_path = build_search_path(rule_path_template, path_keyword, override_path)
                found_files, error_msg = find_matching_files(
                    final_search_path, rule_row['filename_pattern'], filename_keyword, doc_type
                )
                base_record = {
                    'task_id': task_id,
                    'doc_type': doc_type,
                    'rule_desc': f"路径: {path_keyword or '无'}, 文件: {filename_keyword}",
                    'user_action': ''
                }

                if error_msg:
                    local_plan_records.append({
                        **base_record, 'find_status': "查找失败", 'error_msg': error_msg
                    })
                else:
                    for file_path in found_files:
                        dest_sub = rule_row.get('dest_subfolder', '')
                        dest_dir = (
                            os.path.join(str(dest_root), str(task_id), str(dest_sub))
                            if pd.notna(dest_sub) and str(dest_sub).strip()
                            else os.path.join(str(dest_root), str(task_id))
                        )
                        # 获取文件大小和修改时间用于前端展示
                        try:
                            fsize = os.path.getsize(file_path)
                            fmtime = datetime.datetime.fromtimestamp(
                                os.path.getmtime(file_path)
                            ).strftime('%Y-%m-%d %H:%M')
                        except OSError:
                            fsize, fmtime = 0, ''
                        local_plan_records.append({
                            **base_record,
                            'find_status': "已找到",
                            'copy_status': "待复制",
                            'source_path': file_path,
                            'dest_path': os.path.join(dest_dir, os.path.basename(file_path)),
                            'file_size': fsize,
                            'file_mtime': fmtime,
                        })

    return local_plan_records, {
        'index': task_index,
        'status': '规划完成待执行',
        'summary': f"于 {datetime.datetime.now().strftime('%H:%M')} 完成扫描"
    }


def copy_single_file(source_path, dest_path, retry_attempts=3, retry_delay=1):
    """复制单个文件，支持重试。

    Returns: (status, message)  status="success"/"failure"
    """
    for attempt in range(retry_attempts):
        try:
            if pd.isna(source_path) or pd.isna(dest_path):
                return "failure", "配置错误：路径为空"
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(source_path, dest_path)
            return "success", dest_path
        except PermissionError:
            if attempt < retry_attempts - 1:
                time.sleep(retry_delay)
            else:
                return "failure", "文件被占用，多次尝试后失败"
        except Exception as e:
            return "failure", f"复制错误: {e}"


def scan_tasks(tasks_df, rules_df, on_progress=None):
    """扫描所有标记为执行的任务，生成执行计划。

    Args:
        tasks_df: 任务清单DataFrame
        rules_df: 规则库DataFrame
        on_progress: 回调函数 on_progress(current, total, task_id, eta_str)

    Returns: (updated_tasks_df, plan_df)
    """
    tasks_df = tasks_df.copy()
    # enabled: 支持布尔值和Y/N字符串
    tasks_to_scan = tasks_df[tasks_df['enabled'].apply(
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
    start_time = time.time()
    max_workers = min(32, (os.cpu_count() or 1) + 4)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(process_single_task, i, row[1], active_rules): (i, row[1]['task_id'])
            for i, row in enumerate(tasks_to_scan.iterrows())
        }
        for i, future in enumerate(concurrent.futures.as_completed(future_to_task)):
            idx, task_id = future_to_task[future]
            elapsed = time.time() - start_time
            avg_time = elapsed / (i + 1)
            eta = format_eta(avg_time * (total_tasks - (i + 1)))

            if on_progress:
                on_progress(i + 1, total_tasks, task_id, eta)

            try:
                records, update_info = future.result()
                plan_records.extend(records)
                tasks_df.loc[update_info['index'], ['status', 'scan_summary']] = (
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
        total_files = len(items_to_copy)
        start_time = time.time()
        max_workers = min(32, (os.cpu_count() or 1) + 4)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(
                    copy_single_file, row['source_path'], row['dest_path'],
                    retry_attempts, retry_delay
                ): (i, index)
                for i, (index, row) in enumerate(items_to_copy.iterrows())
            }
            for i, future in enumerate(concurrent.futures.as_completed(future_to_index)):
                idx, index = future_to_index[future]
                source_filename = os.path.basename(str(items_to_copy.loc[index, 'source_path']))
                elapsed = time.time() - start_time
                avg_time = elapsed / (i + 1)
                eta = format_eta(avg_time * (total_files - (i + 1)))

                if on_progress:
                    on_progress(i + 1, total_files, source_filename, eta)

                try:
                    status, msg = future.result()
                    plan_df.loc[index, 'dest_path'] = msg if status == "success" else ""
                    plan_df.loc[index, 'copy_status'] = '已复制' if status == "success" else '复制失败'
                    plan_df.loc[index, 'error_msg'] = msg if status != "success" else ""
                except Exception as exc:
                    plan_df.loc[index, ['copy_status', 'error_msg']] = '复制失败', f"线程异常: {exc}"

    # 更新任务状态
    tasks_df = tasks_df.set_index('task_id')
    grouped = plan_df.groupby('task_id')
    for task_id, group in grouped:
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
                tasks_df.loc[task_id, 'enabled'] = False

    tasks_df = tasks_df.reset_index()

    copied_count = len(plan_df[plan_df['copy_status'] == '已复制'])
    failed_count = len(plan_df[plan_df['copy_status'] == '复制失败'])
    skipped_count = skip_mask.sum()
    logger.info(f"复制完成: 成功{copied_count}, 失败{failed_count}, 跳过{skipped_count}")

    return tasks_df, plan_df
