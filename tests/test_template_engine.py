# -*- coding: utf-8 -*-
"""template_engine 原子能力测试。"""
from backend.capabilities.template_engine import (
    substitute_placeholders, build_path, build_filename_pattern,
)


class TestSubstitutePlaceholders:
    def test_basic_replacement(self):
        assert substitute_placeholders("hello {name}", {"name": "world"}) == "hello world"

    def test_multiple_vars(self):
        result = substitute_placeholders("{a}/{b}", {"a": "x", "b": "y"})
        assert result == "x/y"

    def test_placeholder_map_chinese_to_english(self):
        tpl = "*{文件关键词}*发票*.*"
        pmap = {"{文件关键词}": "{PrimaryKeyword}"}
        result = substitute_placeholders(tpl, {"PrimaryKeyword": "ABC001"}, pmap)
        assert result == "*ABC001*发票*.*"

    def test_no_match_leaves_unchanged(self):
        assert substitute_placeholders("{unknown}", {}) == "{unknown}"


class TestBuildPath:
    def test_with_keyword(self):
        assert build_path("/data/{PathKeyword}/files", "202603") == "/data/202603/files"

    def test_override_takes_precedence(self):
        assert build_path("/template/path", "kw", override="/override") == "/override"

    def test_override_nan_ignored(self):
        result = build_path("/data/{PathKeyword}", "kw", override="nan")
        assert "kw" in result

    def test_override_empty_ignored(self):
        result = build_path("/data/{PathKeyword}", "kw", override="")
        assert "kw" in result

    def test_no_keyword(self):
        assert build_path("/data/static") == "/data/static"


class TestBuildFilenamePattern:
    def test_basic(self):
        result = build_filename_pattern("*{PrimaryKeyword}*发票*.*", "ABC", "发票")
        assert result == "*ABC*发票*.*"

    def test_with_doc_type(self):
        result = build_filename_pattern("*{PrimaryKeyword}*{DocumentType}*.*", "001", "报关单")
        assert result == "*001*报关单*.*"

    def test_empty_keyword(self):
        result = build_filename_pattern("*{PrimaryKeyword}*.*", "", "")
        assert result == "**.*"

    def test_dot_wildcard(self):
        """关键词为'.'时应视为通配，不是字面点号。"""
        import fnmatch
        pattern = build_filename_pattern("*{PrimaryKeyword}*合同*.*", ".", "合同")
        assert pattern == "**合同*.*"
        assert fnmatch.fnmatch("测试文件合同.xls", pattern)
        assert fnmatch.fnmatch("采购合同.pdf", pattern)
        assert not fnmatch.fnmatch("readme.txt", pattern)

    def test_dot_wildcard_simple(self):
        """简单模板 *{PrimaryKeyword}*.* + '.' 应匹配所有文件。"""
        import fnmatch
        pattern = build_filename_pattern("*{PrimaryKeyword}*.*", ".", "")
        assert fnmatch.fnmatch("任意文件名.xlsx", pattern)
        assert fnmatch.fnmatch("test.doc", pattern)
