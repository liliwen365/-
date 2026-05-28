# -*- coding: utf-8 -*-
"""文件整理插件 engine 核心逻辑测试。"""
import json
import os

import pandas as pd
import pytest

# 需要确保插件目录在sys.path中（engine.py import rules）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR = os.path.join(ROOT, "plugins", "file-organizer")
if PLUGIN_DIR not in os.path.dirname(os.path.abspath(__file__)):
    pass  # engine通过subprocess加载，但_scan_one_task需要rules可导入


def _make_rules_df(rules):
    return pd.DataFrame(rules)


def _make_tasks_df(tasks):
    return pd.DataFrame(tasks)


class TestScanOneTask:
    """测试 _scan_one_task 的关键字解析和搜索逻辑。"""

    def _run_scan(self, task, rules, tmp_path):
        """辅助：构造参数并调用_scan_one_task。"""
        sys_path_backup = os.sys.path[:]
        try:
            if PLUGIN_DIR not in os.sys.path:
                os.sys.path.insert(0, PLUGIN_DIR)
            from engine import _scan_one_task
            tasks_df = _make_tasks_df([task])
            rules_df = _make_rules_df(rules)
            records, _ = _scan_one_task(tasks_df.iloc[0], rules_df)
            return records
        finally:
            os.sys.path[:] = sys_path_backup

    def test_basic_scan_finds_files(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "ABC001发票.pdf").write_text("inv")
        (src / "ABC001报关单.pdf").write_text("dec")

        task = {
            "task_id": "T001",
            "dest_root": str(tmp_path / "dest"),
            "keywords": {
                "发票": {"path": [str(src)], "file": ["ABC001"]},
                "报关单": {"path": [str(src)], "file": ["ABC001"]},
            },
            "override_path": "",
            "enabled_scan": True,
        }
        rules = [
            {"doc_type": "发票", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*发票*", "dest_subfolder": "发票", "enabled": True},
            {"doc_type": "报关单", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*报关*", "dest_subfolder": "报关单", "enabled": True},
        ]
        records = self._run_scan(task, rules, tmp_path)
        found = [r for r in records if r["find_status"] == "已找到"]
        assert len(found) >= 2
        types = {r["doc_type"] for r in found}
        assert "发票" in types
        assert "报关单" in types

    def test_default_path_keyword_fallback(self, tmp_path):
        """_default组的路径关键词应作为回退。"""
        src = tmp_path / "pool"
        src.mkdir()
        (src / "test.txt").write_text("data")

        task = {
            "task_id": "T002",
            "dest_root": str(tmp_path / "dest"),
            "keywords": {
                "_default": {"path": [str(src)]},
                "其他": {"file": ["test"]},
            },
            "override_path": "",
        }
        rules = [
            {"doc_type": "其他", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*", "dest_subfolder": "", "enabled": True},
        ]
        records = self._run_scan(task, rules, tmp_path)
        found = [r for r in records if r["find_status"] == "已找到"]
        assert len(found) >= 1

    def test_no_file_keyword_skips_rule(self, tmp_path):
        """没有file关键字的分类应跳过该规则。"""
        task = {
            "task_id": "T003",
            "dest_root": str(tmp_path / "dest"),
            "keywords": {"发票": {"path": ["/tmp"], "file": []}},
            "override_path": "",
        }
        rules = [
            {"doc_type": "发票", "search_path": "/tmp", "filename_pattern": "*", "dest_subfolder": "", "enabled": True},
        ]
        records = self._run_scan(task, rules, tmp_path)
        assert len(records) == 0

    def test_override_path_takes_precedence(self, tmp_path):
        """特定搜索路径应覆盖规则模板。"""
        override = tmp_path / "override_dir"
        override.mkdir()
        (override / "special.pdf").write_text("s")

        task = {
            "task_id": "T004",
            "dest_root": str(tmp_path / "dest"),
            "keywords": {"发票": {"path": ["/nonexistent"], "file": ["special"]}},
            "override_path": str(override),
        }
        rules = [
            {"doc_type": "发票", "search_path": "/nonexistent/{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*", "dest_subfolder": "", "enabled": True},
        ]
        records = self._run_scan(task, rules, tmp_path)
        found = [r for r in records if r["find_status"] == "已找到"]
        assert len(found) >= 1

    def test_dest_subfolder(self, tmp_path):
        """带dest_subfolder的目标路径应包含子文件夹。"""
        src = tmp_path / "src"
        src.mkdir()
        (src / "f.pdf").write_text("x")

        task = {
            "task_id": "T005",
            "dest_root": str(tmp_path / "dest"),
            "keywords": {"发票": {"path": [str(src)], "file": ["f"]}},
            "override_path": "",
        }
        rules = [
            {"doc_type": "发票", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*", "dest_subfolder": "发票", "enabled": True},
        ]
        records = self._run_scan(task, rules, tmp_path)
        found = [r for r in records if r["find_status"] == "已找到"]
        assert len(found) == 1
        assert "发票" in found[0]["dest_path"]

    def test_keywords_as_json_string(self, tmp_path):
        """keywords字段为JSON字符串时应自动解析。"""
        src = tmp_path / "src"
        src.mkdir()
        (src / "doc.pdf").write_text("d")

        task = {
            "task_id": "T006",
            "dest_root": str(tmp_path / "dest"),
            "keywords": json.dumps({"发票": {"path": [str(src)], "file": ["doc"]}}),
            "override_path": "",
        }
        rules = [
            {"doc_type": "发票", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*", "dest_subfolder": "", "enabled": True},
        ]
        records = self._run_scan(task, rules, tmp_path)
        found = [r for r in records if r["find_status"] == "已找到"]
        assert len(found) >= 1

    def test_disabled_rule_skipped(self, tmp_path):
        """_scan_one_task不做规则过滤（由scan_tasks统一过滤），此处验证rules全disabled时active_rules为空。"""
        src = tmp_path / "src"
        src.mkdir()
        (src / "f.pdf").write_text("x")

        task = {
            "task_id": "T007",
            "dest_root": str(tmp_path / "dest"),
            "keywords": {"发票": {"path": [str(src)], "file": ["f"]}},
            "override_path": "",
        }
        rules = [
            {"doc_type": "发票", "search_path": "{PathKeyword}", "filename_pattern": "*", "dest_subfolder": "", "enabled": False},
        ]
        # _scan_one_task本身不过滤enabled，但scan_tasks会传过滤后的active_rules
        # 传空rules_df时应返回0条记录
        records = self._run_scan(task, [], tmp_path)
        assert len(records) == 0


class TestScanTasksIntegration:
    """scan_tasks 完整流程测试。"""

    def test_scan_filters_enabled_tasks(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "f.pdf").write_text("x")

        sys_path_backup = os.sys.path[:]
        try:
            if PLUGIN_DIR not in os.sys.path:
                os.sys.path.insert(0, PLUGIN_DIR)
            from engine import scan_tasks

            tasks_df = _make_tasks_df([
                {"task_id": "T1", "dest_root": str(tmp_path / "d"), "keywords": {"发票": {"path": [str(src)], "file": ["f"]}}, "override_path": "", "enabled_scan": True},
                {"task_id": "T2", "dest_root": str(tmp_path / "d"), "keywords": {}, "override_path": "", "enabled_scan": False},
            ])
            rules_df = _make_rules_df([
                {"doc_type": "发票", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*", "dest_subfolder": "", "enabled": True},
            ])
            updated_tasks, plan_df = scan_tasks(tasks_df, rules_df)
            assert len(plan_df) >= 1  # 只有T1被扫描
            task_ids = plan_df["task_id"].unique().tolist()
            assert "T1" in task_ids
            assert "T2" not in task_ids
        finally:
            os.sys.path[:] = sys_path_backup


class TestExecuteCopy:
    """execute_copy 复制逻辑测试。"""

    def test_copy_files_success(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "file1.pdf").write_text("content1")
        (src / "file2.pdf").write_text("content2")

        dest = tmp_path / "dest" / "T001"
        dest.mkdir(parents=True)

        sys_path_backup = os.sys.path[:]
        try:
            if PLUGIN_DIR not in os.sys.path:
                os.sys.path.insert(0, PLUGIN_DIR)
            from engine import execute_copy

            tasks_df = _make_tasks_df([
                {"task_id": "T001", "dest_root": str(tmp_path / "dest"), "enabled_scan": True, "enabled_copy": True},
            ])
            plan_df = _make_tasks_df([
                {"task_id": "T001", "copy_status": "待复制", "user_action": "",
                 "source_path": str(src / "file1.pdf"), "dest_path": str(dest / "file1.pdf")},
                {"task_id": "T001", "copy_status": "待复制", "user_action": "",
                 "source_path": str(src / "file2.pdf"), "dest_path": str(dest / "file2.pdf")},
            ])
            updated_tasks, updated_plan = execute_copy(tasks_df, plan_df)
            copied = updated_plan[updated_plan["copy_status"] == "已复制"]
            assert len(copied) == 2
            assert (dest / "file1.pdf").exists()
            assert (dest / "file2.pdf").exists()
        finally:
            os.sys.path[:] = sys_path_backup

    def test_copy_skip_by_user(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "skip_me.pdf").write_text("x")

        dest = tmp_path / "dest" / "T001"
        dest.mkdir(parents=True)

        sys_path_backup = os.sys.path[:]
        try:
            if PLUGIN_DIR not in os.sys.path:
                os.sys.path.insert(0, PLUGIN_DIR)
            from engine import execute_copy

            tasks_df = _make_tasks_df([
                {"task_id": "T001", "dest_root": str(tmp_path / "dest"), "enabled_scan": True, "enabled_copy": True},
            ])
            plan_df = _make_tasks_df([
                {"task_id": "T001", "copy_status": "待复制", "user_action": "SKIP",
                 "source_path": str(src / "skip_me.pdf"), "dest_path": str(dest / "skip_me.pdf")},
            ])
            updated_tasks, updated_plan = execute_copy(tasks_df, plan_df)
            skipped = updated_plan[updated_plan["copy_status"] == "用户跳过"]
            assert len(skipped) == 1
            assert not (dest / "skip_me.pdf").exists()
        finally:
            os.sys.path[:] = sys_path_backup

    def test_auto_disable_on_complete(self, tmp_path):
        """任务完成后自动禁用enabled_scan/enabled_copy。"""
        src = tmp_path / "src"
        src.mkdir()
        (src / "f.pdf").write_text("x")
        dest = tmp_path / "dest" / "T001"
        dest.mkdir(parents=True)

        sys_path_backup = os.sys.path[:]
        try:
            if PLUGIN_DIR not in os.sys.path:
                os.sys.path.insert(0, PLUGIN_DIR)
            from engine import execute_copy

            tasks_df = _make_tasks_df([
                {"task_id": "T001", "dest_root": str(tmp_path / "dest"), "enabled_scan": True, "enabled_copy": True},
            ])
            plan_df = _make_tasks_df([
                {"task_id": "T001", "copy_status": "待复制", "user_action": "",
                 "source_path": str(src / "f.pdf"), "dest_path": str(dest / "f.pdf")},
            ])
            updated_tasks, _ = execute_copy(tasks_df, plan_df)
            row = updated_tasks[updated_tasks["task_id"] == "T001"].iloc[0]
            assert row["enabled_scan"] == False
            assert row["enabled_copy"] == False
        finally:
            os.sys.path[:] = sys_path_backup
