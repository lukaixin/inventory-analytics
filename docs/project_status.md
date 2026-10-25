# 项目状态

## 当前轮：2026-10-25 总览结构与规则结论补齐

- 已直接补回总览库存结构：范围及三形态卡、周转/时点库存金额切换、业务线当前值/基期差/适用占比、实际历史缩略图与月度展开。
- 重点结论由后端`management_overview_rules_v1`确定性产生；包含完整覆盖检查、形态/业务线正增量及全部并列、长库龄金额/占比方向、精确周转目标差。可展开中文条件和数值/来源依据，非AI生成。
- 原对话旧留存已确认结构化数据/规则方向；最新版完整规则正文未恢复。本轮为公开定义的本地候选规则，见docs/OVERVIEW_STRUCTURE_RULES.md。
- 修复并复核：基期partial不排名、缺事实不当0、缺整形态/整业务线的组合完整性、完整零分母不误报缺数、目标缺省覆盖状态、并列不任取实体下钻、稳定证据字段与中文精度。
- 验证：隔离28测试、前端build、独立金额/占比勾稽、月度11点、桌面1440/390px、键盘/触屏、旧请求防回写及503恢复；所有浏览器pageerror为空。
- 数据：4系列/4版本/旧249明细，持久化payload与原合成夹具完全相同；142保护文件无变化；重启前后新总览结构与规则响应不变。
- 最终门禁：独立QA与Final均PASS WITH FINDINGS，无开放P0/P1；Root批准APPROVE_LOCAL_OVERVIEW_STRUCTURE_AND_RULES。证据目录evidence/overview-structure/。

## 上轮：V6业务内容重构

### 2026-10-25 V6业务内容重构记录

- 依据：用户4张页面照片、恢复到的GPT最新V7架构和V6 Release/快照说明；完整V6正文和工作电脑代码不可得。
- 默认三个核心页面，原有功能保留在来源与专题。新管理演示数据独立系列，不升级旧转录证据等级。
- 本地数据库现4系列/4版本，旧249条明细不变；新增管理payload含11快照/792库存事实/1232指标事实/9目标/16预测。
- 已验证：seed首次True、再次False；离线备份可读；142保护文件哈希无变化；管理数据生成器校验通过。
- 验证：后端隔离26测试、前端构建、三级树表金额、单位换算及筛选导出通过。四主入口1440/390px无文档横向溢出，无pageerror；季度目标覆盖实际季度；快速筛选/下钻/展开全部的旧响应不能回写；总览与分析503重试恢复；重启后4系列与管理总览不变。
- 独立QA：PASS WITH FINDINGS，无开放P0/P1；最终门禁报告见evidence/v6-alignment/final-gate.md。
- 未验收：真实V6完全一致性、正式风险阈值/业务签字、ERP/58万行性能、SSO/生产、PG运行迁移。非阻断维护：favicon.ico 404、TestClient弃用提示。
- 所有旧交付记录仅代表各自阶段，本轮以evidence/v6-alignment/及后续最终判定为准。

## 历史交付记录

- 日期：2026-10-24（Asia/Shanghai）
- 阶段：本地DuckDB演示首版已完成交付门禁。
- 已完成：文档/军规/契约先行；五页React应用、FastAPI、DuckDB迁移/种子/导入/版本/来源；启动停止和备份。
- 当前数据库：用户后续改为DuckDB；PG下载包、程序和未启动空集群保留，项目PG库未创建。
- 数据：历史56趋势/36库龄/8MWD汇总/35明细/18核对；合成246条；浏览器导入示例3条，共3系列/3版本/249明细。
- 验证：20后端测试、npm build、真实浏览器五页/筛选/来源/分页/空态/导入/CSV、390px五页无溢出；142个旧文件哈希不变。
- 修复：畸形导入500、同SHA并发、数值边界、授权、全未知/已知零、库龄差额、版本选择/成功提示、窄屏网格。
- 过程记录：QA一次URL构造失败导致seed误用开发库，额外生成幂等导入批次，未增加正式版本/明细；HTTP复核当时仍2版本246行。之后3行浏览器示例为有意导入。详见QA记录。
- 未开始：完整最新V7设计核对、真实ERP/业务签字、58万行性能、SSO/正式授权、企业部署、PG运行迁移、完整恢复演练。
- 本地地址：http://127.0.0.1:8170；按README启动停止。当前不发布、不推送。
- 交付判定：Final Reviewer = PASS WITH FINDINGS；Orchestrator = APPROVE_LOCAL_DUCKDB_DEMO。无阻断项。TestClient/httpx弃用提示由backend负责后续依赖维护；state跟踪口径已在收口同步。

## 2026-10-25 UI呈现改进
- 已完成深蓝侧栏、浅色分析区、字体与表格层级、可访问图表读数、比例条形与时间跨度提示。
- npm run build通过；隔离DuckDB20测试通过；五页1440/390px无文档溢出，pageerror为空；已有142保护文件哈希未变。
- 3系列3版本与本轮前基线完全相同。数据接入/部署能力与上轮边界一致；现有TestClient弃用提示仍为后续维护项。
- 详细证据：evidence/ui-polish/browser-results.json、independent-review.md、各页前后截图。

UI-P01最终独立复核：PASS（evidence/ui-polish/independent-review.md）。Root交付判定：APPROVE_LOCAL_UI_POLISH。验收证据包含键盘/触屏图表读数、月份同步、五页宽度、无pageerror及数据版本不变。原有本地演示数据等级与未来部署待办保持。

2026-10-25 本轮最终判定：QA及Final Gate均PASS WITH FINDINGS，Root批准APPROVE_LOCAL_V6_CONTENT_RECONSTRUCTION。无本地演示阻断项；服务8170保留运行，验收浏览器已关闭。正式数据/PG/生产验收仍未开展。

## 2026-10-25 GitHub首次移交
用户授权新建GitHub工程并推送，明确这次继续保留演示；真实接入后按交接清单移除正式路径mock。新增REAL_DATA_ONBOARDING与REQUIREMENTS_EVIDENCE、仓库验证摘要，根/模块AGENTS随源码移交；忽略所有本地evidence、配置、运行库、真实资料及备份。干净暂存源码导出中迁移、27passed/1可选历史skip、npmci/build通过。远端创建及推送待独立复核后执行。
