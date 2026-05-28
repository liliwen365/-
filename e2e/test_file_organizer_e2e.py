# -*- coding: utf-8 -*-
"""文件整理插件E2E测试。"""
import pytest
from e2e.pages.plugin_page import PluginPage


class TestFileOrganizerE2E:
    """文件整理插件端到端测试。"""

    def test_load_template_via_api(self, base_url):
        """通过API加载模板验证后端逻辑（无需Playwright）。"""
        import requests

        # 获取token
        token_resp = requests.get(f"{base_url}/api/system/token")
        token = token_resp.json()["token"]

        # 调用模板加载API
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{base_url}/api/plugins/file-organizer/templates/%E5%87%BA%E5%8F%A3%E9%80%80%E7%A8%8E%E8%B5%84%E6%96%99%E6%95%B4%E7%90%86",
            headers=headers
        )

        # 验证返回
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 5
        doc_types = {r["doc_type"] for r in data}
        assert "发票" in doc_types
        assert "报关单" in doc_types

    def test_plugin_config_page_structure(self, page, base_url):
        """插件配置页结构正确。"""
        plugin_page = PluginPage(page, base_url)
        plugin_page.goto("file-organizer")

        # 验证关键元素存在
        assert plugin_page.template_dropdown.is_visible()
        assert plugin_page.scan_button.is_visible()

    def test_scan_button_exists(self, page, base_url):
        """扫描按钮存在。"""
        plugin_page = PluginPage(page, base_url)
        plugin_page.goto("file-organizer")

        assert plugin_page.scan_button.is_visible()
