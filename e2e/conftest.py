# -*- coding: utf-8 -*-
"""E2E测试全局fixtures。"""
import os
import shutil
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext


@pytest.fixture(scope="session")
def base_url():
    """测试基准URL（优先环境变量，默认本地开发）。"""
    return os.getenv("E2E_BASE_URL", "http://localhost:8088")


@pytest.fixture(scope="function")
def auth_page(browser_context: BrowserContext, base_url):
    """已认证的页面context（自动注入token）。"""
    import requests

    # 通过API获取token（避免Playwright事件循环问题）
    resp = requests.get(f"{base_url}/api/system/token")
    token = resp.json()["token"]

    # 将token注入localStorage
    browser_context.add_init_script(f"localStorage.setItem('token', '{token}')")
    browser_context.add_init_script("""
        // 拦截所有API请求，自动添加token header
        const originalFetch = window.fetch;
        window.fetch = function(...args) {
            const token = localStorage.getItem('token');
            if (token && args[1]) {
                args[1].headers = args[1].headers || {};
                args[1].headers['Authorization'] = `Bearer ${token}`;
            }
            return originalFetch.apply(this, args);
        };
    """)

    page = browser_context.new_page()

    # 先访问首页确保认证生效
    page.goto(f"{base_url}/")
    page.wait_for_load_state("networkidle")

    yield page, base_url
    page.close()


@pytest.fixture
def e2e_test_files(tmp_path):
    """E2E测试专用的测试文件（使用项目目录下，确保subprocess可访问）。"""
    import os
    # 使用项目目录下的test_files，而不是系统临时目录
    # 这样在subprocess执行扫描时路径是可访问的
    project_root = Path(__file__).parent.parent
    test_dir = project_root / "test_files_e2e"
    test_dir.mkdir(exist_ok=True)

    source = test_dir / "source"
    source.mkdir(exist_ok=True)
    dest = test_dir / "dest"
    dest.mkdir(exist_ok=True)

    # 创建测试文件（模拟出口退税资料）
    (source / "ABC001发票.pdf").write_text("发票内容", encoding="utf-8")
    (source / "ABC001报关单.pdf").write_text("报关单内容", encoding="utf-8")
    (source / "ABC001装箱单.pdf").write_text("装箱单内容", encoding="utf-8")
    (source / "ABC002发票.pdf").write_text("发票内容", encoding="utf-8")
    (source / "ABC002报关单.pdf").write_text("报关单内容", encoding="utf-8")

    # 创建子目录测试
    subdir = source / "subdir"
    subdir.mkdir(exist_ok=True)
    (subdir / "ABC003发票.pdf").write_text("发票内容", encoding="utf-8")

    yield {
        "test_dir": test_dir,
        "source": str(source),
        "dest": str(dest),
    }

    # 清理测试文件
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)