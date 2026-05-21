# -*- coding: utf-8 -*-
"""股票行情查询插件 - 入口"""
from backend.base_plugin import BasePlugin
from engine import query_prices


class StockPricePlugin(BasePlugin):
    def validate_params(self, params: dict) -> dict:
        stocks = params.get('stocks', [])
        if not stocks:
            raise ValueError("请输入至少一个股票代码")
        for s in stocks:
            code = s.get('code', '').strip()
            if not code:
                raise ValueError("股票代码不能为空")
        return params

    def execute(self, params: dict, progress_callback=None) -> dict:
        return query_prices(params, on_progress=progress_callback)
