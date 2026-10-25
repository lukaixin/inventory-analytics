# 任务板

| Ticket | Routing | Risk | Contract | Accountable | Execution | Regression | Status | Dependency | Next |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D01 | exploration | medium | no | root | source_discovery | root | DONE | 无 | 结果已归档 |
| D02 | exploration | low | no | root | runtime_discovery | root | DONE | 无 | 结果已归档 |
| P01 | decision | high | yes | root | contract_plan | qa | DONE | D01,D02 | 合同已冻结 |
| B01 | domain_execution | high | no | backend | backend_impl | qa | DONE | P01 | 后端实现 |
| F01 | domain_execution | medium | no | frontend | frontend_impl | qa | DONE | P01 | 前端实现 |
| R01 | domain_execution | medium | no | root | runtime_impl | qa | DONE | 文档基线 | DuckDB脚本与休眠PG资产 |
| D03 | domain_execution | medium | no | root | data_impl | qa | DONE | P01 | 数据夹具 |
| Q01 | independent_review | high | no | root | qa_review | final_reviewer | DONE | B01,F01,R01,D03 | PASS WITH FINDINGS |
| G01 | independent_review | high | no | root | final_gate | root | DONE | Q01 | PASS WITH FINDINGS，root批准本地交付 |
| V6-P01 | decision | high | yes | root | v6_contract | v6_qa | DONE | GPT+照片证据 | 重构契约冻结 |
| V6-D01 | domain_execution | medium | no | root | v6_data | v6_qa | DONE | V6-P01 | 确定性夹具校验通过 |
| V6-B01 | domain_execution | high | no | root | v6_backend | v6_qa | DONE | V6-P01,D01 | 后端26测试及语义修复通过 |
| V6-F01 | domain_execution | high | no | root | v6_frontend + v6_chart_race_fix | v6_qa | DONE | V6-P01,B01 | 最终浏览器与异常流程通过 |
| V6-Q01 | independent_review | high | no | root | v6_qa | final_reviewer | DONE | V6-B01,F01 | PASS WITH FINDINGS |
| V6-G01 | independent_review | high | no | root | v6_final_gate | root | DONE | V6-Q01 | PASS WITH FINDINGS，Root批准本地候选版 |
| OSR-P01 | decision | high | yes | root | overview_contract | overview_qa | DONE | 用户Photo2与规则要求 | 语义与边界冻结 |
| OSR-B01 | domain_execution | high | yes | root | overview_backend | overview_qa | DONE | OSR-P01 | 28测试及规则边界修复 |
| OSR-F01 | domain_execution | medium | no | root | v6_chart_race_fix | overview_qa | DONE | OSR-P01,B01 | 同页结构/规则/展开/筛选 |
| OSR-Q01 | independent_review | high | no | root | overview_qa | final_reviewer | DONE | OSR-B01,F01 | PASS WITH FINDINGS |
| OSR-G01 | independent_review | high | no | root | v6_final_gate | root | DONE | OSR-Q01 | PASS WITH FINDINGS，Root批准本地结构与规则 |
| GH-D01 | domain_execution | medium | no | root | real_data_handoff | github_publication_qa | DONE | 用户指令 | 真实数据接入/mock退场指南 |
| GH-T01 | fast_execution | low | no | backend | clone_test_fix | github_publication_qa | DONE | 私有历史不分发 | 缺可选历史测试明确skip |
| GH-Q01 | independent_review | high | no | root | github_publication_qa | final_reviewer | DONE | GH-D01,T01 | PASS WITH FINDINGS |
| GH-G01 | independent_review | medium | no | root | v6_final_gate | root | IN_REVIEW | GH-Q01 | 私有仓库推送前门禁 |
