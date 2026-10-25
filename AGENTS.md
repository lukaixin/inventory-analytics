# Project engineering instructions

## Project profile

- Backend: Python FastAPI + SQLAlchemy
- Frontend: React + TypeScript + Vite
- Database: persistent DuckDB now; PostgreSQL later through isolated dialect/transaction adapters.
- Package/build tools: Python venv/pip; npm lockfile; PowerShell scripts.

## Working agreement

Read this file before changes. Read `backend/AGENTS.md` and/or `frontend/AGENTS.md` when touching those areas. Preserve existing user changes and make the smallest reliable change that meets the request. Prefer simple, stable solutions over speculative infrastructure or abstraction.

Do not commit secrets. Use `.env` locally and keep `.env.example` safe to commit. Track schema changes through Alembic. Keep README, API contracts, tests, and configuration aligned with behavior.

## Validation and handoff

Run backend pytest against isolated temporary DuckDB files, frontend `npm run build`, live API checks and browser journeys. PostgreSQL portability is static-only until separately migrated and tested. Report commands actually run, result, unrun checks and reason, known issues, and any user action required. Do not claim deployment or integration success without evidence.

## 项目军规与职责

必须读 `docs/ENGINEERING_RULES.md`、`docs/WORKFLOW.md`、`docs/DATA_CONTRACT.md`、`docs/API_CONTRACT.md` 和 `docs/PRODUCT_UX.md`。当前是独立V7本地首版；旧V6代码不继承，用户授权范围为本地开发和测试。

- Root只负责需求/契约落档、派工、集成和交付判定；Planner处理改变语义的决策；Worker只写指定文件；QA只读审查；Final Reviewer提供最终门禁意见。
- 探索→Explorer；跨域决策→Planner；明确机械修复→Fast Worker；多文件实现→领域Worker；独立审查→QA。
- 保护父目录的全部已有文件，禁止覆写；候选产物仅放本项目。数据库/卷不删除，密钥不输出；不得修改用户级Codex配置或记忆。
- 数据源转录初稿和合成样例完全分开；未知为null；不假下钻、不把月份补成年份、不把MWD和库龄合计。
- 必须文档及契约先行，再并行实现；完成标准是DuckDB真实持久化、API、前端及浏览器证据通过且状态记录一致。用户最新指令覆盖最初PG选择；保留已下载PG资产，不删除。
- 分工表/任务票见 `docs/task_plan.md`；回合、发现及复盘见 `state/agent_run_log.md`。允许例行技术修复持续推进，范围/语义改变先回Planner。
- 代理并行度按依赖而定，结束任务归档结果；无结束线程工具时记为已完成idle，不声称销毁。

## V6业务内容重构约束（2026-10-25）

先读`docs/V6_RECONSTRUCTION_CONTRACT.md`和`docs/REQUIREMENTS_EVIDENCE.md`。用户工作电脑上的V6文件不可共享，按可读取GPT上下文和照片重构；不得将V4、本轮合成数据或未恢复功能冒称最新V6事实。三个核心页面优先于辅助专题。版本内manifest统一解析四快照；官方KPI由后端提供，金额单位、数量可加性、过滤人口和导出必须一致。已有管理版本不可覆写，改夹具须生成新版本标签及来源SHA。

## 仓库交接与真实数据接入（2026-10-25）

用户已授权创建并推送本工程及AGENTS，后续明确要求将仓库更名为中性名称并开源，许可证选择MIT。仓库为`lukaixin/inventory-analytics`。当前演示继续保留；真实接入时按`docs/REAL_DATA_ONBOARDING.md`逐项替换演示入口和数据提供方，再移除默认mock展示。授权不包含未来生产部署或上传企业真实数据。

新智能体先读README和真实接入文档。真实数据、原图/工作簿、数据库/备份、日志、密钥、`.env`及本机`evidence/`不得进入Git。仓库中的data文件是可复现测试/演示夹具；保留其合成标识。不得只改证据等级、单位或标签来冒充真实接入，也不得删除历史版本/休眠PG资产。历史evidence路径仅是本机验收档案，跨机器使用docs中的摘要与可重跑检查。
