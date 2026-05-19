# -*- coding: utf-8 -*-
"""规则解析模块 - 路径模板替换"""
# 占位符映射：中文→英文（兼容旧模板）
_PLACEHOLDER_MAP = {
    "{路径关键词}": "{PathKeyword}",
    "{文件关键词}": "{PrimaryKeyword}",
    "{文件分类}": "{DocumentType}",
}


def _normalize_placeholders(template: str) -> str:
    """将中文占位符统一为英文内部格式。"""
    for cn, en in _PLACEHOLDER_MAP.items():
        template = template.replace(cn, en)
    return template


def build_search_path(rule_path_template, path_keyword, override_path=None):
    """根据规则模板和路径关键字构建实际搜索路径。"""
    if override_path and str(override_path).strip() and str(override_path) != 'nan':
        return str(override_path)
    template = _normalize_placeholders(str(rule_path_template))
    if path_keyword is not None:
        return template.replace("{PathKeyword}", str(path_keyword))
    return template


def build_filename_pattern(pattern_template, primary_keyword, doc_type):
    """替换文件名模式中的占位符。

    特殊处理：当文件关键词为"."时，`*{PrimaryKeyword}*`变为`*.*`，
    匹配所有含扩展名的文件（即该目录下所有文件）。
    """
    result = _normalize_placeholders(str(pattern_template))
    kw = str(primary_keyword or '')
    result = result.replace("{PrimaryKeyword}", kw)
    result = result.replace("{DocumentType}", str(doc_type or ''))
    return result
