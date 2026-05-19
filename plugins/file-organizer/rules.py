# -*- coding: utf-8 -*-
"""
规则解析模块 - 关键字解析与路径模板替换
"""
import os
import pandas as pd


def parse_structured_keywords(text):
    """解析结构化关键字文本为字典。

    格式: "发票:关键词1,关键词2;合同:关键词3"
    无冒号时归入 '_default' 组。
    """
    if not isinstance(text, str) or not text.strip():
        return {}
    text = text.strip()
    if ':' not in text:
        return {'_default': text}
    keyword_map = {}
    pairs = text.split(';')
    for pair in pairs:
        if ':' in pair:
            key, value = pair.split(':', 1)
            key, value = key.strip(), value.strip()
            if key and value:
                keyword_map[key] = value
    return keyword_map


def create_hyperlink_path(file_path):
    """返回文件路径的绝对路径字符串（用于GUI中打开文件）。"""
    if pd.isna(file_path):
        return ""
    return os.path.abspath(str(file_path))


def build_search_path(rule_path_template, path_keyword, override_path=None):
    """根据规则模板和路径关键字构建实际搜索路径。"""
    if override_path and str(override_path).strip():
        return str(override_path)
    if path_keyword is not None:
        return str(rule_path_template).replace("{PathKeyword}", str(path_keyword))
    return rule_path_template


def build_filename_pattern(pattern_template, primary_keyword, doc_type):
    """替换文件名模式中的占位符。"""
    result = pattern_template.replace("{PrimaryKeyword}", str(primary_keyword or ''))
    result = result.replace("{DocumentType}", str(doc_type or ''))
    return result
