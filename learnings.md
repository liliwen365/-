# 项目学习日志

> 记录非显而易见、会重复出现的经验教训。
> 每条学习记录格式：`- [日期] 经验内容 → 适用场景`
> 超过 100 条时触发 consolidation（合并去重、升级为 rule 或 memory）

## 开发经验

- [2026-06-01] _is_activated() 必须加 try/except 兜底，建表前查询会崩溃 → 涉及中间件/授权的代码
- [2026-06-01] SchemaTable 未实现的类型渲染不会报错，只是静默跳过 → 添加新字段类型时
- [2026-06-01] 智谱 MCP web-search-prime 的 Authorization header 不需要 "Bearer " 前缀也能用 → 配置 MCP 时
- [2026-06-01] guard-report-quality.sh 对非 HTML 文件有 npx 开销，报告专用 hooks 不应全局匹配 Edit|Write → 配置 hooks 时

## 配置经验

- [2026-06-01] CLAUDE.md 超过 60 行后规则遵循率下降，精简到 57 行 + rules/ 拆分效果明显 → 维护配置时
- [2026-06-01] .claude/rules/ 用 globs 按路径加载，比全部堆 CLAUDE.md 更省 token → 添加新规则时
- [2026-06-01] settings.local.json 中的一次性权限（如 cp 命令）应定期清理 → 维护权限时

## 工作流经验

- [2026-06-01] 先 Plan 再动手比直接写代码成功率高 2-3x，尤其是跨文件改动 → 所有非平凡功能
- [2026-06-01] Rewind > Correct：Claude 走偏时 Esc+Esc 回退比追加修正更有效 → Claude 输出不满意时
- [2026-06-04] slash command 内容是注入给 Claude 的指令，不是显示给用户的输出；/cheat 要用 Read 工具读文件再原样输出 → 写展示类 slash 命令时
- [2026-06-04] Stop hook prompt 类型用 haiku 快模型评估 session 价值，比 command 脚本更智能（能区分深度调试 vs 简单问答），command 适合确定性操作 → 类似"需要判断力"的自动化场景
- [2026-06-04] CLAUDE.md 过时检测（文章方案）和经验捕获（prompt hook）是互补的两个问题：前者保鲜规则，后者捕获新经验；小项目先上经验捕获更紧迫 → 规划自动化体系时
