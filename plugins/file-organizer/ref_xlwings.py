# -*- coding: utf-8 -*-
"""
文件整理系统 - xlwings核心引擎
- 进度显示: Excel底部状态栏
- 数据交换: 直接内存读写
- 功能增强: 路径和文件关键字按组配对搜索 (已修正)
"""
import sys
import os
import pandas as pd
import datetime
import tkinter as tk
from tkinter import messagebox
import fnmatch
import shutil
import glob
import concurrent.futures
import xlwings as xw
import time

# --- 全局常量 ---
APP_NAME = "文件整理系统-xlwings版"
TASKS_SHEET_NAME = "任务清单"
RULES_SHEET_NAME = "文件规则库"
PLAN_SHEET_NAME = "执行计划与结果"
SETTINGS_SHEET_NAME = "系统设置"

# --- 辅助函数 (无变动) ---
def update_status_bar(app, message):
    """安全地更新Excel状态栏"""
    try:
        app.status_bar = f"{APP_NAME}: {message}"
    except Exception:
        pass

def show_popup(title, message, type="info"):
    """使用Tkinter显示最终的弹窗消息"""
    try:
        root = tk.Tk()
        root.withdraw()
        if type == "info": messagebox.showinfo(title, message)
        elif type == "warning": messagebox.showwarning(title, message)
        elif type == "error": messagebox.showerror(title, message)
    except Exception:
        pass
    finally:
        if 'root' in locals() and root.winfo_exists():
            root.destroy()

def create_hyperlink_formula(file_path, link_text=None):
    if pd.isna(file_path): return ""
    abs_path = os.path.abspath(str(file_path))
    link_text = link_text if link_text is not None else os.path.basename(abs_path)
    return f'=HYPERLINK("{abs_path.replace("\"", "\"\"")}", "{str(link_text).replace("\"", "\"\"")}")'

def parse_structured_keywords(text):
    if not isinstance(text, str) or not text.strip(): return {}
    text = text.strip()
    if ':' not in text: return {'_default': text}
    keyword_map = {}
    pairs = text.split(';')
    for pair in pairs:
        if ':' in pair:
            key, value = pair.split(':', 1)
            key, value = key.strip(), value.strip()
            if key and value: keyword_map[key] = value
    return keyword_map

# --- 扫描部分的核心逻辑 ---
def find_matching_files(search_paths_str, filename_patterns_str, primary_keyword, doc_type):
    if pd.isna(search_paths_str) or pd.isna(filename_patterns_str): return [], "规则配置错误"
    all_found_files = []
    path_patterns = [p.strip() for p in str(search_paths_str).split(';') if p.strip()]
    expanded_search_paths = [p for pattern in path_patterns for p in (glob.glob(pattern) if any(c in pattern for c in '*?[') else [pattern])]
    filename_patterns = [p.strip() for p in str(filename_patterns_str).split(';') if p.strip()]
    for base_path in expanded_search_paths:
        if not os.path.isdir(base_path): continue
        for pattern in filename_patterns:
            final_pattern = pattern.replace("{PrimaryKeyword}", str(primary_keyword or '')).replace("{DocumentType}", str(doc_type or ''))
            for root, _, files in os.walk(base_path):
                for file_name in files:
                    if fnmatch.fnmatch(file_name, final_pattern): all_found_files.append(os.path.join(root, file_name))
    if not all_found_files: return [], "未找到匹配的文件。"
    return list(set(all_found_files)), None

def process_single_task(task_row_tuple, active_rules):
    """【核心修改】此函数已重构，以实现路径和文件关键字的“配对搜索”"""
    task_index, task_row = task_row_tuple
    task_id, dest_root = task_row['海关报关单ID'], task_row['目标存放根路径']
    
    # 1. 解析出两组结构化的关键字字典
    structured_path_keywords = parse_structured_keywords(task_row.get('路径关键词'))
    structured_filename_keywords = parse_structured_keywords(task_row.get('主要识别关键词'))
    
    override_path, local_plan_records = task_row.get('特定搜索路径'), []

    # 2. 外层循环遍历“文件规则库”中的每一条规则
    for _, rule_row in active_rules.iterrows():
        doc_type = rule_row['文件类型']  # 例如 '发票'
        rule_path_template = rule_row['源文件搜索路径']
        
        # 3. 使用规则的'文件类型'作为key，去任务的关键字中寻找对应的组
        filename_keywords_str = structured_filename_keywords.get(doc_type)
        
        # 如果当前规则的'文件类型'在任务的'主要识别关键词'中没有定义，则跳过此条规则
        if not filename_keywords_str:
            continue
            
        # 4. 寻找与之配对的“路径关键字”组
        #    - 优先使用同名组（如'发票'）
        #    - 若无，则回退到使用'_default'组
        path_keywords_str = structured_path_keywords.get(doc_type, structured_path_keywords.get('_default'))

        # 5. 将关键字字符串转换为列表
        filename_keyword_list = [k.strip() for k in str(filename_keywords_str).split(',') if k.strip()]
        path_keyword_list = [p.strip() for p in str(path_keywords_str or '').split(',') if p.strip()]

        # 如果路径关键字列表为空（意味着路径不依赖关键字），我们用[None]来确保循环至少执行一次
        if not path_keyword_list:
            path_keyword_list = [None]
        
        # 6. 执行“笛卡尔积”式的嵌套循环搜索
        for path_keyword in path_keyword_list:
            for filename_keyword in filename_keyword_list:
                # 构造搜索路径
                final_search_path = str(override_path) if pd.notna(override_path) and str(override_path).strip() else str(rule_path_template).replace("{PathKeyword}", str(path_keyword)) if path_keyword is not None else rule_path_template
                
                # 执行查找
                found_files, error_msg = find_matching_files(final_search_path, rule_row['文件名模式'], filename_keyword, doc_type)
                
                # 准备记录
                base_record = {'海关报关单ID': task_id, '文件类型': doc_type, '应用规则说明': f"规则 {rule_row.name + 2} (组: {doc_type}, 路径关键字: {path_keyword or '无'}, 文件关键字: {filename_keyword})", '用户确认操作': ''}
                
                if error_msg:
                    local_plan_records.append({**base_record, '查找状态': "查找失败", '错误信息/代码': error_msg})
                else:
                    for file_path in found_files:
                        dest_dir = os.path.join(str(dest_root), str(task_id), str(rule_row['目标子文件夹'])) if pd.notna(rule_row['目标子文件夹']) else os.path.join(str(dest_root), str(task_id))
                        local_plan_records.append({**base_record, '查找状态': "已找到", '复制状态': "待复制", '源文件完整路径': file_path, '(计划)目标文件路径': os.path.join(dest_dir, os.path.basename(file_path))})
    
    return local_plan_records, {'index': task_index, 'status': '规划完成待执行', 'summary': f"于 {datetime.datetime.now().strftime('%H:%M')} 完成扫描"}


# --- 执行复制部分的核心逻辑 ---
def copy_single_file(source_path, dest_path):
    """【核心修改】处理单个文件复制，增加了对文件占用的重试逻辑"""
    for attempt in range(3): # 最多尝试3次
        try:
            if pd.isna(source_path) or pd.isna(dest_path):
                return "failure", "配置错误：路径为空"
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(source_path, dest_path)
            return "success", create_hyperlink_formula(dest_path, "打开文件") # 成功后立刻返回
        except PermissionError:
            if attempt < 2: # 如果不是最后一次尝试
                time.sleep(1) # 等待1秒
                continue # 继续下一次尝试
            else: # 如果是最后一次尝试，则返回失败信息
                return "failure", "文件被占用，多次尝试后失败"
        except Exception as e:
            # 其他类型的错误，直接失败，不重试
            return "failure", f"复制错误: {e}"

# =================================================================================
# xlwings 可调用的主函数 (无变动)
# =================================================================================
def scan_files():
    """由VBA按钮调用的“扫描与规划”主函数"""
    book = xw.Book.caller()
    app = book.app
    update_status_bar(app, "开始扫描与规划...")

    try:
        # 1. 从Excel读取配置 (直接内存读取)
        update_status_bar(app, "正在读取任务清单和规则库...")
        tasks_sheet = book.sheets[TASKS_SHEET_NAME]
        rules_sheet = book.sheets[RULES_SHEET_NAME]
        tasks_df = tasks_sheet.range("A1").expand().options(pd.DataFrame, header=1, index=False).value
        rules_df = rules_sheet.range("A1").expand().options(pd.DataFrame, header=1, index=False).value

        # 2. 执行扫描核心逻辑
        tasks_to_scan = tasks_df[tasks_df['是否执行本次扫描'].astype(str).str.upper() == 'Y']
        active_rules = rules_df[rules_df['是否启用此规则'].astype(str).str.upper() == 'Y']
        if tasks_to_scan.empty or active_rules.empty:
            show_popup("提示", "没有标记为需要扫描的任务或没有启用的规则。", "info")
            update_status_bar(app, "就绪")
            return
        
        plan_records = []
        total_tasks = len(tasks_to_scan)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 1) + 4)) as executor:
            future_to_task = {executor.submit(process_single_task, row, active_rules): (i, row[1]['海关报关单ID']) for i, row in enumerate(tasks_to_scan.iterrows())}
            for i, future in enumerate(concurrent.futures.as_completed(future_to_task)):
                idx, task_id = future_to_task[future]
                update_status_bar(app, f"扫描中: {i + 1}/{total_tasks} - {task_id}")
                try:
                    records, update_info = future.result()
                    plan_records.extend(records)
                    tasks_df.loc[update_info['index'], ['处理状态', '扫描结果摘要']] = update_info['status'], update_info['summary']
                except Exception as exc:
                    update_status_bar(app, f"错误: 任务 {task_id} 处理异常 - {exc}")

        # 3. 将结果写回Excel (直接内存写入)
        update_status_bar(app, "扫描完成，正在将结果写入Excel...")
        plan_df = pd.DataFrame(plan_records) if plan_records else pd.DataFrame()
        
        plan_sheet = book.sheets[PLAN_SHEET_NAME]
        plan_sheet.clear_contents()
        if not plan_df.empty:
            plan_sheet.range("A1").options(index=False, header=True).value = plan_df
        
        tasks_sheet.clear_contents()
        tasks_sheet.range("A1").options(index=False, header=True).value = tasks_df
        
        # 4. 【核心修改】统计结果并显示最终弹窗
        total_count = len(plan_df)
        failed_count = 0
        if not plan_df.empty and '查找状态' in plan_df.columns:
            failed_count = len(plan_df[plan_df['查找状态'] == '查找失败'])

        update_status_bar(app, "扫描与规划完成！")
        summary_message = f"扫描与规划已完成！\n\n共生成 {total_count} 条执行计划。\n其中，查找失败 {failed_count} 条。"
        show_popup("操作完成", summary_message)

    except Exception as e:
        update_status_bar(app, f"发生严重错误: {e}")
        show_popup("严重错误", f"执行扫描时发生严重错误:\n{e}", "error")
    finally:
        update_status_bar(app, "就绪")


def execute_copy():
    """由VBA按钮调用的“执行复制”主函数"""
    book = xw.Book.caller()
    app = book.app
    update_status_bar(app, "开始执行文件复制...")

    try:
        # 1. 从Excel读取配置
        update_status_bar(app, "正在读取任务清单和执行计划...")
        tasks_sheet = book.sheets[TASKS_SHEET_NAME]
        plan_sheet = book.sheets[PLAN_SHEET_NAME]
        tasks_df = tasks_sheet.range("A1").expand().options(pd.DataFrame, header=1, index=False).value
        plan_df = plan_sheet.range("A1").expand().options(pd.DataFrame, header=1, index=False).value

        # 2. 执行复制核心逻辑
        plan_df['用户确认操作'] = plan_df['用户确认操作'].fillna('').astype(str).str.upper().str.strip()
        skip_mask = (plan_df['复制状态'] == '待复制') & (plan_df['用户确认操作'].isin(['SKIP', '跳过']))
        plan_df.loc[skip_mask, ['复制状态', '错误信息/代码']] = '用户跳过', '用户手动选择跳过'
        items_to_copy = plan_df[plan_df['复制状态'] == '待复制']
        
        if not items_to_copy.empty:
            total_files = len(items_to_copy)
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 1) + 4)) as executor:
                future_to_index = {executor.submit(copy_single_file, row['源文件完整路径'], row['(计划)目标文件路径']): (i, index) for i, (index, row) in enumerate(items_to_copy.iterrows())}
                for i, future in enumerate(concurrent.futures.as_completed(future_to_index)):
                    idx, index = future_to_index[future]
                    source_filename = os.path.basename(str(items_to_copy.loc[index, '源文件完整路径']))
                    update_status_bar(app, f"复制中: {i + 1}/{total_files} - {source_filename}")
                    try:
                        status, msg = future.result()
                        plan_df.loc[index, '(计划)目标文件路径'] = msg if status == "success" else ""
                        plan_df.loc[index, '复制状态'] = '已复制' if status == "success" else '复制失败'
                        plan_df.loc[index, '错误信息/代码'] = msg if status != "success" else ""
                    except Exception as exc:
                        plan_df.loc[index, ['复制状态', '错误信息/代码']] = '复制失败', f"线程异常: {exc}"
                        update_status_bar(app, f"错误: 文件 {source_filename} 复制出错 - {exc}")

        # 3. 更新任务清单状态
        update_status_bar(app, "复制完成，正在更新任务状态...")
        tasks_df = tasks_df.set_index('海关报关单ID')
        grouped = plan_df.groupby('海关报关单ID')
        for task_id, group in grouped:
            copied = (group['复制状态'] == '已复制').sum()
            status = "执行出错"
            if (copied + (group['复制状态'] == '用户跳过').sum()) == len(group): status = "已完成" if copied > 0 else "已跳过"
            elif copied > 0: status = "部分完成"
            summary = f"执行于 {datetime.datetime.now().strftime('%H:%M')}, {copied}/{len(group)} 文件成功。"
            path = ""
            if copied > 0 and task_id in tasks_df.index:
                path = create_hyperlink_formula(os.path.join(str(tasks_df.loc[task_id, '目标存放根路径']), str(task_id)), "打开文件夹")
            if task_id in tasks_df.index:
                tasks_df.loc[task_id, ['处理状态', '扫描结果摘要', '最终文件夹路径']] = status, summary, path
                # 【核心修改】如果任务已完成，则自动将扫描和复制标志都设置为'N'
                if status == "已完成":
                    cols_to_update = []
                    if '是否执行本次扫描' in tasks_df.columns:
                        cols_to_update.append('是否执行本次扫描')
                    if '是否执行本次复制' in tasks_df.columns:
                        cols_to_update.append('是否执行本次复制')
                    if cols_to_update:
                        tasks_df.loc[task_id, cols_to_update] = 'N'
        tasks_df = tasks_df.reset_index()

        # 4. 将结果写回Excel
        update_status_bar(app, "正在将最终结果写入Excel...")
        plan_sheet.clear_contents()
        plan_sheet.range("A1").options(index=False, header=True).value = plan_df
        tasks_sheet.clear_contents()
        tasks_sheet.range("A1").options(index=False, header=True).value = tasks_df
        
        copied_count = len(plan_df[plan_df['复制状态'] == '已复制'])
        failed_count = len(plan_df[plan_df['复制状态'] == '复制失败'])
        skipped_count = skip_mask.sum()
        summary_message = f"文件复制操作已完成！\n\n成功: {copied_count} 个, 失败: {failed_count} 个, 用户跳过: {skipped_count} 个"
        show_popup("操作完成", summary_message)

    except Exception as e:
        update_status_bar(app, f"发生严重错误: {e}")
        show_popup("严重错误", f"执行复制时发生严重错误:\n{e}", "error")
    finally:
        update_status_bar(app, "就绪")

if __name__ == "__main__":
    try:
        book_path = sys.argv[1]
        xw.Book(book_path).set_mock_caller()
        scan_files()
    except IndexError:
        print("请提供Excel文件的完整路径作为命令行参数来进行调试。")
