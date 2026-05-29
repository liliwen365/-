# -*- coding: utf-8 -*-
"""模板替换引擎 - 从 rules.py 提取的通用占位符替换能力"""


def substitute_placeholders(template, variables, placeholder_map=None):
    """替换模板中的 {Key} 占位符。

    Args:
        template: 含 {Key} 占位符的字符串
        variables: {Key: value} 映射
        placeholder_map: 可选的别名映射，如 {"{旧名}": "{新名}"}
    """
    result = str(template)
    if placeholder_map:
        for old, new in placeholder_map.items():
            result = result.replace(old, new)
    for key, value in variables.items():
        result = result.replace(f"{{{key}}}", str(value))
    return result


def build_path(path_template, path_keyword=None, override=None, placeholder_map=None):
    """从模板构建实际路径，支持覆盖。

    当 override 有值时直接返回 override（忽略模板和关键词）。
    """
    if override and str(override).strip() and str(override) != 'nan':
        return str(override)
    variables = {}
    if path_keyword is not None:
        variables["PathKeyword"] = str(path_keyword)
    return substitute_placeholders(path_template, variables, placeholder_map)


def build_filename_pattern(pattern_template, primary_keyword="", doc_type="", placeholder_map=None):
    """从模板构建文件名匹配模式。

    当文件关键词为"."时表示通配（match all），
    *{PrimaryKeyword}* 变为 *，匹配任意文件。
    """
    # '.' 是通配符，等价于空字符串：*{PrimaryKeyword}* → ** → 等同于 *
    if primary_keyword == '.':
        primary_keyword = ''
    variables = {
        "PrimaryKeyword": str(primary_keyword or ''),
        "DocumentType": str(doc_type or ''),
    }
    return substitute_placeholders(pattern_template, variables, placeholder_map)
