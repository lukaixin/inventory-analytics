# 智能体接手指南：接入真实数据与退出演示模式

更新日期：2026-10-25。本文件供首次进入仓库的智能体与工程师使用。

**当前决定：保留演示。真实数据接入并验收后，再移除正式用户路径中的 mock。**
当前主流程使用合成管理数据，用户工作电脑上的真实资料暂不可共享；不要猜测字段、阈值或业务数值，也不要把演示改名为“真实”后交付。

## 1. 先读什么

1. 根目录 `AGENTS.md`，以及将要修改目录下的 `backend/AGENTS.md`、`frontend/AGENTS.md`。
2. `README.md`、`docs/project_status.md`：启动方法、当前事实和未验收范围。
3. `docs/ENGINEERING_RULES.md`、`docs/WORKFLOW.md`：保护边界、职责和交付流程。
4. `docs/DATA_CONTRACT.md`、`docs/API_CONTRACT.md`。
5. `docs/V6_RECONSTRUCTION_CONTRACT.md`：三主页面、四时点与管理数据结构。
6. `docs/OVERVIEW_STRUCTURE_RULES.md`：结构占比、确定性结论与完整性规则。
7. `docs/DATABASE_PORTABILITY.md`、`docs/DEPLOY.md`：DuckDB、PG和生产边界。

仓库中的历史验收只证明当时的合成/转录版本；不能代替真实数据验收。缺失的本地私有资料或截图，不要从演示数字反推。

## 2. 当前工程真实状态

- React + TypeScript + Vite → FastAPI → SQLAlchemy → 本地持久化 DuckDB。
- 默认工作区：趋势总览、明细分析、库存数据表；来源与专题保留历史转录、MWD和合成导入。
- `management_demo` / `management_demo_v1` 是管理演示系列及 payload schema。
- 主流程的库存事实、KPI、目标和预测均为合成；历史 `legacy` 是截图转录初稿。
- 管理数据保存在不可变 `DatasetVersion.payload`；旧 `inventory_detail` 使用关系化快照/明细表。
- 当前没有真实 ERP 管理数据导入器，也没有已批准的真实管理数据 schema/证据等级。
- 重点结论由后端确定性规则产生，无 LLM；规则是本地候选规则，尚未完成真实业务签字。
- PostgreSQL 是后续目标，当前未验证其运行迁移；SSO、生产部署和大数据量性能也未验收。

## 3. 代码从哪里入手

| 路径 / 入口 | 当前职责 | 接真实数据时关注 |
| --- | --- | --- |
| `backend/app/models.py` | Series、Version、SourceFile、ImportBatch、Snapshot、Item | 保留来源、不可变版本和当前指针；新表由迁移管理 |
| `backend/app/db.py`、`config.py`、`database_adapter.py` | 连接、环境、方言与写事务边界 | 正式配置、单写进程、PG差异 |
| `backend/migrations/versions/0001_initial.py` | 初始结构 | 不改已执行迁移；后续新增迁移 |
| `backend/app/seed.py::seed_management` | 导入管理合成夹具 | 只保留为演示初始化，不能承担真实导入 |
| `backend/app/services.py::validate_payload/preview/commit_batch` | 旧 canonical 合成明细导入 | 当前拒绝非 `SYNTHETIC_DEMO`，不是管理事实导入通道 |
| `backend/app/management.py::_payload/catalog/overview/analysis/inventory_table/management_export` | 管理查询、四时点、树表和导出 | 当前限定 demo kind/schema；接入适配层与正式 schema 校验 |
| `backend/app/management_overview.py::enrich_overview` | 结构、勾稽、五条规则与证据 | 完整人口、缺失抑制、规则版本、正式指标定义 |
| `backend/app/policy.py::ActorContext/AccessPolicy` | 服务端范围权限 | 真实身份、业务线授权，查询/导出/来源一致 |
| `backend/app/services.py::source_for_version/evidence_for_version` | 来源与证据访问 | 新系列必须进入同等权限控制，不能漏过 kind 分支 |
| `backend/app/main.py` | HTTP路由、数据集/版本列表、导入 | 新写入流程、只读DTO、元数据访问范围 |
| `frontend/src/App.tsx` | 默认系列、三个主页面、辅助专题 | 当前选择 demo、固定标识、来源选择和空态 |
| `frontend/src/OverviewStructure.tsx` | 结构、历史展开和规则证据 | 保留 API 驱动与缺失/部分覆盖显示 |
| `frontend/src/api.ts` | 数据类型与API客户端 | kind/schema扩展、真实元数据与响应类型 |
| `data/management-demo.json`、`management-demo-manifest.json` | 确定性管理夹具 | 仅测试/演示，不作为正式来源 |
| `data/synthetic-inventory.json`、`scripts/generate_management_demo.py` | 旧样例与管理夹具生成器 | 正式启动不运行；测试可保留 |

用函数名搜索定位，行号会随版本变化。前端不得自行计算正式 KPI、汇总或规则结论。

## 4. 先收集来源与业务确认，不先“清洗成合理值”

在获准的私有目录保存原始导出，记录文件 SHA-256、导出时间、数据截止日、系统/报表、负责人及访问范围。
原始 Excel/CSV、数据库、备份、客户/物料明细、凭据和带业务数据的截图都不进 Git；私有仓库也不是企业数据存储。
先确认 `.gitignore` 覆盖实际使用的私有目录，再落文件；日志和测试报告也不得带真实明细或连接密码。

建立一份**私有字段映射表**，至少回答下列问题：

| 来源内容 | 目标字段 / 概念 | 必须确认 |
| --- | --- | --- |
| 数据日期、报表期间 | snapshot key、`exact_date`、period key | 来源内部日期与文件名冲突时拒绝；不按名称猜日期 |
| 当前/年初/年中/月初 | `snapshot_manifest` 四个 alias | 业务实际定义与精确快照；不能用最近日期补齐 |
| 库存明细主键 | `snapshot_key + record_key` | 物料、仓库、批次等真实粒度；行号不自动成为业务主键 |
| 业务线、项目、物料小类 | 对应 id/name | 正式编码、别名、组织变化、权限范围 |
| 库存形态 | `raw/semi_finished/finished` | 源分类到三形态的确认映射；其他类别如何处理 |
| 金额、成本口径 | `inventory_amount`、`amount_known` | 币种、元/万/亿、含税、成本类型；缺失不能变0 |
| 数量与单位 | `quantity`、`quantity_unit`、`quantity_additive` | 件/箱等单位与能否相加；跨单位不直接求和 |
| 库龄或入库依据 | 八个 `aging_bucket` / `UNKNOWN` | 源桶、边界与算法；粗桶不能无依据拆细 |
| 周转、平均库存、时点库存、发货成本 | `metric_facts` | 正式公式、粒度、期间、单位、可加性、来源 |
| 管理目标与预测 | `targets`、`forecasts` | 独立来源、审批/版本、预测截至日及方法 |
| 各数据块覆盖范围 | 完整性与控制总额 | 缺整业务线/整形态与真实零库存如何区分 |
| 规则阈值与例外 | `risk_policies`、规则版本 | 生效日期、负责人、例外处理；当前成品>60天只是演示 |

仍未确认的正式周转公式、平均库存算法、币种、主键、阈值、四锚点定义和真实V6一致性，必须保持待确认状态。

## 5. 接口和计算必须保留的约束

- 四 alias 为 `YEAR_START / MID_YEAR / MONTH_START / CURRENT`，由同版本 manifest 解析；版本刷新不能悄悄混用旧快照。
- KPI事实按 `metric_id + period_key + scope_id + material_form` 定位；目标/预测还须使用 actual 的显式引用期间精确匹配。
- 不从集团目标回填业务线，不从 `ALL` 回填单形态，不用邻期或数组末项补目标。
- 周转、平均库存和发货成本沿用经确认的事实；不能求和、简单平均或用库存金额加权替代正式算法。
- 库存金额只在同快照授权叶事实内加总；父子不可重复相加，MWD/PO与长库龄不能混加。
- 金额与比例使用 Decimal；API传十进制字符串或null。展示舍入不能参与排名、并列判定或对账。
- 基期0时相对变化无定义；已知0有来源证据，缺行、缺金额、缺整个组成部分不能解释成0。
- 当前结构服务用全版本已知授权的“业务线×形态”检查缺组合；真实接入应补明确覆盖清单/零库存证明，避免把组织停用误当缺数。
- partial可显示已知小计；需要完整事实的占比、差值、排名及结论必须抑制，并标明哪一期不完整。
- 查询、结构、结论、历史、来源和导出必须先授权后聚合；前端筛选不是权限控制。
- `>180天金额/占比`是观察事实，`policy_risk_amount`是规则命中，两者不可互换。
- 五条 `OVR_*` 候选规则及其版本见结构规则契约；无命中只能说未触发已配置规则，不能说没有风险。

**单位键注意：**当前代码/夹具/API使用 `unit_policy.inventory_amount` 和 `detail_amount`；旧契约片段的名称现已统一；不要新增 `overview_amount` 别名。
接入时同步契约和实现，不要同时维护两套名称。
当前万元→亿元勾稽配置为 `reconciliation.point_inventory.conversion_divisor`；真实币种与单位确认后才能提供正式换算规则。

## 6. 分阶段实施

### A. 建立基线和隔离环境

记录当前 Git commit、系列/版本/current指针、来源SHA与验收结果；保护已有数据库、备份、版本和休眠PG资产。
在独立工作分支及私有数据库副本开发真实接入，避免把正式资料送入 demo seed。

```powershell
# 在仓库根目录；首次克隆安装依赖
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
Push-Location frontend
npm ci
npm run build
Pop-Location
pwsh -File scripts/bootstrap-local.ps1
# 仅首次本地演示初始化使用 -Seed
pwsh -File scripts/start.ps1 -Migrate -Seed
pwsh -File scripts/check.ps1
```

准备真实接入副本时，先检查忽略的 `.env` 中 `DATABASE_URL` 确实指向隔离文件；不要输出凭据。
真实候选库只迁移结构，不执行 `-Seed`。现有 `start.ps1 -Migrate` 仍会启动API；导入器若用独立写进程，须先停止API。

```powershell
pwsh -File scripts/stop.ps1
pwsh -File scripts/backup.ps1
# 数据库目标确认后才迁移；本脚本不负责创建真实导入器
pwsh -File scripts/start.ps1 -Migrate
```

### B. 先冻结真实输入合同，再实现只读解析和预览

输出字段映射、来源版本、指标字典、快照manifest、覆盖清单、单位和权限合同；不能确认的字段不填假值。
新增真实来源适配器：读取→结构/类型/日期/主键校验→隔离暂存→错误/样本/控制总额预览，预览不创建正式版本。
测试重复主键、错日期、未知映射、非有限数、单位冲突、重复带出的物料级金额，以及整块数据缺失。
现有 `/imports/preview` 只接旧合成 `inventory_detail`，不可直接拿来上传真实管理ERP文件。

### C. 新来源、新不可变版本和受控发布

先由契约决定新的正式series kind/schema及证据等级；这些名称不是当前已有能力。
实现服务端导入、schema校验、授权、幂等提交和审计，再创建新 `SourceFile`、`DatasetSeries`、`DatasetVersion`。
真实payload可先复用规范化接口形状，但不能继续伪装为 `management_demo_v1` 或只替换证据字符串。
大数据量应评估关系事实表/分析Mart/provider适配；现有JSON读路径不构成58万行或更大规模能力证明。
需要表结构变化时新增Alembic迁移；先在隔离库执行，不覆盖已提交payload，不自动切 current。
通过逐版本核对后，用受控服务事务切当前指针；当前没有管理系列通用发布API，需实现并测试，勿手工散改数据库。

### D. 核对、试运行、再切默认

逐快照/业务线/形态核对行数、主键、已知金额、未知数、库龄桶、控制总额和KPI勾稽；差额必须解释或阻止发布。
检查目标/预测缺失、部分覆盖、基期0、所有并列、单业务线权限、父子汇总、全筛选导出、规则证据及期间安全下钻。
至少重跑：

```powershell
pwsh -File scripts/test.ps1
Push-Location frontend
npm run build
Pop-Location
pwsh -File scripts/start.ps1
pwsh -File scripts/check.ps1
```

`test.ps1`每次创建独立DuckDB测试文件；其合成断言不能代替真实来源对账。
还要实测API、桌面/390px浏览器、快速筛选旧请求、失败重试、重启持久化和真实规模性能，并保存不含明细的验收报告。
业务确认字段/指标/规则，IT确认身份/部署后，才把正式系列设为默认；没有真实数据时显示空态，不静默回退demo。

## 7. 接入后逐项移除 mock 的清单

“移除”指正式用户路径退出演示；默认不删除历史版本、备份及有价值的隔离测试夹具。

| mock / 固定入口 | 切换动作 | 验收条件 |
| --- | --- | --- |
| `seed.py::seed_management`、`seed_legacy`、旧样例seed | 正式初始化不运行；演示另设显式选项/环境 | 新正式库无合成默认版本 |
| `management.py::_payload` 限定 demo kind/schema | 引入经审议的正式schema校验/provider路由，保留版本隔离 | 真实与demo可区分且拒绝错schema |
| `services.py` 来源/证据的demo kind分支 | 正式kind采用同等或更严格授权 | 越权来源/导出不可见 |
| `App.tsx` 按 `management_demo` 找默认系列 | 从获准正式系列/配置选择；不随意取第一项 | 当前版本、空态、回退明确 |
| `ManagementHeader`、顶栏、`ManagementEmpty`固定演示文案 | 改为API来源/证据/环境元数据驱动 | 不再把演示标真实，也不把真实标演示 |
| `api.ts` 的Dataset kind联合类型 | 同步正式kind和响应元数据 | TypeScript与后端合同一致 |
| `DEMO-*` 编码、演示单位、固定换算 | 用正式主数据和确认单位；缺映射拒绝/待核对 | 无“换标签不换数值” |
| `risk_policies`演示阈值、`supplied_demo`预测 | 替换为审批来源及有效期；缺失保持未提供 | 规则和预测均可追溯 |
| 分析页“按演示规则命中”等固定说明 | 按当前版本规则状态/来源显示 | 不宣称未批准阈值已生效 |
| SourcesTopics里的旧V4/MWD/合成导入 | 正式导航隐藏或隔离；仅管理员可进入演示维护 | 用户不会把旧时域混入正式分析 |
| `data/*demo*`、生成器、合成测试 | 可保留为测试fixture，禁止正式启动自动装载 | 缺真实来源时不fallback到fixture |

不要全局删除 `SYNTHETIC` 或 `DEMO` 字符串：测试应继续证明合成来源不会冒充正式来源。
也不要仅隐藏标识而继续请求demo版本；最后检查网络响应中的series/version/source/单位与页面一致。

## 8. 交付、回滚与下一位智能体

交付需包含：变更commit、源映射/审批记录、来源SHA、真实候选版本ID、当前指针、对账结果、权限/性能/浏览器证据、未完成项和回滚目标。
失败时停止正式发布，切回已验收的旧正式版本或连接；保留失败候选供审计，不删库、不覆写旧版本、不在DuckDB与PG双写。
PG迁移必须单独验证类型/约束、事务锁、数据搬迁、并发、备份和回归；不能承诺只改连接串即可完成。
当前生产模式明确拒绝启动；正式身份、最小权限与部署方案落地前不要解除该保护或对外暴露服务。

可交给下一位智能体的起始任务：

> 先读AGENTS与docs/REAL_DATA_ONBOARDING.md。真实数据位置为【私有目录/获准来源】，业务确认人为【负责人】。先只读盘点字段、主键、日期、单位、覆盖和控制总额，提交映射及差异清单；未确认项保持未知。随后按契约实现隔离预览、不可变新版本和对账，验证权限/导出/规则/持久化后再切正式默认。演示保留作测试，正式路径不回退mock；不上传真实数据、凭据或明细日志到Git。
