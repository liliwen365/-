# -*- coding: utf-8 -*-
"""银行流水对账插件 - 入口"""
import os

from backend.base_plugin import BasePlugin
from engine import reconcile


class BankReconciliationPlugin(BasePlugin):
    def validate_params(self, params: dict) -> dict:
        bank_file = params.get('bank_file', '').strip()
        if not bank_file:
            raise ValueError("请指定银行流水文件路径")
        journal = params.get('journal', [])
        if not journal:
            raise ValueError("请输入企业日记账数据")
        return params

    def execute(self, params: dict, progress_callback=None) -> dict:
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        return reconcile(params, plugin_dir, on_progress=progress_callback)
