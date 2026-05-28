# -*- coding: utf-8 -*-
"""全局测试配置 — fixtures、数据库、TestClient。"""
import os
import sys
import pytest

# 确保项目根目录可导入
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


@pytest.fixture
def app():
    """创建测试用FastAPI应用（跳过前端静态文件挂载）。"""
    import tempfile
    test_data_dir = os.path.join(tempfile.gettempdir(), "localagent_test")
    os.environ["LOCAL_AGENT_DATA_DIR"] = test_data_dir
    from backend.app import create_app
    application = create_app()
    return application


@pytest.fixture
def client(app):
    """同步TestClient，自动处理生命周期。"""
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_token(client):
    """获取API认证token。"""
    resp = client.get("/api/system/token")
    assert resp.status_code == 200
    return resp.json()["token"]


@pytest.fixture
def auth_headers(auth_token):
    """带Authorization头的headers。"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def tmp_tree(tmp_path):
    """创建临时目录结构用于文件扫描测试。"""
    # 模拟源文件目录
    src = tmp_path / "source"
    src.mkdir()
    (src / "发票_001.pdf").write_text("inv1")
    (src / "发票_002.pdf").write_text("inv2")
    (src / "报关单_001.pdf").write_text("decl1")
    (src / "合同_ABC.pdf").write_text("contract")
    (src / "其他文件.txt").write_text("misc")
    sub = src / "subdir"
    sub.mkdir()
    (sub / "发票_003.pdf").write_text("inv3")
    return tmp_path
