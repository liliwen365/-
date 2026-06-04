---
description: 插件开发规则（匹配 plugins/ 目录）
globs: plugins/**/*
---

- plugin.yaml 声明参数 Schema，前端通用渲染引擎自动生成 UI
- 列名统一用英文 snake_case（task_id, dest_root），后端 engine 和前端共享
- 关键字输入用标签组件，不用冒号/分号文本格式
- 模板 JSON 的 key 必须和 plugin.yaml 的列名一致
- 插件执行通过 WebSocket 推送进度，前端实时显示
