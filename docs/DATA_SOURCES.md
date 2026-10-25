# 数据来源与样例校验

本页记录 2026-10-24 本地实际读取结果。两类数据不可合并、互相对账或构成上下级血缘。

## 1. 历史截图转录初稿

源文件：`../isolated_versions/inventory_v4_real_20260913/data/reviewed_data.json`。
本项目副本：`data/private/legacy-reviewed.json`，受 `.gitignore` 保护，不应提交真实资料。

副本逐字节复制，两个 JSON 文件 SHA256 相同：

```text
914ba7517aa89e695ee7bdcb794177b5a10dd30b5dc9b02c003fd3a056c695eb
```

原始来源工作簿为 `../outputs/01a07a11-32be-7dc2-8130-b6254512ec90/远途库存_原始资料拼接与核对初稿.xlsx`。本轮重新计算工作簿 SHA256，与 JSON 的 `metadata.source_sha256` 一致：

```text
2afbe9b3cdd20fbb203a28881370d30d8744f3f62ab7eb6f992eb9675bca832f
```

来源链：原始截图 → 旧版转录工作簿 → 旧版适配JSON → 本项目逐字节副本 → 独立DuckDB版本（按本轮最新决定）。以上哈希证明复制和文件一致性，不代表截图转录已业务验收，也不证明约58万行ERP底表存在于本机。

| 内容 | 实际数量 |
| --- | ---: |
| `trend` 月度范围记录 | 56 |
| `aging` 库龄组 | 36 |
| `mwd.summary` 来源汇总范围 | 8 |
| `mwd.details` 来源可见明细 | 35 |
| `checks` 核对事项 | 18 |
| `topics` 专题原始记录 | 425 |
| `sources` 原行/单元格来源引用 | 2142 |

### 必须保留的事实边界

- 原文件证据等级为 `SOURCE_SCREENSHOT_TRANSCRIPTION_DRAFT`；V7展示等级映射为 `SOURCE_TRANSCRIPTION_DRAFT`，保留原 metadata。
- `year=null`；1月至8月不是已确认年份的日期。库龄仅0829，0831总览、MWD不能并成同一快照。
- 所有缺失值保留null，源比例不因金额舍入重算；周转和平均库存沿用来源，不重推五点/天数字典。
- `inventory` 在MWD中为清单对应库存，`stock`为MWD库存，`po/total/provision`独立。8个范围有父子重叠，不能相加。
- 业务线与BG差额不补“其他”；可见MWD条目不代表全库存客户/项目/物料明细。
- `reviewed`是历史适配文件名，不表示原始资料经业务签字。18条核对事项仍保留原状态。

## 2. 独立合成库存明细

`data/synthetic-inventory.json` 完全由 `data/generate_synthetic.py` 确定性生成，`series.code=synthetic-inventory`，证据等级 `SYNTHETIC_DEMO`。四日期仅为合成快照标签，字段来自已确认库存维度，内容使用DEMO编码。金额单位“演示元”，不与历史“亿”混用。

| 合成时点 | 行数 | 已知金额小计（演示元） | 未知金额行 | 已知零金额行 |
| --- | ---: | ---: | ---: | ---: |
| 2026-01-01 | 60 | 3763516.50 | 0 | 0 |
| 2026-06-30 | 62 | 4177832.50 | 0 | 0 |
| 2026-09-01 | 62 | 4625443.25 | 0 | 1 |
| 2026-09-09 | 62 | 4970393.50 | 1 | 0 |

总计246条，每个时点内部 `record_key` 唯一。覆盖3个物料大类、3个演示PDT、6个客户、9个项目和4个子库存。不同快照存在新增和消失物料，以验证变化贡献；第三时点保留已知零金额，最终时点DEMO-M066的单价和总金额为null，用于检验未知值与0的区别。最终时点的小计不是完整总金额，界面必须展示覆盖提示。

对于三项数值均已知的每条记录，使用Python Decimal验证 `quantity × unit_cost = total_cost_amount`。无风险等级、库龄天数、责任人、周转或MWD字段。

SHA256、逐快照计数、金额与类别计数见 `data/synthetic-manifest.json`。当前合成JSON SHA256：

```text
77b683612dd7382dda4cdffe2dd999c04ab50daa9cc3a3c506b19b1cfa09e672
```

## 3. 导入验证样例

`data/import-example.json` 使用独立 `synthetic-upload-demo` 系列，包含2026-09-09的3条完整记录，金额小计56079.50演示元。用于模板下载、预览不写正式数据、提交幂等和版本持久化验证；不属于历史转录数据。

SHA256：`982f35571241ab77bfa5b6df109de046a3321ca51d5b55f66e7463c1701943ac`。

## 重建与复核

在项目根运行：

```powershell
python -X utf8 data/generate_synthetic.py
```

脚本仅重建合成JSON、导入示例和合成清单，不读取或修改历史资料，不写数据库。脚本内检查快照引用、唯一键、非负金额和金额乘积。两次运行的三个输出哈希应相同；数据库导入/接口验收由后端与QA另行记录。
