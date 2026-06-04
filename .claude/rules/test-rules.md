---
description: 测试开发规则（匹配 tests/ 目录）
globs: tests/**/*.py
---

- 单元/集成: pytest + FastAPI TestClient
- conftest.py: license_code 插入必须在 TestClient context 内部（create_tables 在 lifespan 中）
- 依赖 DB 的操作必须在 `with TestClient(app) as c:` 内部
- 用 tempfile.gettempdir() 不用 /tmp（Windows 兼容）
- 跳过授权: LOCAL_AGENT_SKIP_LICENSE=1
- 测试数据目录: LOCAL_AGENT_DATA_DIR 指向临时目录
