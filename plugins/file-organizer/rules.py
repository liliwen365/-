# -*- coding: utf-8 -*-
"""规则解析模块 - 路径模板替换"""
import pandas as pd


def build_search_path(rule_path_template, path_keyword, override_path=None):
    """根据规则模板和路径关键字构建实际搜索路径。"""
    if override_path and str(override_path).strip() and str(override_path) != 'nan':
        return str(override_path)
    if path_keyword is not None:
        return str(rule_path_template).replace("{PathKeyword}", str(path_keyword))
    return rule_path_template


def build_filename_pattern(pattern_template, primary_keyword, doc_type):
    """替换文件名模式中的占位符。"""
    result = pattern_template.replace("{PrimaryKeyword}", str(primary_keyword or ''))
    result = result.replace("{DocumentType}", str(doc_type or ''))
    return result
