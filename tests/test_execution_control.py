# -*- coding: utf-8 -*-
"""执行过程控制测试 —— 扫描上限/深度剪枝/进度回调/配置项。

超时强杀、取消即停属子进程级时序行为，在 Mac 端到端实测验证，不在单测里跑。
"""
import os
import tempfile

from backend.capabilities.file_scanner import scan_directory


class TestScanLimits:
    """扫描防卡死：文件数上限 + 深度剪枝。"""

    def test_scan_respects_max_files(self):
        """max_files 截断：20 个匹配文件限制 5 个，应只返回 5 个。"""
        with tempfile.TemporaryDirectory() as d:
            for i in range(20):
                open(os.path.join(d, f"发票_{i}.pdf"), "w").close()
            report = scan_directory(d, "发票_*.pdf", max_files=5)
            assert report.error is None
            assert len(report.files) == 5  # 在上限处截断

    def test_scan_max_depth_prunes_deep_dirs(self):
        """max_depth=1 时不应进入二级子目录下的文件。"""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "a", "b"))
            open(os.path.join(d, "a", "发票_shallow.pdf"), "w").close()
            open(os.path.join(d, "a", "b", "发票_deep.pdf"), "w").close()
            report = scan_directory(d, "发票_*.pdf", max_depth=1)
            paths = [f.path for f in report.files]
            assert any("发票_shallow.pdf" in p for p in paths)   # 浅层能找到
            assert not any("发票_deep.pdf" in p for p in paths)  # 深层被剪枝

    def test_scan_progress_callback_invoked(self):
        """on_progress 回调应被调用（让前端/日志感知扫描进度，不黑箱）。"""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "sub"))
            open(os.path.join(d, "发票_1.pdf"), "w").close()
            open(os.path.join(d, "sub", "发票_2.pdf"), "w").close()
            seen_dirs = []
            scan_directory(
                d, "发票_*.pdf",
                on_progress=lambda root, n: seen_dirs.append(root),
            )
            assert len(seen_dirs) >= 1  # 至少回调一次


class TestExecutionControlSettings:
    """可配参数默认值（.env 可覆盖）。"""

    def test_settings_have_defaults(self):
        from backend.config import settings
        assert settings.TASK_TIMEOUT_SEC == 600
        assert settings.SCAN_MAX_FILES == 50000
        assert settings.SCAN_MAX_DEPTH == 10
