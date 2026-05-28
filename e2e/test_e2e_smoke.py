# -*- coding: utf-8 -*-
"""E2E冒烟测试 — 验证基础功能可用。"""
import pytest


class TestE2ESmoke:
    """冒烟测试：验证平台基础功能。"""

    def test_homepage_loads(self, page, base_url):
        """首页能正常加载。"""
        page.goto(base_url)
        page.wait_for_load_state("networkidle")
        assert "本地自动化平台" in page.title() or page.locator("body").text() != ""

    def test_plugin_page_loads(self, page, base_url):
        """插件配置页能正常加载。"""
        from e2e.pages.plugin_page import PluginPage

        plugin_page = PluginPage(page, base_url)
        plugin_page.goto("file-organizer")

        # 验证页面加载（等待扫描按钮出现）
        assert plugin_page.scan_button.is_visible()

    def test_api_auth_works(self, base_url):
        """API认证机制正常（无需Playwright）。"""
        import requests

        resp = requests.get(f"{base_url}/api/system/token")
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert len(data["token"]) > 0
