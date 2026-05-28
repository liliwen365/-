# -*- coding: utf-8 -*-
"""资源路径解析 — 兼容开发环境和 PyInstaller 打包环境。"""

import sys
import os


def resource_path(relative_path: str) -> str:
    """获取资源文件的绝对路径。

    开发环境：基于项目根目录（backend/ 的上级）。
    打包环境：基于 sys._MEIPASS（PyInstaller 解压目录）。
    """
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
    return os.path.join(base_path, relative_path)
