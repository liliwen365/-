# -*- coding: utf-8 -*-
"""跨平台路径处理工具。"""
import os
import platform
from pathlib import Path, PureWindowsPath, PurePosixPath


class PathUtils:
    """跨平台路径处理工具类。"""

    @staticmethod
    def normalize_path(path_str):
        """标准化路径格式（转换为当前系统格式）。"""
        if not path_str:
            return path_str

        # 检测是否是Windows路径
        if '\\' in path_str or (len(path_str) >= 2 and path_str[1] == ':'):
            # Windows路径
            if platform.system() == 'Windows':
                # Windows上保持原样或使用PureWindowsPath标准化
                return str(PureWindowsPath(path_str))
            else:
                # macOS/Linux上：Windows路径无法直接访问
                # 记录警告并返回原样（实际访问会失败）
                return path_str
        else:
            # Unix风格路径
            return str(Path(path_str))

    @staticmethod
    def is_windows_unc_path(path_str):
        """检测是否是Windows UNC路径。"""
        return path_str.startswith('\\\\') or path_str.startswith('//')

    @staticmethod
    def is_windows_drive_path(path_str):
        """检测是否是Windows盘符路径。"""
        return len(path_str) >= 2 and path_str[1] == ':' and path_str[0].isalpha()

    @staticmethod
    def convert_to_local(path_str):
        """尝试将路径转换为本地可访问格式。"""
        system = platform.system()

        if system == 'Windows':
            # Windows上，处理macOS风格的路径
            if path_str.startswith('/'):
                # 无法直接转换，保持原样
                return path_str
            return path_str

        else:
            # macOS/Linux上，处理Windows路径
            if PathUtils.is_windows_drive_path(path_str):
                # 盘符路径无法在macOS上直接访问
                # 可选：提示用户使用SMB挂载
                return path_str
            elif PathUtils.is_windows_unc_path(path_str):
                # UNC路径，尝试转换为SMB挂载路径
                # \\Server\Share -> /Volumes/Share (需要手动挂载)
                # 这里只做提示，实际转换需要用户配置
                return path_str
            return path_str

    @staticmethod
    def get_path_type(path_str):
        """识别路径类型，返回描述字符串。"""
        if PathUtils.is_windows_unc_path(path_str):
            return "Windows UNC路径 (网络路径)"
        elif PathUtils.is_windows_drive_path(path_str):
            return "Windows盘符路径 (本地或映射驱动器)"
        elif path_str.startswith('/'):
            return "Unix风格路径"
        else:
            return "相对路径或未知格式"


def test_path_utils():
    """测试路径处理工具。"""
    # Windows路径检测
    assert PathUtils.is_windows_unc_path(r"\\Server\Share")
    assert PathUtils.is_windows_unc_path(r"//Server/Share")
    assert PathUtils.is_windows_drive_path(r"C:\Users")
    assert PathUtils.is_windows_drive_path(r"Y:\报关单")

    # 路径类型识别
    print(PathUtils.get_path_type(r"Y:\报关单\2026年"))  # Windows盘符路径
    print(PathUtils.get_path_type(r"\\NAS-Server\退税资料"))  # Windows UNC路径
    print(PathUtils.get_path_type("/Users/test/file"))  # Unix风格路径

    print("✓ PathUtils测试通过")


if __name__ == "__main__":
    test_path_utils()
