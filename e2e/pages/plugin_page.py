# -*- coding: utf-8 -*-
"""文件整理插件页面POM。"""
from playwright.sync_api import Page, Locator


class PluginPage:
    """插件配置页面。"""

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

        # 核心元素
        self.template_dropdown = page.get_by_role("button", name="加载模板")
        self.scan_button = page.get_by_role("button", name="扫描")
        self.copy_button = page.get_by_role("button", name="复制")
        self.result_table = page.locator(".el-table").last  # 结果表格是最后一个
        self.progress_bar = page.locator(".el-progress")

    def goto(self, plugin_name: str = "file-organizer"):
        """导航到插件配置页。"""
        self.page.goto(f"{self.base_url}/plugin/{plugin_name}")
        self.page.wait_for_load_state("networkidle")

    def load_template(self, template_name: str):
        """加载模板（通过下拉菜单）。"""
        self.template_dropdown.click()
        self.page.get_by_text(template_name).click()
        self.page.wait_for_timeout(500)

    def click_scan(self):
        """点击扫描按钮。"""
        self.scan_button.click()

    def wait_for_scan_complete(self, timeout: int = 15000):
        """等待扫描完成（进度条消失）。"""
        # 等待进度条出现然后消失
        try:
            self.progress_bar.wait_for(timeout=3000)
        except:
            pass  # 进度条可能太快错过了
        self.progress_bar.wait_for(state="hidden", timeout=timeout)

    def get_scan_result_count(self):
        """获取扫描结果数量（从复制按钮文本解析）。"""
        try:
            button_text = self.copy_button.inner_text()
            print(f"复制按钮文本: {button_text}")  # 调试
            # 提取 "复制 (N 个文件)" 中的N
            import re
            match = re.search(r'复制\s*\((\d+)\s*个文件', button_text)
            if match:
                return int(match.group(1))
            # 如果找不到匹配，尝试其他模式
            match = re.search(r'(\d+)\s*个文件', button_text)
            return int(match.group(1)) if match else 0
        except Exception as e:
            print(f"获取扫描结果数量失败: {e}")
            return 0

    def click_copy(self):
        """点击复制按钮。"""
        self.copy_button.click()

    def wait_for_copy_complete(self, timeout: int = 15000):
        """等待复制完成（进度条消失）。"""
        self.progress_bar.wait_for(state="hidden", timeout=timeout)

    def get_result_table_rows(self):
        """获取结果表格所有行。"""
        return self.result_table.locator(".el-table__body tr").all()


class HomePage:
    """首页POM。"""

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def goto(self):
        """导航到首页。"""
        self.page.goto(f"{self.base_url}/")
        self.page.wait_for_load_state("networkidle")

    def get_plugin_link(self, plugin_name: str):
        """获取插件卡片链接。"""
        return self.page.get_by_text(plugin_name)
