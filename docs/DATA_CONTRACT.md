# 数据契约 v1.0（2026-10-24 冻结）

2026-10-25扩展：独立`management_demo`系列使用`management_demo_v1`不可变版本payload，证据等级`SYNTHETIC_MANAGEMENT_DEMO`。包含快照manifest、库存事实、预计算KPI、目标及预测，完整定义见[V6重构契约](V6_RECONSTRUCTION_CONTRACT.md)。不将旧截图转录包装成V6实数，不改变旧系列内容。

Planner审议通过：Server-first单体、两个独立系列、六张核心表。保留schema_version的历史JSON避免拆成十余张重复转录表；正式明细则关系化。2026-10-24用户后续改为先用DuckDB；JSON/UUID采用SQLAlchemy通用类型，库特定能力由adapter管理，API契约不变。

## 持久化

- DatasetSeries：UUID id，唯一code，title，kind=`legacy|inventory_detail|management_demo`，current_version_id。
- SourceFile：UUID id，filename，sha256，evidence_level，metadata JSON，created_at。
- DatasetVersion：UUID id，series_id，label，schema_version，evidence_level，source_file_id，payload JSON，limitations JSON，created_at；提交后无修改接口。
- ImportBatch：UUID id，sha256，filename，payload JSON，validation JSON，status，committed_version_id，created_at；预览只进入此表。
- InventorySnapshot：UUID id，version_id，label，exact_date，ordinal。
- InventoryItem：UUID id，snapshot_id，record_key，material_code，material_description，pdt，customer，project，material_category，subinventory_code，quantity NUMERIC，unit_cost NUMERIC，total_cost_amount NUMERIC。唯一snapshot_id+record_key。演示时pdt字段代表已知的组织/PDT维度，DEMO值不表示真实组织代码。

使用唯一约束和适用的FK，数据库不支持的循环/更新约束必须由事务服务验证并在迁移中注明；金额用Decimal/Numeric；API金额、比例、数量用十进制字符串。来源JSON中的数值保持原结构，读取时Decimal转换，原始舍入事实不伪装为额外精度。DuckDB只运行一个后端写进程，进程内事务写锁；PG切换时使用数据库事务/锁语义，需实测并发。

## 历史系列 legacy-transcription

来源为V4的reviewed_data.json逐字节复制并记录SHA256；保持 `periods,scopes,metrics,trend,aging,mwd,checks,reconciliations,sources,metadata` 键及原语义。版本schema_version=`legacy_v4_1`，evidence_level=`SOURCE_TRANSCRIPTION_DRAFT`。实际数据56条月趋势、36组库龄、8条MWD汇总、35条可见明细、18项核对。year=null；月份1–8月、库龄0829、MWD未确认日期独立。

`inventory/average_inventory/ship_cost/turnover` 是四KPI键；`old/old_share`额外保留。MWD的 `inventory` 是清单对应总库存，`stock`才是MWD库存；`po,total,provision`分别为MWD PO、来源合计、计提。不得漏掉stock或把inventory当MWD库存。源refs如`趋势数据:103`指向sources字典。

## 合成明细 canonical_json_v1

```json
{
  "schema_version": "1.0",
  "domain": "inventory_detail",
  "series": {"code": "synthetic-inventory", "title": "合成库存明细"},
  "evidence_level": "SYNTHETIC_DEMO",
  "version_label": "四时点演示",
  "snapshots": [
    {"key":"demo-2026-01-01", "label":"2026-01-01", "exact_date":"2026-01-01", "ordinal":1}
  ],
  "records": [
    {"snapshot_key":"demo-2026-01-01", "record_key":"DEMO-001-01", "material_code":"DEMO-M001", "material_description":"演示物料001", "pdt":"DEMO-PDT-A", "customer":"DEMO-客户01", "project":"DEMO-项目01", "material_category":"原材料", "subinventory_code":"DEMO-WH01", "quantity":"100.00", "unit_cost":"25.00", "total_cost_amount":"2500.00"}
  ]
}
```

演示金额单位是“演示元”，与历史的“亿（来源单位，币种未确认）”不混用。四时点使用2026-01-01、06-30、09-01、09-09，均为合成标签。缺金额用null并报告unknown_count；不能以0表示缺数。不生成周转、发货成本、MWD或风险等级。聚合含缺数时报告覆盖情况，不冒充完整总额；分页只限制明细展示，汇总按全量授权筛选结果。

文件最大5MiB、最多10000条明细、最多32个快照；未知schema、重复key、孤儿snapshot引用、非法日期、负/非有限金额、不符类型和数量×单价不一致拒绝提交。所有正式记录在一个事务生成；同import_id重试返回原版本；同文件SHA256重复导入报告并复用原版本，不产生副本。可导入标识仅SYNTHETIC_DEMO，ERP_EXPORT/BUSINESS_APPROVED待正式映射后开放。

## 授权边界

ActorContext/AccessPolicy由服务端创建；开发默认所有范围，允许环境配置限制历史scope和明细pdt；聚合和明细、来源均执行同一策略。浏览器自定义头不能扩大权限。APP_ENV=production且未配置正式身份提供方时拒绝启动。未来接SSO替换身份提供者，不改业务聚合。
