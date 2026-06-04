---
description: Python 后端开发规则（匹配 backend/ 目录）
globs: backend/**/*.py
---

- 异步用 async/await，FastAPI 路由必须是 async def
- 错误处理用显式 try/except，不静默吞异常
- 数据库操作用 with 管理 session/conn 生命周期
- API 路径用 kebab-case: `/api/plugins/file-organizer`
- 运行时问题先查日志，不要猜测试错
