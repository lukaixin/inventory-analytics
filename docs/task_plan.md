# 任务计划与责任票

共同约束：只在inventory-v7内修改；不得还原他人代码；遵守根/模块AGENTS；契约以docs为准；不跨组变更共享语义。全部任务由root集成，QA独立回归；escalation_agent=contract_plan。完成报告须给改动、检查、结果、风险、契约影响和下一步。

| ticket_id | objective / scope / files | routing_class | semantic_risk | contract_change | accountable_owner | execution_owner | regression_owner | dependencies | acceptance / verification | expected_output / parallelism |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B01 | backend/** API/数据库迁移/seed/测试 | domain_execution | high | no（遵守冻结v1） | backend | backend | qa | 本文及数据/API冻结 | 真DuckDB迁移、seed幂等、导入事务、查询/权限测试 | 后端代码与实测报告；可并行F01/R01/D03 |
| F01 | frontend/** 五页及API客户端 | domain_execution | medium | no | frontend | frontend | qa | API/UX冻结 | 类型/构建、浏览器交互 | 前端及报告；可并行B01 |
| R01 | scripts/**,.runtime/**,.env,compose.yaml,deploy/**,docs/DEPLOY.md | domain_execution | medium | no | root | runtime_worker | qa | 文档基线 | 真实DuckDB可连接、生命周期脚本、持久化 | 运行脚本与环境证据；可并行B01/F01 |
| D03 | data/**,docs/DATA_SOURCES.md | domain_execution | medium | no | root | data_worker | qa | 数据冻结 | 旧数据哈希一致、合成四快照闭合 | 私有原始转录副本、合成JSON；可并行B01/F01 |
| Q01 | 只读全项目与evidence/qa*报告 | independent_review | high | no | root | qa | final_reviewer | 集成完成 | 独立重现关键测试、发现和复验 | QA判定；串行 |
| G01 | 只读最终交付门禁 | independent_review | high | no | root | final_reviewer | root | QA后 | 契约/产品/证据/保护区一致 | PASS等结论；串行 |

spawn_required：B01、F01、R01、D03、Q01、G01均为是。状态和修复轮次记录在state，不在此重复动态状态。

## UI-P01 — 2026-10-25
用户请求 Data 优化数据呈现、字体及结构，可参考 Visualize。视觉方向和数据边界已先写 PRODUCT_UX。frontend worker 独占 frontend/src；root负责文档、集成、浏览器验证；独立QA审查。先存原源码/桌面截图和3系列3版本基线。数据库及API不变，既有PG资产保留。

## V6-D01 / V6-B01 / V6-F01 实施任务票（2026-10-25）
- objective：依据V6_RECONSTRUCTION_CONTRACT构建三核心业务页、独立管理演示版本与服务端查询；不是V4美化。
- routing_class：domain_execution；semantic_risk：high；contract_change：yes（新增management族）。
- accountable_owner：root；execution_owner：各领域worker；regression_owner：QA；escalation_agent：v6_contract。
- files_or_modules：D01独占data/management-demo.json、data/management-demo-manifest.json、scripts/generate_management_demo.py；B01独占backend/app与backend/tests；F01独占frontend/src。
- constraints：不覆盖旧版本/保护区；不写正式ERP数据；无业务数组前端硬编码；证据级别SYNTHETIC_MANAGEMENT_DEMO；未知不置零；DuckDB单写进程，PG资产保留。
- dependencies：本轮契约；Planner补齐精确JSON附录后输出保持一致；后端/数据共享契约，前端使用服务API。
- acceptance_criteria：目标/预测精确匹配、四Alias、同人口分析、三级树/父子勾稽、授权/导出、持久化/重启、三页桌面390px、辅助页保留。
- verification_method：数据确定性与勾稽；后端隔离pytest；前端build；root浏览器；独立QA和Final。
- expected_output：文件、命令、验证、风险与契约差异清单。
- spawn_required：yes；expected_parallelism：3（文件互斥）。

## OV-P01 / OV-B01 / OV-F01 — 总览结构和规则（2026-10-25）
- objective：补回Photo2库存结构、月度业务线展开和确定性重点结论。
- routing_class：decision→domain_execution→independent_review；semantic_risk：high；contract_change：yes，新增只读派生响应。
- accountable_owner：root；Planner：overview_contract；Backend：overview_backend；Frontend：v6_chart_race_fix；regression_owner：独立QA。
- ownership：Planner仅docs/OVERVIEW_STRUCTURE_RULES.md；Backend仅backend/app与backend/tests；Frontend仅frontend/src；Root仅集成/证据/状态。
- protected：data/management-demo*.json、开发库payload、旧系列及父目录保护文件均不改变，无seed/迁移。
- evidence：evidence/overview-structure/intake.md、qa-inventory.md与后续API/浏览器报告。
- acceptance：总览直接呈现结构；周转不加总不分摊份额；金额构成、规则及筛选人口一致；月度展开、规则条件证据、null/partial/tie/zero/权限、桌面390及失败重试有证据。
