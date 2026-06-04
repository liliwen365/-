---
description: Vue 前端开发规则（匹配 frontend/ 目录）
globs: frontend/**/*.{vue,ts,js}
---

- 优先用 Element Plus 内置组件，引入新依赖前必须验证 EP 没有等效方案
- 分组标签输入: el-select + el-option-group + multiple + allow-create
- 步骤引导: el-steps + v-show + reactive currentStep
- 文件结果展示: el-table + el-drawer 详情面板
- 共享逻辑提取到 utils/，组件只 import 不重复实现
- 用户可见文本用中文，变量名用英文
