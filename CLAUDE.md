# 本地自动化平台 - Claude Code 项目规范

## 元规则（最高优先级）

1. **本文件行数上限150行**。超过150行后指令遵循率显著下降。每新增规则必须评估：删掉这行Claude会犯错吗？不会则不加。
2. **规则仅写非默认约定**。Claude从代码可推断的不写，linter能检查的不写，显而易见的不写。
3. **先查后造**。实现任何非trivial功能前，先查社区方案、标准库、成熟框架，优先采纳而非自研。自研仅在没有合格现有方案时。

## 项目概述

本地自动化平台（LocalAgent）。Python运行时+Web管理界面，通过安装插件实现各类自动化需求。文件整理是第一个内置插件。

**技术栈**: Python + FastAPI + Vue 3 + Element Plus + SQLite
**运行平台**: Windows（员工） / macOS（开发）
**当前版本**: v0.1.0

## UI组件原则

- **优先用Element Plus内置组件**，不造轮子。引入新依赖前必须验证EP没有等效方案
- 分组标签输入: `el-select` + `el-option-group` + `multiple` + `allow-create`
- 步骤引导: `el-steps` + `v-show` + reactive `currentStep`，不引入wizard库
- CSV/Excel解析: PapaParse（标准库），Excel粘贴=TSV解析（`split('\n').map(r=>r.split('\t'))`）
- 文件结果展示: `el-table` + `el-drawer`详情面板

## 插件开发规范

- plugin.yaml声明参数Schema，前端通用渲染引擎自动生成UI
- **列名统一用英文snake_case**（task_id, dest_root），后端engine和前端共享同一命名，不用中文列名
- 关键字输入用标签组件，不用冒号/分号文本格式
- 模板JSON的key必须和plugin.yaml的列名一致
- 插件执行通过WebSocket推送进度，前端实时显示

## 代码规范

- 用户可见文本用中文，变量名/函数名用英文snake_case
- 常量用UPPER_SNAKE_CASE
- 不写注释解释"是什么"，仅写"为什么这样"的非显而易见原因
- API路径用kebab-case: `/api/plugins/file-organizer`

## 关键约束

- 前端打包为静态文件嵌入PyInstaller，FastAPI通过StaticFiles服务
- pystray必须在主线程运行（macOS AppKit要求），FastAPI放后台线程
- SPA路由: FastAPI catch-all `/{full_path:path}` 返回index.html
- 授权: RSA公钥验证，平台级授权，前台不显示剩余天数
- 插件目录: plugins/（内置）+ user-plugins/（用户自定义）

## 已踩坑记录

- engine.py用中文列名但plugin.yaml用英文，数据传递会断裂——必须统一
- engine.py缺`format_eta`函数会NameError——需补全
- SchemaTable未实现tags类型渲染——需补全

## 开发命令

```bash
python main.py                        # 完整启动（FastAPI+托盘+浏览器）
cd backend && python -m uvicorn backend.app:app --reload --port 8088  # 仅后端
cd frontend && npm install && npm run dev                             # 仅前端
python license_tool.py gen-keys       # 生成RSA密钥对
python license_tool.py issue <mid> <days>  # 签发授权
```

## 详细设计

见 [DESIGN.md](DESIGN.md)
