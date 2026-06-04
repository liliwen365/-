---
description: 数据库迁移规则（匹配 alembic/ 目录）
globs: alembic/**/*.py
---

- 迁移脚本用 autogenerate 生成后必须人工检查（可能漏检测或误检测）
- 迁移脚本一旦提交不应再修改，新建修订版
- downgrade 必须与 upgrade 对称
