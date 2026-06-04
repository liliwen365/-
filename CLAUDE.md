# 本地自动化平台 - Claude Code 项目规范

## 元规则（最高优先级）

1. **本文件行数上限150行**。超过150行后指令遵循率显著下降。每新增规则必须评估：删掉这行Claude会犯错吗？不会则不加。
2. **规则仅写非默认约定**。Claude从代码可推断的不写，linter能检查的不写，显而易见的不写。
3. **先查后造**。实现任何非trivial功能前，先查社区方案、标准库、成熟框架，优先采纳而非自研。

## 项目概述

本地自动化平台（LocalAgent）。Python运行时+Web管理界面，通过安装插件实现各类自动化需求。文件整理是第一个内置插件。

**技术栈**: Python + FastAPI + Vue 3 + Element Plus + SQLite
**运行平台**: Windows（员工） / macOS（开发）
**当前版本**: v0.1.0

## Agentic Engineering 工作流

遵循 **Research → Plan → Execute → Review → Ship** 五阶段：
- **非平凡功能先进 Plan Mode**，对齐方案再动手
- **Rewind > Correct**：Claude 走偏时 Esc+Esc 回退重试，不在错误路径上追加修正
- **不要 babysit**：给目标，不要逐步指挥怎么做
- **给 Claude 验证工具**：改完必须跑测试验证

## 自我进化机制

两层持续进化（确保真正生效）：
- **第一层 — 自动捕获**：Stop hook 检测 → Claude 自动写入 learnings.md
- **第二层 — 定期审计**：`/self-evolve` 唯一进化入口（六维度检查 + 整合升级）
- session 开始时自动检查上次进化日期，超过 7 天提醒用户运行 /self-evolve

## 代码规范

- 用户可见文本用中文，变量名/函数名用英文snake_case
- 常量用UPPER_SNAKE_CASE
- 不写注释解释"是什么"，仅写"为什么这样"的非显而易见原因
- 具体规范见 .claude/rules/（按路径自动加载）

## 关键约束

- 前端打包为静态文件嵌入PyInstaller，FastAPI通过StaticFiles服务
- pystray必须在主线程运行（macOS AppKit要求），FastAPI放后台线程
- SPA路由: FastAPI catch-all `/{full_path:path}` 返回index.html
- 授权: RSA公钥验证，平台级授权，前台不显示剩余天数
- 插件目录: plugins/（内置）+ user-plugins/（用户自定义）

## 开发命令

```bash
python main.py                        # 完整启动（FastAPI+托盘+浏览器）
cd backend && python -m uvicorn backend.app:app --reload --port 8088  # 仅后端
cd frontend && npm install && npm run dev                             # 仅前端
python3 -m pytest tests/ -v           # 跑测试
python license_tool.py gen-keys       # 生成RSA密钥对
python license_tool.py issue <mid> <days>  # 签发授权
```

## 详细设计

见 [DESIGN.md](DESIGN.md)

## 细分规则

按文件路径自动加载：`.claude/rules/python-rules.md`、`vue-rules.md`、`test-rules.md`、`plugin-rules.md`

## 学习日志

见 [learnings.md](learnings.md) — 跨 session 持续积累的非显而易见经验
