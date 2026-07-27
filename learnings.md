# 项目学习日志

> 记录非显而易见、会重复出现的经验教训。
> 每条学习记录格式：`- [日期] 经验内容 → 适用场景`
> 超过 100 条时触发 consolidation（合并去重、升级为 rule 或 memory）

## 开发经验

- [2026-06-01] _is_activated() 必须加 try/except 兜底，建表前查询会崩溃 → 涉及中间件/授权的代码
- [2026-06-01] SchemaTable 未实现的类型渲染不会报错，只是静默跳过 → 添加新字段类型时
- [2026-06-01] 智谱 MCP web-search-prime 的 Authorization header 不需要 "Bearer " 前缀也能用 → 配置 MCP 时
- [2026-06-01] guard-report-quality.sh 对非 HTML 文件有 npx 开销，报告专用 hooks 不应全局匹配 Edit|Write → 配置 hooks 时
- [2026-07-23] ProcessPoolExecutor 的 future.cancel() 对运行中子进程无效（返回 False、拿不到 pid）→ 要"取消即停/超时强杀"必须改用 multiprocessing.Process 自管(p.terminate→p.kill)；否则卡死任务占满池(max_workers=2)后续全假死 → 写需要取消/超时的后台任务执行器时
- [2026-07-23] 项目用 loguru(backend.logger)，模块若用标准 logging.getLogger 则 root logger 无 handler、INFO 全被丢弃（黑箱）；多进程并发写同一日志文件必须 logger.add(enqueue=True) 否则跨日轮转竞态丢日志 → 新增任何打日志的模块时
- [2026-07-23] FastAPI 路由里 raise ValueError 若在 try 块外，会被当 500 且丢消息；要单独 except ValueError → HTTPException(400, str(e)) 才能把校验消息透传前端 → 写带参数校验的 API 时
- [2026-07-23] 子进程异常经 multiprocessing.Queue 传回主进程后，默认只存数据库不 logger.error → 日志查不到插件失败原因；必须显式写日志且 get_status/history 透传 error_traceback → 设计异步任务可观测性时
- [2026-07-23] 模块级单例(如 task_runner)持有 asyncio loop 引用，pytest 每测试新 loop 时旧 loop 已 closed → "Event loop is closed"；需 if loop.is_closed(): 重新绑定+废弃旧 task → 写持有 loop 的单例+多测试时
- [2026-07-23] FastAPI 路由裸类型参数 `task_id: int` 默认收 query string；前端若放 body 会 422 且请求不进函数体(无日志), 表现为前端"操作失败"+后端零记录, 极易误判为业务bug。同文件 getStatus 用 `params:{task_id}` 是正确范式 → 写带简单类型参数的前后端接口时,务必对齐 query/body 传递方式
- [2026-07-27] Windows multiprocessing 用 spawn，子进程重新解释执行、不继承主进程的 loguru sink；_subprocess_entry 必须显式 `from backend.logger import logger` 才会配置文件 sink，否则不直接 import logger 的插件（bank/stock）子进程日志走默认 stderr，console=False 打包下 stderr=devnull → 全丢、排查零线索 → 写 multiprocessing.Process 子进程跑插件/任务时，入口函数必须显式触发日志配置

## 配置经验

- [2026-06-04] 配置经验（CLAUDE.md行数控制、rules懒加载、权限清理）已升级为全局 memory → 所有项目通用

## 工作流经验

- [2026-06-01] 先 Plan 再动手比直接写代码成功率高 2-3x，尤其是跨文件改动 → 所有非平凡功能
- [2026-06-01] Rewind > Correct：Claude 走偏时 Esc+Esc 回退比追加修正更有效 → Claude 输出不满意时
- [2026-06-04] slash command 内容是注入给 Claude 的指令，不是显示给用户的输出；/cheat 要用 Read 工具读文件再原样输出 → 写展示类 slash 命令时
- [2026-06-04] Stop hook prompt 类型用 haiku 快模型评估 session 价值，比 command 脚本更智能（能区分深度调试 vs 简单问答），command 适合确定性操作 → 类似"需要判断力"的自动化场景
- [2026-06-04] CLAUDE.md 过时检测（文章方案）和经验捕获（prompt hook）是互补的两个问题：前者保鲜规则，后者捕获新经验；小项目先上经验捕获更紧迫 → 规划自动化体系时
- [2026-06-04] MCP 工具权限名必须与 ~/.claude.json 中 mcpServers 的 key 完全一致（`mcp__{server_key}__{tool}`），server 被重命名后旧权限名会变成幽灵条目，不会报错但权限无效 → 添加/修改 MCP 权限时
- [2026-06-04] settings.local.json 中 `Bash(cmd args1)` 和 `Bash(cmd args2)` 两条权限，args1 是 args2 的子集时可以只保留超集那条 → 维护权限列表时
