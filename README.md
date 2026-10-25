# 远图库存健康与风险看板 · V7

私有仓库：[lukaixin/yuantu-inventory](https://github.com/lukaixin/yuantu-inventory)，默认分支`main`。

独立Server-first小应用：浏览器 → FastAPI → 本地DuckDB。默认工作区为趋势总览、明细分析、库存数据表；历史转录、MWD、库存探索和版本管理保留在来源与专题中。不依赖V6代码。

## 新智能体从这里开始

先读[AGENTS](AGENTS.md)，再读[真实数据接入与mock退场指南](docs/REAL_DATA_ONBOARDING.md)。指南给出代码入口、字段映射、真实导入器的缺口、验证及回滚步骤。**本次保留演示，真实数据接入并验收后再移除正式用户路径中的mock。**

仓库仅包含源码、工程文档和明确标记的合成夹具。`.env`、数据库/备份、休眠PG二进制及凭据、历史转录私有副本、原始资料和`evidence/`本机档案不随仓库分发。可移交需求摘要见[需求证据](docs/REQUIREMENTS_EVIDENCE.md)。历史日志中出现的本机路径不是新机器的运行依赖；新机器按下方初始化命令重建环境。

[首次交接验证](docs/REPOSITORY_VALIDATION.md)：干净源码导出中迁移和前端构建通过，后端27通过、1项可选私有历史测试跳过。本机有该私有副本时完整28项通过。

## 当前交付

2026-10-25：按用户照片及恢复到的GPT上下文重构核心业务内容。最新版V7架构说明与V6快照/Release语义已读取，完整V6功能正文及工作电脑代码不可得，因此本地版本不声称与V6逐项一致。见[本轮契约](docs/V6_RECONSTRUCTION_CONTRACT.md)、[需求证据](docs/REQUIREMENTS_EVIDENCE.md)与[项目状态](docs/project_status.md)。

新增独立管理演示版本：11个快照、792条库存事实、1232条预计算指标事实、9条目标和16条预测，全部标记为合成数据。旧3系列/3版本/249条明细保留，当前共4系列/4版本。历史转录仍含56条趋势、36组库龄、8个MWD汇总、35条可见明细、18项核对和2142个来源引用。

- 趋势总览：四项KPI、实际/目标/预测、分析期与基期比较；目标和预测严格匹配期间及范围，缺失不回填。主趋势下直接展示库存结构、业务线实际历史及月度展开，并提供规则式重点结论与可展开数值依据。
- 明细分析：年初/年中/月初/当前快照、金额及超过180天金额/占比、业务线和物料形态构成。
- 库存数据表：业务线→项目→物料小类展开、八个库龄桶、金额/数量、风险筛选、排序、搜索和全筛选范围CSV。
- 快照日期来自版本manifest；长库龄与规则风险分开，原料/半成品风险阈值尚未确认。未知金额和不可加数量不填0。

结构支持周转/库存金额切换：周转使用预计算事实，金额使用同快照明细及适用份额；重点结论使用后端确定性候选规则，包含并列增量贡献、长库龄金额/占比方向、精确目标差与数据覆盖提示。原对话留存确认规则方向，但完整V6规则正文未恢复，具体规则定义见[库存结构与规则](docs/OVERVIEW_STRUCTURE_RULES.md)，本轮验证见evidence/overview-structure/。

## 技术与目录

Python3.13、FastAPI、SQLAlchemy、Alembic、DuckDB1.5.6 / duckdb-engine；React19、TypeScript、Vite、Node24。精确版本由backend/requirements.lock.txt和frontend/package-lock.json记录。

- backend/：API、服务、数据库adapter、迁移和测试。
- frontend/：React页面、共享API客户端和构建。
- data/：合成夹具；private/保存忽略的历史转录副本。
- docs/：需求、军规、流程、数据/API/UX契约和部署。
- scripts/：初始化、启动、停止、检查、测试和备份。
- state/、evidence/：分工状态、复盘及验收证据。
- .runtime/：忽略的数据库、日志、备份和休眠PG资产。

## 本机运行（PowerShell 7）

在仓库根目录执行。新克隆先完成下一节初始化；本机已有依赖、数据库、样例和前端构建：

```powershell
pwsh -File scripts/start.ps1
pwsh -File scripts/check.ps1
```

打开[本地应用](http://127.0.0.1:8170)和[API文档](http://127.0.0.1:8170/docs)，默认仅监听127.0.0.1。

```powershell
pwsh -File scripts/stop.ps1
pwsh -File scripts/backup.ps1
```

关闭API才可迁移、seed或备份。DuckDB当前只运行一个后端写进程，不启动多个worker。

## 新环境初始化

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
Push-Location frontend
npm ci
npm run build
Pop-Location
pwsh -File scripts/bootstrap-local.ps1
pwsh -File scripts/start.ps1 -Migrate -Seed
```

历史转录副本不入Git。新克隆如缺data/private/legacy-reviewed.json，seed仅导入合成数据；复制历史数据须保持来源SHA。.env由初始化生成且被忽略，.env.example仅示例，勿提交私有配置。

开发前端在frontend运行npm run dev，地址5177，代理API8170。日常后端同源托管frontend/dist。

## 检查

```powershell
# 每次创建隔离测试文件，不写开发库
pwsh -File scripts/test.ps1
Push-Location frontend
npm run build
Pop-Location
```

本机含可选私有历史副本时28项隔离后端测试通过；干净仓库源码为27项通过、1项因缺少该私有副本跳过。前端构建、桌面/390px浏览器、延迟请求竞态、失败重试、CSV勾稽及重启持久化已在本机通过，记录见evidence/v6-alignment/；初版及视觉优化记录分别保留在evidence/与evidence/ui-polish/。58万行性能、正式ERP/SSO、企业上线和PG运行未验收。

## 数据和后续部署

历史数据是截图转录初稿，未逐格签字验收；年份未知，不补造日期。合成DEMO明细与历史汇总隔离，未知不当0，MWD和库龄不叠加。原142个文件哈希检查无差异。

PG17.11包、程序、未启动空集群按用户要求保留在.runtime，日常启动不使用。后续切PG需要连接/方言、迁移、数据搬迁、事务并发和回归，前端API保持稳定；见[数据库切换](docs/DATABASE_PORTABILITY.md)。服务器和权限待IT确认，当前生产模式拒绝启动。见[部署指南](docs/DEPLOY.md)。

开发前读[AGENTS](AGENTS.md)、[军规](docs/ENGINEERING_RULES.md)、[流程](docs/WORKFLOW.md)、[数据契约](docs/DATA_CONTRACT.md)和[API契约](docs/API_CONTRACT.md)。

常见问题：8170占用先核对进程；DuckDB锁冲突先停其他写进程，不删数据库；页面空白先构建frontend/dist；服务日志在.runtime/backend.err.log。备份可读不等于完整生产恢复演练。

## 2026-10-25 数据呈现优化
已按新的产品视觉要求调整五页：深蓝侧栏与浅色分析区、统一字体/筛选/表格、2×2核心指标趋势、真实刻度与点选读数、忠实的零值/缺失条形。数据版本、来源及时间边界保留。

验证记录与前后截图见 `evidence/ui-polish/`。浏览器实测桌面1440px、窄屏390px五页无文档横向溢出；月份与基期、来源、客户筛选/清除、空态、请求重试、分页/导出、库龄和MWD范围、模板下载通过。现有3系列3版本未改变。本次未提交导入或更改业务数据。
