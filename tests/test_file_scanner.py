# -*- coding: utf-8 -*-
"""file_scanner 原子能力测试。"""
import os
import pytest

from backend.capabilities.file_scanner import scan_directory, ScanReport


class TestScanDirectory:
    def test_finds_matching_files(self, tmp_tree):
        report = scan_directory(str(tmp_tree / "source"), "*.pdf")
        assert report.error is None
        paths = [f.path for f in report.files]
        assert any("发票_001" in p for p in paths)

    def test_multiple_patterns_semicolon(self, tmp_tree):
        report = scan_directory(str(tmp_tree / "source"), "*.pdf;*.txt")
        assert report.error is None
        paths = [f.path for f in report.files]
        assert any("发票_001" in p for p in paths)
        assert any("其他文件" in p for p in paths)

    def test_single_pattern_no_match(self, tmp_tree):
        report = scan_directory(str(tmp_tree / "source"), "*.xyz")
        assert report.error is not None

    def test_empty_path(self):
        report = scan_directory("", "*.pdf")
        assert report.error is not None

    def test_empty_pattern(self, tmp_tree):
        report = scan_directory(str(tmp_tree / "source"), "")
        assert report.error is not None

    def test_nonexistent_dir(self):
        report = scan_directory("/nonexistent/path/12345", "*.pdf")
        assert report.error is not None

    def test_dedup(self, tmp_tree):
        """同一路径用两个模式都匹配到，只出现一次。"""
        report = scan_directory(str(tmp_tree / "source"), "发票_001.pdf;发票*.*")
        assert report.error is None
        inv001 = [f for f in report.files if "发票_001" in f.path]
        assert len(inv001) == 1

    def test_subdirectory_walk(self, tmp_tree):
        report = scan_directory(str(tmp_tree / "source"), "发票_003.pdf")
        assert report.error is None
        assert any("subdir" in f.path for f in report.files)

    def test_file_metadata(self, tmp_tree):
        report = scan_directory(str(tmp_tree / "source"), "发票_001.pdf")
        assert report.error is None
        f = report.files[0]
        assert f.size > 0
        assert f.mtime  # 非空时间字符串

    def test_glob_expansion(self, tmp_tree):
        """搜索路径含通配符时自动展开。"""
        report = scan_directory(str(tmp_tree / "sour*"), "*.pdf")
        assert report.error is None

    def test_pattern_builder_callback(self, tmp_tree):
        report = scan_directory(
            str(tmp_tree / "source"),
            "*{kw}*.*",
            pattern_builder=lambda p: p.replace("{kw}", "发票_001"),
        )
        assert report.error is None
        assert any("发票_001" in f.path for f in report.files)

    def test_semicolon_pattern_both_match(self, tmp_tree):
        """两个模式各自匹配不同文件，结果合并。"""
        report = scan_directory(str(tmp_tree / "source"), "发票*.pdf;报关单*.pdf")
        assert report.error is None
        paths = [f.path for f in report.files]
        assert any("发票" in p for p in paths)
        assert any("报关单" in p for p in paths)
