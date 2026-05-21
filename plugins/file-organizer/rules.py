# -*- coding: utf-8 -*-
"""规则解析模块 - 薄包装层，委托给平台 template_engine 能力"""
from backend.capabilities.template_engine import build_path as _build_path
from backend.capabilities.template_engine import build_filename_pattern as _build_pattern

_PLACEHOLDER_MAP = {
    "{路径关键词}": "{PathKeyword}",
    "{文件关键词}": "{PrimaryKeyword}",
    "{文件分类}": "{DocumentType}",
}


def build_search_path(rule_path_template, path_keyword, override_path=None):
    return _build_path(rule_path_template, path_keyword, override_path, _PLACEHOLDER_MAP)


def build_filename_pattern(pattern_template, primary_keyword, doc_type):
    return _build_pattern(pattern_template, primary_keyword, doc_type, _PLACEHOLDER_MAP)
