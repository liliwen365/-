# 项目学习日志

> 记录非显而易见、会重复出现的经验教训。
> 每条学习记录格式：`- [日期] 经验内容 → 适用场景`
> 超过 100 条时触发 consolidation（合并去重、升级为 rule 或 memory）

## 开发经验

- ~~[2026-06-01] engine.py 和 plugin.yaml 列名必须统一用英文 snake_case~~ → 已升级为 plugin-rules.md
- ~~[2026-06-01] conftest.py 的 license_code 插入必须在 TestClient context 内部~~ → 已升级为 test-rules.md
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
