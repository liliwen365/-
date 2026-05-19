# 本地自动化平台 — 技术架构设计

## 一、产品定位

**本地自动化平台（LocalAgent）**：安装在员工电脑上的Python运行时+Web管理界面，通过安装不同"插件"实现各类自动化需求。

- 不是单一工具，是可扩展的平台
- 文件整理是第一个内置插件，后续可加发票处理、报表生成、截图采集等
- 授权控制平台层面，插件可按需授权

## 二、系统架构

```
用户浏览器
    │
    ▼ HTTP / WebSocket
┌──────────────────────────────────┐
│         FastAPI 后端              │
│                                  │
│  ┌────────┐ ┌──────┐ ┌────────┐ │
│  │授权服务 │ │插件   │ │任务调度 │ │
│  │        │ │管理器 │ │器      │ │
│  └────────┘ └──┬───┘ └────────┘ │
│               │                  │
│  ┌────────────▼────────────────┐ │
│  │      插件运行时              │ │
│  │  ┌────────┐ ┌────────┐     │ │
│  │  │插件A   │ │插件B   │ ... │ │
│  │  │(子进程) │ │(子进程) │     │ │
│  │  └────────┘ └────────┘     │ │
│  └────────────────────────────┘ │
│                                  │
│  ┌────────────────────────────┐ │
│  │  系统服务                   │ │
│  │  日志 / 配置 / 通知 / 托盘  │ │
│  └────────────────────────────┘ │
└──────────────────────────────────┘
         ↕
    本地文件系统 / NAS / Office / ...
```

## 三、技术栈

### 后端
| 组件 | 选择 | 版本 |
|------|------|------|
| Web框架 | FastAPI | 0.100+ |
| ASGI服务器 | uvicorn | 0.24+ |
| 插件加载 | importlib + yaml | 标准库 |
| 进程隔离 | concurrent.futures.ProcessPoolExecutor | 标准库 |
| 数据库 | SQLite (本地) | 标准库 |
| ORM | SQLAlchemy 2.0 | 2.0+ |
| 授权 | rsa | 复用现有 |
| 配置 | pydantic-settings | 2.0+ |
| 日志 | loguru | 0.7+ |
| 系统托盘 | pystray | 0.19+ |

### 前端
| 组件 | 选择 | 版本 |
|------|------|------|
| 框架 | Vue 3 | 3.4+ |
| 构建 | Vite | 5+ |
| UI组件库 | Element Plus | 2.5+ |
| Admin模板 | Vue Pure Admin 精简版 | 最新 |
| 状态管理 | Pinia | 2+ |
| 路由 | Vue Router 4 | 4+ |
| HTTP | axios | 1+ |
| WebSocket | native WebSocket | — |
| 图标 | @iconify/vue | — |

### 打包部署
| 组件 | 选择 |
|------|------|
| Python打包 | PyInstaller |
| 前端打包 | Vite build → dist/ |
| 安装包 | Inno Setup (Windows) |
| CI | GitHub Actions |

## 四、插件系统设计

### 4.1 插件目录结构

```
plugins/
├── file-organizer/              # 内置插件：文件整理
│   ├── plugin.yaml              # 声明式元数据
│   ├── main.py                  # 插件入口
│   ├── engine.py                # 核心逻辑
│   ├── schemas.py               # 参数Schema定义
│   └── assets/
│       └── icon.png
│
├── invoice-processor/           # 后续插件示例
│   ├── plugin.yaml
│   ├── main.py
│   └── schemas.py
│
└── user-plugins/                # 用户自定义插件目录
```

### 4.2 plugin.yaml 规范

```yaml
name: "file-organizer"
version: "1.0.0"
display_name: "文件整理"
description: "按规则搜索并整理文件到目标目录结构"
category: "file"                    # file / tax / report / custom
icon: "assets/icon.png"
color: "#2196F3"
author: "LocalAgent"

entry: "main:FileOrganizerPlugin"   # 模块:类名

# 插件提供的功能点（每个功能点对应一个页面/操作）
features:
  - id: "scan_and_copy"
    display_name: "扫描与整理"
    description: "扫描源文件并复制到目标目录"
    icon: "search"

# 参数定义（前端根据此Schema自动渲染表单）
params:
  - name: "tasks"
    type: "table"                   # table = 可增删改查的表格
    label: "任务清单"
    columns:
      - name: "task_id"
        label: "任务ID"
        type: "text"
        required: true
        width: 120
      - name: "dest_root"
        label: "目标存放路径"
        type: "path"
        required: true
        width: 200
      - name: "path_keywords"
        label: "路径关键词"
        type: "tags"                # tags = 多值标签输入
        group_by: "doc_type"        # 按文件分类分组
        width: 150
      - name: "file_keywords"
        label: "文件关键词"
        type: "tags"
        group_by: "doc_type"
        width: 150
      - name: "override_path"
        label: "特定搜索路径"
        type: "path"
        width: 150
      - name: "enabled"
        label: "是否执行"
        type: "switch"
        default: true
        width: 60

  - name: "rules"
    type: "table"
    label: "文件规则库"
    columns:
      - name: "doc_type"
        label: "文件分类"
        type: "select"
        options: ["发票", "报关单", "合同", "提单", "装箱单"]
        width: 100
      - name: "search_path"
        label: "源文件搜索路径"
        type: "path"
        required: true
        width: 280
      - name: "filename_pattern"
        label: "文件名模式"
        type: "text"
        placeholder: "如 *{PrimaryKeyword}*发票*.*"
        width: 200
      - name: "dest_subfolder"
        label: "目标子文件夹"
        type: "text"
        width: 120
      - name: "enabled"
        label: "是否启用"
        type: "switch"
        default: true
        width: 60

# 模板（预设配置，用户可一键加载）
templates:
  - name: "出口退税资料整理"
    file: "templates/export_tax.json"
  - name: "合同归档整理"
    file: "templates/contract.json"
  - name: "项目资料整理"
    file: "templates/project.json"

# 依赖声明（可选）
dependencies:
  pip:
    - "pandas>=1.5"
```

### 4.3 插件基类

```python
from abc import ABC, abstractmethod
from typing import Any

class BasePlugin(ABC):
    """所有插件必须继承此基类。"""

    @abstractmethod
    def get_info(self) -> dict:
        """返回插件元信息（从plugin.yaml自动加载，一般不需重写）。"""
        ...

    @abstractmethod
    def validate_params(self, params: dict) -> dict:
        """校验用户提交的参数，返回清洗后的参数。"""
        ...

    @abstractmethod
    def execute(self, params: dict, progress_callback=None) -> dict:
        """执行插件核心逻辑。

        Args:
            params: 用户配置的参数（已校验）
            progress_callback: 回调函数 callback(current, total, message)
        Returns:
            执行结果dict，包含 status/summary/data 等
        """
        ...

    def on_load(self):
        """插件被加载时调用（可选重写）。"""
        pass

    def on_unload(self):
        """插件被卸载时调用（可选重写）。"""
        pass
```

### 4.4 插件生命周期

```
1. 发现    → 扫描plugins/目录，解析plugin.yaml
2. 注册    → 写入插件注册表（SQLite）
3. 加载    → 动态import entry类，实例化
4. 配置    → 前端根据params Schema渲染配置表单
5. 执行    → 子进程调用execute()，通过Queue推送进度
6. 完成    → 结果写入数据库，前端展示
```

### 4.5 插件隔离策略

```python
# 主进程中执行插件
import concurrent.futures

def run_plugin(plugin_instance, params):
    """在子进程中执行插件，防止崩溃影响主进程。"""
    with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
        future = executor.submit(plugin_instance.execute, params)
        # 通过轮询future状态推送进度
        while not future.done():
            # 检查进度队列
            ...
        return future.result()
```

## 五、前端架构设计

### 5.1 页面结构

```
┌─────────────────────────────────────────────┐
│  Logo   本地自动化平台          用户 | 设置  │
├────────┬────────────────────────────────────┤
│        │                                    │
│ 仪表板  │  [当前页面内容]                     │
│        │                                    │
│ 文件   │                                    │
│  ├ 整理 │                                    │
│        │                                    │
│ 发票   │                                    │
│  ├ 处理 │                                    │
│        │                                    │
│ 报表   │                                    │
│  ├ 生成 │                                    │
│        │                                    │
│ ───── │                                    │
│ 插件   │                                    │
│  管理  │                                    │
│        │                                    │
│ 设置   │                                    │
│        │                                    │
└────────┴────────────────────────────────────┘
```

### 5.2 动态路由机制

```typescript
// 后端 GET /api/plugins/installed 返回:
{
  "plugins": [
    {
      "name": "file-organizer",
      "display_name": "文件整理",
      "category": "file",
      "icon": "folder",
      "features": [
        { "id": "scan_and_copy", "display_name": "扫描与整理" }
      ]
    }
  ]
}

// 前端动态注册路由
const installedPlugins = await fetchInstalledPlugins()
for (const plugin of installedPlugins) {
  router.addRoute({
    path: `/plugin/${plugin.name}`,
    component: () => import('@/views/plugin/PluginPage.vue'),
    meta: { plugin }
  })
}
```

### 5.3 Schema驱动渲染（核心）

插件不提供独立Vue组件，而是通过JSON Schema声明页面结构，前端通用渲染引擎自动生成：

```vue
<!-- PluginPage.vue -->
<template>
  <div class="plugin-page">
    <!-- 操作指引（首次使用） -->
    <GuideCard v-if="!hasHistory" :plugin="plugin" />

    <!-- 参数配置区（根据Schema动态渲染） -->
    <SchemaForm :schema="plugin.params" v-model="formData" />

    <!-- 操作按钮 -->
    <el-button @click="execute" :loading="running">
      {{ plugin.features[0].display_name }}
    </el-button>

    <!-- 实时进度 -->
    <ProgressBar v-if="running" :progress="progress" />

    <!-- 结果展示 -->
    <ResultTable v-if="result" :data="result" />
  </div>
</template>
```

### 5.4 Schema渲染器映射

| Schema type | 渲染组件 | 说明 |
|-------------|---------|------|
| text | el-input | 文本输入 |
| path | PathInput | 带浏览按钮的路径输入 |
| select | el-select | 下拉选择 |
| switch | el-switch | 开关 |
| tags | TagInput | 标签输入（替代冒号分隔） |
| table | SchemaTable | 可增删改查的表格（Excel式） |
| group_by | 分组标签 | tags按分类分组 |

## 六、API设计

### 6.1 核心端点

```
# 系统级
GET    /api/system/info              # 系统信息（版本、运行状态）
GET    /api/system/license           # 授权状态
POST   /api/system/license/activate  # 激活授权

# 插件管理
GET    /api/plugins/installed         # 已安装插件列表
GET    /api/plugins/:name/info        # 插件详情+Schema
POST   /api/plugins/:name/install     # 安装插件
DELETE /api/plugins/:name             # 卸载插件

# 插件配置
GET    /api/plugins/:name/config      # 获取插件配置
PUT    /api/plugins/:name/config      # 保存插件配置
POST   /api/plugins/:name/templates/:template  # 加载模板

# 插件执行
POST   /api/plugins/:name/execute     # 启动执行
POST   /api/plugins/:name/cancel      # 取消执行
GET    /api/plugins/:name/status      # 当前执行状态

# 任务历史
GET    /api/plugins/:name/history     # 执行历史
GET    /api/plugins/:name/history/:id # 历史详情

# WebSocket
WS     /ws/events                     # 实时事件流（进度/日志/状态变更）
```

### 6.2 WebSocket事件格式

```json
{
  "type": "progress",
  "plugin": "file-organizer",
  "data": {
    "current": 5,
    "total": 20,
    "message": "正在扫描: TASK001",
    "percent": 25,
    "eta": "2分30秒"
  }
}
```

## 七、项目结构

```
local-agent/
├── main.py                    # 入口（启动FastAPI+托盘+浏览器）
├── pyproject.toml             # 项目配置+依赖
├── requirements.txt           # 依赖列表
│
├── backend/                   # Python后端
│   ├── __init__.py
│   ├── app.py                 # FastAPI应用创建
│   ├── config.py              # 配置管理（Pydantic Settings）
│   ├── database.py            # SQLite数据库
│   ├── models.py              # SQLAlchemy模型
│   ├── auth.py                # 授权服务（复用）
│   ├── plugin_manager.py      # 插件管理器（发现/加载/卸载）
│   ├── plugin_runner.py       # 插件执行器（子进程+进度）
│   ├── base_plugin.py         # 插件基类
│   ├── ws_manager.py          # WebSocket管理器
│   ├── routes/                # API路由
│   │   ├── system.py
│   │   ├── plugins.py
│   │   └── auth.py
│   └── utils/                 # 工具函数
│       ├── tray.py            # 系统托盘
│       ├── notify.py          # 通知
│       └── logging.py         # 日志
│
├── plugins/                   # 插件目录
│   └── file-organizer/        # 内置：文件整理
│       ├── plugin.yaml
│       ├── main.py
│       ├── engine.py          # 复用现有engine.py逻辑
│       ├── schemas.py
│       ├── templates/
│       └── assets/
│
├── frontend/                  # Vue 3前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/
│   │   │   └── index.ts       # 动态路由注册
│   │   ├── stores/            # Pinia stores
│   │   │   ├── plugin.ts
│   │   │   ├── auth.ts
│   │   │   └── app.ts
│   │   ├── views/
│   │   │   ├── dashboard/     # 仪表板
│   │   │   ├── plugin/        # 通用插件页面
│   │   │   │   └── PluginPage.vue
│   │   │   ├── plugin-manage/ # 插件管理
│   │   │   └── settings/      # 设置
│   │   ├── components/
│   │   │   ├── schema/        # Schema渲染器
│   │   │   │   ├── SchemaForm.vue
│   │   │   │   ├── SchemaTable.vue
│   │   │   │   ├── TagInput.vue
│   │   │   │   └── PathInput.vue
│   │   │   ├── progress/      # 进度展示
│   │   │   └── guide/         # 操作指引
│   │   ├── api/               # API调用
│   │   └── utils/
│   └── public/
│
├── assets/                    # 全局资源
│   └── icon.ico
│
├── setup.iss                  # Inno Setup安装脚本
├── .github/workflows/         # CI
└── CLAUDE.md
```

## 八、开发路线

### Phase 1: 平台骨架（2-3天）
- [ ] 项目初始化（pyproject.toml + Vue Pure Admin精简版）
- [ ] FastAPI应用骨架 + SQLite数据库
- [ ] 插件管理器（发现/注册/加载）
- [ ] 插件基类定义
- [ ] 前端动态路由 + 通用插件页面框架
- [ ] 前端Schema渲染器（text/path/select/switch四种基础类型）
- [ ] 启动流程（main.py → FastAPI → 自动打开浏览器）

### Phase 2: 文件整理插件（2-3天）
- [ ] 迁移engine.py核心逻辑为file-organizer插件
- [ ] plugin.yaml完整参数定义
- [ ] Schema渲染器扩展：table类型、tags类型
- [ ] 模板加载功能
- [ ] WebSocket进度推送
- [ ] Excel/CSV批量导入任务
- [ ] 操作指引（GuideCard）

### Phase 3: 授权+产品化（1-2天）
- [ ] RSA授权迁移
- [ ] 授权激活页面
- [ ] 系统托盘（pystray）
- [ ] 配置持久化
- [ ] 日志系统

### Phase 4: 打包+部署（1-2天）
- [ ] PyInstaller打包配置
- [ ] 前端build嵌入
- [ ] Inno Setup安装脚本
- [ ] GitHub Actions CI
- [ ] Windows测试

### Phase 5: 第二个插件验证扩展性（后续）
- [ ] 开发第二个插件（发票处理或报表生成）
- [ ] 验证插件安装/卸载流程
- [ ] 验证Schema渲染器通用性
