---
description: E2E 测试规则（匹配 e2e/ 目录）
globs: e2e/**/*.py
---

- 需要 Playwright + pytest-playwright，必须先启动服务器
- E2E 不在 CI 中运行（需要运行环境），仅本地验证
- 复用 test-rules.md 的 conftest 时序规则（TestClient context）
- 用 tempfile.gettempdir() 不用 /tmp（Windows 兼容）
- page fixture 来自 pytest-playwright
