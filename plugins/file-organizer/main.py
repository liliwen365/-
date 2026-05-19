# -*- coding: utf-8 -*-
"""文件整理插件 - 入口。"""
import pandas as pd
from backend.base_plugin import BasePlugin
from engine import scan_tasks, execute_copy


class FileOrganizerPlugin(BasePlugin):
    def validate_params(self, params: dict) -> dict:
        tasks = params.get("tasks", [])
        rules = params.get("rules", [])
        for t in tasks:
            if not t.get("task_id"):
                raise ValueError("任务ID不能为空")
            if not t.get("dest_root"):
                raise ValueError("目标存放路径不能为空")
        for r in rules:
            if not r.get("doc_type"):
                raise ValueError("文件分类不能为空")
            if not r.get("search_path"):
                raise ValueError("源文件搜索路径不能为空")
            if not r.get("filename_pattern"):
                raise ValueError("文件名模式不能为空")
        return params

    def execute(self, params: dict, progress_callback=None) -> dict:
        tasks_data = params.get("tasks", [])
        rules_data = params.get("rules", [])
        action = params.get("action", "scan")

        tasks_df = pd.DataFrame(tasks_data) if tasks_data else pd.DataFrame()
        rules_df = pd.DataFrame(rules_data) if rules_data else pd.DataFrame()

        if tasks_df.empty or rules_df.empty:
            return {"status": "error", "summary": "请先添加任务和规则", "data": {}}

        if action == "scan":
            tasks_df, plan_df = scan_tasks(tasks_df, rules_df, on_progress=progress_callback)
            plan_records = plan_df.to_dict("records") if not plan_df.empty else []
            total = len(plan_df)
            found = len(plan_df[plan_df["查找状态"] == "已找到"]) if not plan_df.empty and "查找状态" in plan_df.columns else 0
            return {
                "status": "success",
                "summary": f"扫描完成：共 {total} 条计划，找到 {found} 个文件",
                "data": {"tasks": tasks_df.to_dict("records"), "plan": plan_records},
            }

        elif action == "copy":
            plan_data = params.get("plan", [])
            plan_df = pd.DataFrame(plan_data) if plan_data else pd.DataFrame()
            if plan_df.empty:
                return {"status": "error", "summary": "没有可执行的复制计划", "data": {}}
            tasks_df, plan_df = execute_copy(tasks_df, plan_df, on_progress=progress_callback)
            copied = len(plan_df[plan_df["复制状态"] == "已复制"])
            failed = len(plan_df[plan_df["复制状态"] == "复制失败"])
            return {
                "status": "success",
                "summary": f"复制完成：成功 {copied}，失败 {failed}",
                "data": {"tasks": tasks_df.to_dict("records"), "plan": plan_df.to_dict("records")},
            }

        return {"status": "error", "summary": f"未知操作: {action}", "data": {}}
