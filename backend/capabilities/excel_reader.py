# -*- coding: utf-8 -*-
"""Excel/CSV 灵活列映射解析能力 - 不同数据源用关键词匹配自动映射列名"""
import csv
import io
import os

import pandas as pd


def _match_columns(df_columns, column_mapping):
    """用关键词包含匹配将 DataFrame 列名映射到标准字段名。

    Args:
        df_columns: DataFrame 的列名列表
        column_mapping: {"标准字段名": "关键词" 或 ["关键词1", ...]}
            例: {"date": "交易日期"} 或 {"date": ["交易日期", "日期", "记账日期"]}

    Returns:
        {"标准字段名": 实际列名} 的映射（只包含匹配到的字段）
    """
    result = {}
    used_cols = set()
    for std_name, hints in column_mapping.items():
        if isinstance(hints, str):
            hints = [hints]
        for hint in hints:
            for col in df_columns:
                if col in used_cols:
                    continue
                if hint in str(col):
                    result[std_name] = col
                    used_cols.add(col)
                    break
            if std_name in result:
                break
    return result


def read_excel(file_path, column_mapping, sheet=0, skip_rows=0, encoding=None):
    """读取 Excel/CSV，用关键词映射自动匹配列名。

    Args:
        file_path: 文件路径（.xlsx/.xls/.csv）
        column_mapping: {"标准字段名": "关键词" 或 ["关键词1", ...]}
        sheet: Excel sheet 索引或名称
        skip_rows: 跳过前N行（银行流水常有表头区域）
        encoding: 文件编码（CSV 默认自动检测，可强制指定如 'gbk'）

    Returns:
        list[dict] 每行一个字典，key 为标准字段名。
        空行自动跳过。空值转为 None。
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.csv':
        enc = encoding or _detect_csv_encoding(file_path)
        df = pd.read_csv(file_path, skiprows=skip_rows, encoding=enc)
    elif ext in ('.xlsx', '.xls', '.xlsm'):
        df = pd.read_excel(file_path, sheet_name=sheet, skiprows=skip_rows)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")

    col_map = _match_columns(list(df.columns), column_mapping)

    if not col_map:
        raise ValueError(
            f"未能匹配任何列名。文件列名: {list(df.columns)}，"
            f"映射关键词: {list(column_mapping.keys())}"
        )

    records = []
    for _, row in df.iterrows():
        record = {}
        has_value = False
        for std_name, actual_col in col_map.items():
            val = row.get(actual_col)
            if pd.notna(val) and str(val).strip():
                record[std_name] = _clean_value(val)
                has_value = True
            else:
                record[std_name] = None
        if has_value:
            records.append(record)

    return records, col_map


def detect_columns(file_path, known_mappings, skip_rows=0, encoding=None):
    """自动检测文件列名，返回推荐映射。

    用于前端预览：展示文件实际列名和推荐的标准字段名对应关系。

    Args:
        file_path: 文件路径
        known_mappings: {"标准字段名": "关键词"} 的全局映射池
        skip_rows: 跳过行数
        encoding: 文件编码

    Returns:
        {
            "columns": ["实际列名1", ...],  # 文件中所有列名
            "suggested": {"标准字段名": "实际列名"},  # 推荐映射
            "unmapped": ["实际列名1", ...],  # 未映射的列名
            "preview": [  # 前5行数据预览
                {"实际列名1": "值", ...},
            ]
        }
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.csv':
        enc = encoding or _detect_csv_encoding(file_path)
        df = pd.read_csv(file_path, skiprows=skip_rows, encoding=enc, nrows=5)
    else:
        df = pd.read_excel(file_path, skiprows=skip_rows, nrows=5)

    actual_columns = list(df.columns)
    suggested = _match_columns(actual_columns, known_mappings)
    mapped_actual = set(suggested.values())
    unmapped = [c for c in actual_columns if c not in mapped_actual]

    preview = []
    for _, row in df.iterrows():
        preview.append({col: _clean_value(row[col]) for col in actual_columns})

    return {
        "columns": actual_columns,
        "suggested": suggested,
        "unmapped": unmapped,
        "preview": preview,
    }


def _detect_csv_encoding(file_path):
    """检测 CSV 文件编码（银行系统常见 GBK）。"""
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(4096)
        raw.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        return 'gbk'


def _clean_value(val):
    """清理单元格值：去空白、统一类型。"""
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    if not s or s == 'nan' or s == 'NaN':
        return None
    # 尝试转数字（银行金额常有千分位逗号）
    s_no_comma = s.replace(',', '').replace('，', '')
    try:
        return float(s_no_comma)
    except ValueError:
        return s
