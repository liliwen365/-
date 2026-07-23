# -*- coding: utf-8 -*-
"""API集成测试 — 插件配置隔离、模板加载、执行流程。"""
import pytest


class TestPluginConfigIsolation:
    """验证每个插件的配置互不污染。"""

    def test_file_organizer_config_has_only_own_keys(self, client, auth_headers):
        resp = client.get("/api/plugins/file-organizer/config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"tasks", "rules"}

    def test_bank_reconciliation_config_has_only_own_keys(self, client, auth_headers):
        resp = client.get("/api/plugins/bank-reconciliation/config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        expected = {"bank_file", "bank_name", "skip_rows", "journal", "match_rules"}
        assert set(data.keys()) == expected

    def test_stock_price_config_has_only_own_keys(self, client, auth_headers):
        resp = client.get("/api/plugins/stock-price-query/config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"stocks"}

    def test_save_config_filters_foreign_keys(self, client, auth_headers):
        """保存时不应存入不属于该插件的字段。"""
        payload = {
            "config": {
                "tasks": [{"task_id": "test"}],
                "rules": [],
                "evil_inject": "should_be_removed",
                "bank_file": "also_foreign",
            }
        }
        resp = client.put("/api/plugins/file-organizer/config", json=payload, headers=auth_headers)
        assert resp.status_code == 200

        # 验证读取回来只有正确字段
        resp2 = client.get("/api/plugins/file-organizer/config", headers=auth_headers)
        data = resp2.json()
        assert "evil_inject" not in data
        assert "bank_file" not in data
        assert "tasks" in data

    def test_save_config_does_not_affect_other_plugins(self, client, auth_headers):
        """修改file-organizer配置不应影响bank-reconciliation。"""
        payload = {"config": {"tasks": [], "rules": []}}
        client.put("/api/plugins/file-organizer/config", json=payload, headers=auth_headers)

        resp = client.get("/api/plugins/bank-reconciliation/config", headers=auth_headers)
        data = resp.json()
        # bank-reconciliation应仍只有自己的字段
        assert "tasks" not in data
        assert "rules" not in data


class TestPluginInfo:
    def test_file_organizer_info(self, client, auth_headers):
        resp = client.get("/api/plugins/file-organizer/info", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "file-organizer"
        assert len(data["params"]) == 2
        param_names = {p["name"] for p in data["params"]}
        assert param_names == {"tasks", "rules"}

    def test_nonexistent_plugin_returns_404(self, client, auth_headers):
        resp = client.get("/api/plugins/nonexistent/info", headers=auth_headers)
        assert resp.status_code == 404


class TestTemplateLoading:
    def test_load_exit_tax_template(self, client, auth_headers):
        resp = client.get("/api/plugins/file-organizer/templates/%E5%87%BA%E5%8F%A3%E9%80%80%E7%A8%8E%E8%B5%84%E6%96%99%E6%95%B4%E7%90%86", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 5
        types = {r["doc_type"] for r in data}
        assert "发票" in types
        assert "报关单" in types

    def test_load_nonexistent_template_returns_404(self, client, auth_headers):
        resp = client.get("/api/plugins/file-organizer/templates/不存在的模板", headers=auth_headers)
        assert resp.status_code == 404


class TestPluginExecution:
    def test_execute_empty_params_returns_error(self, client, auth_headers):
        resp = client.post(
            "/api/plugins/file-organizer/execute",
            json={"params": {"tasks": [], "rules": [], "action": "scan"}},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]
        assert task_id > 0

        # 轮询直到完成
        import time
        for _ in range(10):
            status_resp = client.get(
                f"/api/plugins/file-organizer/status?task_id={task_id}",
                headers=auth_headers,
            )
            assert status_resp.status_code == 200
            if status_resp.json()["status"] in ("success", "error", "cancelled"):
                break
            time.sleep(0.5)

        result = status_resp.json()
        assert result["status"] == "error"
        assert "请先添加任务" in result["progress_message"]

    def test_validate_error_returns_400_with_message(self, client, auth_headers):
        """任务行字段不完整时，execute 应返回400并带中文校验消息（修复前是500吞掉原因）。"""
        resp = client.post(
            "/api/plugins/file-organizer/execute",
            json={"params": {
                "tasks": [{"task_id": "T1"}],  # 故意缺 dest_root
                "rules": [{"doc_type": "发票", "search_path": "D:/x", "filename_pattern": "*"}],
                "action": "scan",
            }},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "目标存放路径不能为空" in resp.json()["detail"]

    def test_status_includes_error_traceback_field(self, client, auth_headers):
        """status 接口应返回 error_traceback 字段（供前端展示失败详情）。"""
        resp = client.post(
            "/api/plugins/file-organizer/execute",
            json={"params": {"tasks": [], "rules": [], "action": "scan"}},
            headers=auth_headers,
        )
        task_id = resp.json()["task_id"]
        import time
        status_resp = resp
        for _ in range(10):
            status_resp = client.get(
                f"/api/plugins/file-organizer/status?task_id={task_id}",
                headers=auth_headers,
            )
            if status_resp.json()["status"] in ("success", "error", "cancelled"):
                break
            time.sleep(0.5)
        assert "error_traceback" in status_resp.json()

    def test_history_includes_error_traceback_field(self, client, auth_headers):
        """历史记录每条应包含 error_traceback 字段。"""
        resp = client.get("/api/plugins/file-organizer/history", headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json()["history"]:
            assert "error_traceback" in item

    def test_installed_plugins_list(self, client, auth_headers):
        resp = client.get("/api/plugins/installed", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        names = {p["name"] for p in data["plugins"]}
        # 只验证file-organizer（其他插件有依赖问题，不是测试重点）
        assert "file-organizer" in names


class TestAuthMiddleware:
    def test_api_without_token_returns_401(self, client):
        resp = client.get("/api/plugins/installed")
        assert resp.status_code == 401

    def test_api_with_wrong_token_returns_401(self, client):
        resp = client.get("/api/plugins/installed", headers={"Authorization": "Bearer wrong"})
        assert resp.status_code == 401

    def test_token_endpoint_is_public(self, client):
        resp = client.get("/api/system/token")
        assert resp.status_code == 200
        assert "token" in resp.json()

    def test_health_endpoint_is_public(self, client):
        resp = client.get("/api/system/health")
        assert resp.status_code == 200

    def test_spa_routes_return_html(self, client):
        """SPA catch-all应返回index.html（仅在前端已构建时）。"""
        import os
        frontend_dist = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "frontend", "dist",
        )
        if not os.path.isdir(frontend_dist):
            pytest.skip("前端未构建，跳过SPA路由测试")
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
