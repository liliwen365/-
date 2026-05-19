# 本地自动化平台 - Claude Code 项目规范

## 元规则（最高优先级）

1. **本文件行数上限150行**。超过150行后指令遵循率显著下降。每新增规则必须评估：删掉这行Claude会犯错吗？不会则不加。
2. **规则仅写非默认约定**。Claude从代码可推断的不写，linter能检查的不写，显而易见的不写。

## 项目概述

本地自动化平台（LocalAgent）。Python运行时+Web管理界面，通过安装插件实现各类自动化需求。文件整理是第一个内置插件。

**技术栈**: Python + FastAPI + Vue 3 + Element Plus + SQLite
**运行平台**: Windows（员工） / macOS（开发）
**当前版本**: v0.1.0

## 代码规范

- 用户可见文本用中文，变量名/函数名用英文snake_case
- 常量用UPPER_SNAKE_CASE
- 不写注释解释"是什么"，仅写"为什么这样"的非显而易见原因
- API路径用kebab-case: `/api/plugins/file-organizer`
- 数据库表名用snake_case，与SQLAlchemy模型对应

## 架构要点

- **前后端分离**: FastAPI后端 + Vue 3前端，HTTP/WebSocket通信
- **插件系统**: 目录扫描发现 → YAML声明元数据 → 动态import → 子进程执行
- **Schema驱动UI**: 插件声明参数Schema，前端通用渲染引擎自动生成表单
- **动态路由**: 后端返回已安装插件列表，前端router.addRoute()动态注册
- **进程隔离**: 插件在ProcessPoolExecutor子进程执行，崩溃不影响主进程
- **授权系统**: RSA公钥验证，机器绑定，平台级授权（复用旧项目auth.py）

## 关键约束

- 前端打包为静态文件嵌入PyInstaller，运行时FastAPI通过StaticFiles服务
- 端口自动选择可用端口，避免冲突
- 插件目录: plugins/（内置）+ user-plugins/（用户自定义）
- 旧项目文件（01出口退税资料整理/）保留作参考，不参与新项目

## 开发命令

```bash
# 后端
cd backend && pip install -r requirements.txt
python -m uvicorn backend.app:app --reload --port 8088

# 前端
cd frontend && npm install && npm run dev

# 验证
python -c "from backend.app import app; print('OK')"
```

## 详细设计

见 [DESIGN.md](DESIGN.md)
