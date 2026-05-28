# -*- coding: utf-8 -*-
"""文件整理插件真实E2E测试 — 完整流程测试。"""
import json
import logging
import pytest
import requests
from pathlib import Path
from e2e.pages.plugin_page import PluginPage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.e2e
class TestFileOrganizerRealE2E:
    """文件整理插件真实端到端测试（需要真实文件操作）。"""

    def test_full_scan_copy_workflow(self, page, base_url, e2e_test_files):
        """完整流程：加载模板 → 配置任务 → 扫描 → 验证结果。"""
        from pathlib import Path

        # 直接使用项目目录下的测试文件
        project_root = Path(__file__).parent.parent
        source = str(project_root / "test_files_e2e" / "source")
        dest = str(project_root / "test_files_e2e" / "dest")

        logger.info(f"使用测试文件路径: source={source}, dest={dest}")
        logger.info(f"source文件存在: {Path(source).exists()}")
        logger.info(f"source文件列表: {list(Path(source).rglob('*.pdf'))}")

        # 1. 通过API获取token
        token_resp = requests.get(f"{base_url}/api/system/token")
        token = token_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 构造正确的规则模板（不使用旧模板的Windows路径）
        rules = [
            {"doc_type": "发票", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*发票*.*", "dest_subfolder": "发票", "enabled": True},
            {"doc_type": "报关单", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*报关*.*", "dest_subfolder": "报关单", "enabled": True},
            {"doc_type": "装箱单", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*装箱*.*", "dest_subfolder": "装箱单", "enabled": True},
        ]

        # 3. 通过API配置任务和规则
        config = {
            "tasks": [{
                "task_id": "E2E_TEST_001",
                "dest_root": dest,
                "keywords": json.dumps({
                    "发票": {"path": [source], "file": ["ABC001", "ABC002", "ABC003"]},
                    "报关单": {"path": [source], "file": ["ABC001", "ABC002"]},
                    "装箱单": {"path": [source], "file": ["ABC001"]},
                }),
                "override_path": "",
                "enabled_scan": True,
                "enabled_copy": True,
            }],
            "rules": rules,
        }
        save_resp = requests.put(
            f"{base_url}/api/plugins/file-organizer/config",
            json={"config": config},
            headers=headers
        )
        logger.info(f"保存配置响应: {save_resp.status_code} {save_resp.text}")

        # 验证配置保存成功（强制刷新）
        assert save_resp.status_code == 200, f"配置保存失败: {save_resp.text}"
        get_resp = requests.get(f"{base_url}/api/plugins/file-organizer/config", headers=headers)
        saved_config = get_resp.json()
        logger.info(f"读取配置: tasks={len(saved_config.get('tasks', []))}, rules={len(saved_config.get('rules', []))}")

        # 4. 通过UI执行扫描
        plugin_page = PluginPage(page, base_url)
        plugin_page.goto("file-organizer")

        # 刷新页面确保配置生效（多次刷新确保）
        plugin_page.page.reload()
        plugin_page.page.wait_for_load_state("networkidle")
        plugin_page.page.wait_for_timeout(1000)  # 额外等待让JS处理完成

        # 检查扫描按钮是否可用
        assert plugin_page.scan_button.is_enabled(), "扫描按钮应可点击"

        plugin_page.click_scan()
        plugin_page.wait_for_scan_complete()

        # 等待任务完成
        import time
        time.sleep(2)  # 给后端时间完成处理

        # 通过API查询任务历史
        history_resp = requests.get(f"{base_url}/api/plugins/file-organizer/history", headers=headers)
        logger.info(f"任务历史响应: {history_resp.status_code}")
        if history_resp.status_code == 200:
            history_data = history_resp.json()
            # 处理history数据结构: {'history': [...]}
            history = history_data.get('history', [])
            logger.info(f"任务历史数量: {len(history)}")
            if history and len(history) > 0:
                last_task = history[-1]
                logger.info(f"最新任务: {last_task.get('summary')}")
                if "找到 0 个文件" in last_task.get('summary', ''):
                    logger.error("扫描未找到文件，可能是路径或权限问题")
                    # 打印详细的文件信息用于调试
                    logger.info(f"测试目录: {e2e_test_files}")
                    logger.info(f"源文件列表: {list(Path(source).rglob('*'))}")

        # 等待一下让UI更新
        plugin_page.page.wait_for_timeout(1000)

        # 如果扫描失败，打印错误信息
        error_locator = plugin_page.page.locator(".el-alert--error")
        if error_locator.count() > 0:
            error_msg = error_locator.inner_text()
            logger.error(f"扫描错误信息: {error_msg}")

        # 5. 验证扫描结果数量
        result_count = plugin_page.get_scan_result_count()

        # 如果结果为0，打印更多调试信息
        if result_count == 0:
            logger.info(f"调试信息:")
            logger.info(f"  - source路径: {source}")
            logger.info(f"  - dest路径: {dest}")
            logger.info(f"  - source文件存在: {Path(source).exists()}")
            logger.info(f"  - source文件列表: {list(Path(source).rglob('*.pdf'))}")

            # 获取页面文本查看是否有错误
            page_text = plugin_page.page.inner_text("body")
            if "错误" in page_text or "失败" in page_text:
                logger.warning(f"页面包含错误信息")
                # 打印页面文本的前1000个字符来定位错误
                logger.warning(f"页面文本片段: {page_text[:1000]}")

        assert result_count >= 6, f"应至少找到6个文件，实际找到{result_count}个"

        # 6. 验证结果表格有数据
        rows = plugin_page.get_result_table_rows()
        assert len(rows) >= 6, f"结果表格应至少有6行，实际有{len(rows)}行"

        logger.info(f"✓ 扫描完成，找到 {result_count} 个文件")

    def test_scan_with_custom_keywords(self, page, base_url, e2e_test_files):
        """测试自定义关键字的扫描。"""
        from pathlib import Path

        # 直接使用项目目录下的测试文件
        project_root = Path(__file__).parent.parent
        source = str(project_root / "test_files_e2e" / "source")
        dest = str(project_root / "test_files_e2e" / "dest")

        # 1. 获取token
        token_resp = requests.get(f"{base_url}/api/system/token")
        token = token_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 配置只扫描ABC002的发票和报关单
        config = {
            "tasks": [{
                "task_id": "E2E_TEST_002",
                "dest_root": dest,
                "keywords": json.dumps({
                    "发票": {"path": [source], "file": ["ABC002"]},
                    "报关单": {"path": [source], "file": ["ABC002"]},
                }),
                "override_path": "",
                "enabled_scan": True,
                "enabled_copy": False,
            }],
            "rules": [
                {"doc_type": "发票", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*发票*", "dest_subfolder": "发票", "enabled": True},
                {"doc_type": "报关单", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*报关*", "dest_subfolder": "报关单", "enabled": True},
            ],
        }
        requests.put(
            f"{base_url}/api/plugins/file-organizer/config",
            json={"config": config},
            headers=headers
        )

        # 3. 执行扫描
        plugin_page = PluginPage(page, base_url)
        plugin_page.goto("file-organizer")
        plugin_page.click_scan()
        plugin_page.wait_for_scan_complete()

        # 4. 验证只找到2个文件
        result_count = plugin_page.get_scan_result_count()
        assert result_count == 2, f"应找到2个文件，实际找到{result_count}个"

        logger.info(f"✓ 自定义关键字扫描完成，找到 {result_count} 个文件")

    def test_copy_workflow(self, page, base_url, e2e_test_files):
        """测试复制工作流（不通过UI验证文件系统，通过API验证）。"""
        from pathlib import Path

        source = e2e_test_files["source"]
        dest = e2e_test_files["dest"]

        # 1. 获取token
        token_resp = requests.get(f"{base_url}/api/system/token")
        token = token_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 配置任务（简单案例：只复制1个发票文件）
        config = {
            "tasks": [{
                "task_id": "E2E_TEST_COPY",
                "dest_root": dest,
                "keywords": json.dumps({
                    "发票": {"path": [source], "file": ["ABC001"]},
                }),
                "override_path": "",
                "enabled_scan": True,
                "enabled_copy": True,
            }],
            "rules": [
                {"doc_type": "发票", "search_path": "{PathKeyword}", "filename_pattern": "*{PrimaryKeyword}*发票*", "dest_subfolder": "", "enabled": True},
            ],
        }
        requests.put(
            f"{base_url}/api/plugins/file-organizer/config",
            json={"config": config},
            headers=headers
        )

        # 3. 扫描
        plugin_page = PluginPage(page, base_url)
        plugin_page.goto("file-organizer")
        plugin_page.click_scan()
        plugin_page.wait_for_scan_complete()

        # 4. 复制
        plugin_page.click_copy()
        plugin_page.wait_for_copy_complete()

        # 5. 验证文件确实被复制（通过文件系统）
        dest_path = Path(dest)
        assert dest_path.exists(), "目标目录应存在"

        # 查找复制的文件
        copied_files = list(dest_path.rglob("ABC001*.pdf"))
        assert len(copied_files) >= 1, f"应至少复制1个文件，实际找到{len(copied_files)}个"

        logger.info(f"✓ 复制完成，文件已复制到: {copied_files[0]}")
