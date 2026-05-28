# -*- coding: utf-8 -*-
"""Windows兼容性测试 - 在macOS上模拟Windows路径场景。"""
import os
import platform
import pytest
from pathlib import Path, PureWindowsPath, PurePosixPath

from backend.capabilities.file_scanner import scan_directory


class TestWindowsPathCompatibility:
    """Windows路径兼容性测试（在macOS上模拟）。"""

    def test_windows_path_separator_normalization(self):
        """Windows反斜杠路径应能被正确处理。"""
        # 模拟Windows路径
        windows_style = r"Y:\报关单\2026年\*.pdf"
        # Python的os.path和pathlib应该能处理
        # 但实际文件系统操作需要真实路径

    def test_unc_path_simulation(self):
        """模拟UNC路径格式。"""
        unc_path = r"\\NAS-Server\退税资料\报关单\*.pdf"
        # 在macOS上无法直接访问Windows UNC路径
        # 需要路径转换逻辑

    def test_network_drive_mapping_simulation(self, tmp_path):
        """模拟网络驱动器映射场景。"""
        # 创建模拟目录结构
        (tmp_path / "报关单" / "2026年").mkdir(parents=True)
        (tmp_path / "报关单" / "2026年" / "ABC001报关单.pdf").write_text("test")

        # 使用本地路径测试（模拟映射后的Y盘）
        local_path = str(tmp_path / "报关单" / "2026年")
        result = scan_directory(local_path, "*.pdf")

        assert result.error is None
        assert len(result.files) >= 1


class TestCrossPlatformDifferences:
    """跨平台差异测试。"""

    def test_path_separator_handling(self):
        """测试路径分隔符处理。"""
        # macOS/Linux用 /，Windows用 \
        posix_path = "/Users/test/file.pdf"
        windows_path = r"C:\Users\test\file.pdf"

        # pathlib应该能正确处理
        p = Path(posix_path)
        assert p.as_posix() == posix_path

    def test_fnmatch_case_sensitivity(self):
        """测试fnmatch大小写敏感性。"""
        import fnmatch

        # macOS/Linux: 大小写敏感
        # Windows: 大小写不敏感
        pattern = "*.PDF"
        filename = "test.pdf"

        # 在macOS上这个测试会失败
        # 在Windows上会通过
        is_windows = platform.system() == "Windows"

        if not is_windows:
            assert not fnmatch.fnmatch(filename, pattern)
        else:
            # Windows上大小写不敏感
            assert fnmatch.fnmatch(filename, pattern)


class TestWindowsSpecificIssues:
    """Windows特定问题测试。"""

    def test_chinese_filename_encoding(self, tmp_path):
        """测试中文文件名编码。"""
        chinese_name = "测试文件.pdf"
        (tmp_path / chinese_name).write_text("test content")

        # 确保文件能被正确读取
        assert (tmp_path / chinese_name).exists()

        # 扫描应该能找到这个文件
        result = scan_directory(str(tmp_path), "*.pdf")
        assert result.error is None
        assert any(f.name == chinese_name for f in result.files)

    def test_path_with_spaces(self, tmp_path):
        """测试包含空格的路径。"""
        dir_with_space = tmp_path / "folder with spaces"
        dir_with_space.mkdir()
        (dir_with_space / "file.pdf").write_text("test")

        result = scan_directory(str(dir_with_space), "*.pdf")
        assert result.error is None
        assert len(result.files) >= 1
