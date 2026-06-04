---
description: 部署工具规则（匹配 deploy/ 目录）
globs: deploy/**/*.py
---

- Windows 测试工具需要 PYTHONUTF8=1 环境变量
- NAS 路径映射为 Y 盘，测试前需确认映射存在
- 此工具仅用于 Windows 环境验证，macOS 开发时不运行
