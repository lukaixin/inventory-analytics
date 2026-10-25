# V6 业务内容重构契约（本地可运行候选版）

- 冻结日期：2026-10-25（Asia/Shanghai）
- 适用阶段：V7 本地 DuckDB 功能重构
- 契约状态：可实施；真实 V6 文件缺失形成的业务未知项保持显式
- 证据边界：用户当前指令 > 《远图工作任务述说》中已恢复的内容 > 用户提供的四张页面照片 > 旧 V3/V4 资料

## Decision

本轮不再以 V4 的五页和历史转录数据定义产品范围。V7 的默认产品改为三个业务主页面：

1. **趋势总览**：实际、目标、预测、基期差的管理层视图；
2. **明细分析**：四个快照别名、业务线、物料形态联动的库存规模与长库龄分析；
3. **库存数据表**：业务线 → 项目 → 物料小类的分层库存表，支持库龄桶、排序、展开、筛选和导出。

现有的 V4 转录汇总、MWD 可见数据、数据版本、导入与来源核对继续保留，但放入**“来源与专题”辅助入口**，不再作为默认产品主流程。PO、AI 摘要、Risk Case、Owner/Deadline/Action 等未经本轮可靠证据确认的能力不进入当前实现。

真实 V6 文件无法从工作电脑取得，因此新主流程使用一个独立、持久化、不可变的 `management_demo` 数据系列验证产品能力。它必须在所有页面标注“合成管理演示”，不得使用 V4 数字或照片数字冒充 V6 真实业务数据。

## Rationale

- 四张照片和已恢复会话都指向同一核心：管理层先看 Actual/Target/Forecast，再按四个时间锚点、业务线和物料形态诊断，最后在分层数据表查到项目与物料。
- 当前实现以 V4 截图转录、单纯趋势和合成物料探索为中心，缺失目标匹配、预测、四锚点语义、长库龄联动和树形库存表，所以继续修饰原五页不能解决内容差距。
- 新系列与旧系列隔离，既能完成可运行的功能重构，又不会提高旧转录数据的证据等级或伪称已经实现 V6 数据等价。
- 复用 `DatasetSeries`、`DatasetVersion.payload`、来源文件和不可变版本机制，当前无需为合成候选版扩张大量数据库表；真实 ERP 接入时再根据数据量和查询证据将事实拆为关系表或分析 Mart。

## Scope Impact

### 当前范围

- 新增 `DatasetSeries.kind = management_demo`，既有 `legacy` 与 `inventory_detail` 不变。
- 新增 `management_demo_v1` 版本化 payload、服务端聚合和 `/api/v1/management/*` 只读接口。
- 新增一份确定性合成管理数据，覆盖趋势、目标、预测、四锚点、业务线、物料形态、项目、物料小类与库龄桶。
- 重排导航与默认页面，保留旧专题、版本和来源入口。
- 复用现有 DuckDB、Alembic、版本、来源、授权入口、启动/备份和未来 PostgreSQL 适配边界。

### 明确不在当前范围

- 不声明与工作电脑 V6 的数值或规则一致；
- 不接真实 ERP、Excel 自动清洗、正式 Target 文件或正式 Forecast；
- 不实现 PO 页面或把 PO/MWD 加入正式核心 KPI；
- 不实现 AI 判断、Risk Case、人工确认或行动闭环；
- 不确定正式货币、数量可加性、周转字典、风险阈值、企业 SSO 或生产部署；
- 不做 58 万行或 200 万行性能承诺。

## Content Truth 分级

| 分级 | 可展示内容 | UI 要求 |
| --- | --- | --- |
| `SYNTHETIC_MANAGEMENT_DEMO` | 本轮生成的趋势、目标、预测和明细 | 页面顶端持续显示“合成管理演示”；单位使用“演示亿元/演示万元”等明确演示单位 |
| `FUNCTIONAL_REFERENCE` | 照片体现的页面结构、筛选方式、实际/目标/预测关系、树形表交互 | 只能决定功能和布局，不能复制照片数字为事实 |
| `SOURCE_TRANSCRIPTION_DRAFT` | 既有 V4 转录、MWD 汇总和来源引用 | 只在辅助入口使用，继续显示“转录初稿”及原限制 |
| `BUSINESS_APPROVED` | 当前不存在 | 不得在 UI 或 API 声称存在 |

## 数据对象契约

`management_demo_v1` 保存在独立 `DatasetVersion.payload`。金额、数量、比例与天数仍以十进制字符串或 `null` 传输；未知不能转换为 0。

```json
{
  "schema_version": "management_demo_v1",
  "domain": "inventory_management",
  "evidence_level": "SYNTHETIC_MANAGEMENT_DEMO",
  "unit_policy": {
    "currency": "DEMO_CURRENCY",
    "inventory_amount": "演示亿元",
    "detail_amount": "演示万元"
  },
  "snapshot_manifest": {
    "YEAR_START": "demo-2025-12-31",
    "MID_YEAR": "demo-2026-05-31",
    "MONTH_START": "demo-2026-09-30",
    "CURRENT": "demo-2026-10-22"
  },
  "snapshots": [],
  "metric_catalog": [],
  "metric_facts": [],
  "targets": [],
  "forecasts": [],
  "inventory_facts": [],
  "risk_policies": [],
  "sources": {}
}
```

### SnapshotManifest

每个 `snapshots[]`：

- `key`：版本内稳定键；
- `exact_date`：真实 ISO 日期（合成版也必须是合法日期）；
- `label`：人类可读标签；
- `ordinal`：展示顺序；
- `role`：`YEAR_START | MID_YEAR | MONTH_START | CURRENT | HISTORY`。

查询只能通过 payload 内的 `snapshot_manifest` 解析别名。服务、前端和测试不得分别硬编码 CURRENT 日期。别名缺失时返回受控错误，不回退到“最新日期”。

合成版采用上述四个日期，是为了复现已恢复的 V6 Release `20261023_02` 快照语义与页面交互；日期可作为功能参考，随附的所有库存数值仍是合成数据。先前照片中的 `2026-10-15` 仅是旧页面截图时点，不再作为当前别名。

### MetricCatalog 与 MetricFact

管理总览的四个核心指标固定为：

| metric_id | 中文名 | aggregation_rule | 说明 |
| --- | --- | --- | --- |
| `turnover_days` | 库存周转 | `PRECOMPUTED_NON_ADDITIVE` | 只读预计算事实，不从明细金额重算，不跨业务线相加 |
| `average_inventory` | 平均库存 | `PRECOMPUTED_NON_ADDITIVE` | 只读预计算事实，不把几个快照简单平均 |
| `point_inventory` | 时点库存 | `PRECOMPUTED_RECONCILABLE` | 管理事实；可与同版本明细合计显示勾稽差，但不能静默替换 |
| `shipment_cost` | 发货成本 | `PRECOMPUTED_NON_ADDITIVE` | 只读预计算事实，不从库存明细推导 |

每个 `metric_facts[]` 至少包含：

- `metric_id`、`period_key`、`period_label`、`period_order`；
- `value`、`unit`、`observation_type = actual`；
- `scope_id`（集团用 `GROUP`）；
- `material_form`（无该维度时为 `ALL`）；
- `reference_target_period_key`、`reference_forecast_period_key`：当前事实要对照的目标/预测期间，可为 null；
- `source_ref`、`coverage_state = complete | partial | unavailable`。

金额单位边界固定为：overview 的预计算货币 metric fact 使用“演示亿元”；`inventory_facts.inventory_amount` 使用“演示万元”。analysis 与 inventory-table 均直接聚合授权后的明细金额，因此返回“演示万元”，不得只改标签而不换算。需要与 overview 的 `point_inventory` 做勾稽时由服务端显式换算，例如 `49788 演示万元 = 4.9788 演示亿元`，并继续保留管理事实与明细聚合的差异信息。

### Target 与 Forecast 的精确匹配

每个目标或预测必须带完整匹配键：

`metric_id + period_key + scope_id + material_form`

- `targets[]` 还包含 `target_kind = period_end | quarterly`；
- `forecasts[]` 包含 `forecast_as_of`、`forecast_method = supplied_demo`；
- overview 先从选中的 actual fact 读取 `reference_target_period_key` 与 `reference_forecast_period_key`，再用完整匹配键查找目标/预测；
- 只允许**完全相同维度**匹配；禁止从集团目标回填业务线、从 ALL 物料形态回填单一形态，或拿相邻期间填补；
- 引用期间为空、引用期间不存在或完整维度不匹配时均返回 `match_status:"missing"`；禁止按“最近季度”“同月”或数组最后一项猜测；
- 没有匹配值时返回 `value:null, match_status:"missing"`，UI 显示“未提供”；
- 基期为 0 或 null 时相对变化为 null，UI 显示“—”；
- 目标差与预测差是服务端 Decimal 计算的派生展示值，并返回公式说明。

### InventoryFact

每条 `inventory_facts[]` 是一个快照下的末级演示事实，至少包含：

- 标识：`snapshot_key`、`record_key`；
- 业务维度：`business_line_id/name`、`project_id/name`、`material_subclass_id/name`；
- 物料维度：`material_code`、`material_description`、`material_form = raw | semi_finished | finished`；
- 库龄：`aging_bucket = D0_7 | D8_14 | D15_30 | D31_60 | D61_90 | D91_180 | D181_PLUS | UNKNOWN`；
- 数值：`inventory_amount`、`quantity`、`quantity_unit`；
- 完整性：`amount_known`、`quantity_additive`、`source_ref`。

业务线、项目和物料小类是同一层级树的三个层级；`record_key` 只标识演示事实，不被解释为未来 Risk Case 主键。

### 加总、空值和覆盖规则

1. `inventory_amount` 只在 `amount_known=true` 的同快照授权集合内求和；存在未知金额时返回 `unknown_amount_count` 和 `coverage_state=partial`，标题显示“已知金额小计”。
2. `quantity` 只有在全部记录 `quantity_additive=true` 且 `quantity_unit` 相同时才聚合；否则聚合数量返回 null，并说明“单位或可加性不一致”。
3. 周转、平均库存、发货成本不从 `inventory_facts` 重算。
4. 父节点等于其授权子节点的服务端聚合；前端不得再次合计父子行。
5. 零是已知零，必须显示 0；`null` 是未知，显示“暂无数据”。

### 长库龄与风险规则

必须同时保留两个不同概念：

- `over_180_amount`：`D181_PLUS` 的已知金额合计，是跨物料形态一致的长库龄观察指标；
- `policy_risk_amount`：按当前版本 `risk_policies[]` 判断的规则命中金额。

两者不得互换或相加。合成版只允许配置已从照片看见的功能示例：

```json
{
  "material_form": "finished",
  "threshold_days": 60,
  "comparison": "GT",
  "classification": "DEMO_RULE_CONFIG",
  "label": "成品 >60天（演示规则）"
}
```

`raw` 与 `semi_finished` 的阈值本轮设为 `null`，显示“规则待确认”，不得猜测。若一个库龄桶跨越阈值且无法从末级事实精确判断，`policy_risk_amount` 返回 null、`risk_evaluation=unclassified`，不能按整桶金额强行归类。`over_180_amount` 仍可独立计算。

## API 契约

所有接口沿用 `{data, meta}` 与统一错误结构，必须验证 `version_id` 属于 `management_demo`，并通过同一个 `ActorContext / AccessPolicy` 限制业务线、明细和导出。客户端请求头不能扩大范围。

### 1. `GET /api/v1/management/catalog`

参数：`version_id`。

返回：

- `metrics`、`periods`、`snapshot_aliases`；
- 授权后的 `business_lines`、`material_forms`；
- `risk_policies`（含 classification）；
- `unit_policy`、`evidence_level`、`data_as_of`。

最小响应形状：

```json
{
  "metrics": [
    {
      "id": "turnover_days",
      "label": "库存周转",
      "unit": "天",
      "aggregation_rule": "PRECOMPUTED_NON_ADDITIVE"
    }
  ],
  "periods": [
    {
      "key": "2026-10-22",
      "label": "当前 2026-10-22",
      "order": 10,
      "period_type": "snapshot",
      "observation_type": "actual"
    },
    {
      "key": "2026-Q4",
      "label": "2026-Q4",
      "order": 14,
      "period_type": "quarter",
      "observation_type": "target"
    }
  ],
  "snapshot_aliases": [
    {
      "alias": "CURRENT",
      "snapshot_key": "demo-2026-10-22",
      "label": "当前",
      "exact_date": "2026-10-22",
      "ordinal": 4
    }
  ],
  "business_lines": [{"id": "DEMO-BL-A", "label": "演示业务线A"}],
  "material_forms": [
    {"id": "ALL", "label": "全部"},
    {"id": "finished", "label": "成品"}
  ],
  "risk_policies": [
    {
      "material_form": "finished",
      "threshold_days": 60,
      "comparison": "GT",
      "classification": "DEMO_RULE_CONFIG",
      "label": "成品 >60天（演示规则）"
    }
  ],
  "unit_policy": {
    "currency": "DEMO_CURRENCY",
    "inventory_amount": "演示亿元",
    "detail_amount": "演示万元"
  },
  "data_as_of": "2026-10-22",
  "evidence_level": "SYNTHETIC_MANAGEMENT_DEMO"
}
```

### 2. `GET /api/v1/management/overview`

参数：

- 必填：`version_id`；
- 可选：`scope_id=GROUP`、`material_form=ALL`、`analysis_period`、`baseline_period`。

返回 `cards[]`，每个卡包含：

- `metric_id,label,unit,actual,baseline,absolute_delta,relative_delta`；
- `target:{value,period_key,match_status,gap}`；
- `forecast:{value,period_key,as_of,match_status,gap}`；
- `series:[{period_key,label,exact_date,period_type,source_order,order,value,observation_type}]`；
- `aggregation_rule,coverage_state,source_ref`。

目标/预测对象还必须返回 actual fact 使用的引用期间，便于前端解释为何当前点对照季度目标或其他期间：

```json
{
  "target": {
    "reference_period_key": "2026-Q4",
    "value": "52.0",
    "period_key": "2026-Q4",
    "match_status": "matched",
    "gap": "8.9"
  },
  "forecast": {
    "reference_period_key": "2026-Q4",
    "value": "57.7",
    "period_key": "2026-Q4",
    "as_of": "2026-10-22",
    "match_status": "matched",
    "gap": "3.2"
  },
  "series": [
    {
      "period_key": "2026-10",
      "label": "2026-10 预测",
      "exact_date": "2026-10-31",
      "period_type": "month",
      "source_order": 11,
      "order": 10,
      "value": "56.8",
      "observation_type": "forecast"
    }
  ]
}
```

如果 actual fact 的引用期间为 null，上述 `reference_period_key/period_key/value/gap` 均为 null，`match_status` 为 `missing`。

`series.exact_date` 是可定位到单日时的 ISO 日期，否则为 null；`period_type = snapshot | month | quarter | year`。`source_order` 保留版本 payload 内的原始顺序，公开字段 `order` 是服务端完成展示归并后的展示顺序，API 不另设其他展示顺序字段。overview 图的横轴必须使用 `exact_date` 的连续时间比例尺，`order` 只用于稳定数组顺序和同日项目的确定性顺序，不能把不同日期画成等距类别点。季度目标根据 `period_key` 解析真实自然季度起止，例如 `2026-Q4` 对应 `2026-10-01` 至 `2026-12-31`，在该真实时间区间展示目标线；不得用数组位置伪造季度跨度。若同一季度已经提供逐月 forecast，趋势 `series` 省略该季度的汇总 forecast 点以免重复；这只影响图表序列，卡片仍按 actual fact 的 `reference_forecast_period_key` 做精确期间匹配，不改用月度值或最近值。

趋势中的 actual、target、forecast 必须用不同字段和图例；不得把预测点连接成已发生实线。页面切换主指标时，下方大趋势显示该卡的完整系列；四张卡仍同时可见。

### 3. `GET /api/v1/management/analysis`

参数：

- `version_id`、`current_alias`、`baseline_alias`；
- 可选 `business_line_id`、`material_form`（默认 ALL）。

返回：

- 已解析的当前/基期快照键和日期；
- `inventory_amount`、`baseline_inventory_amount`、差值；
- `over_180_amount`、`over_180_share` 及各自基期差；
- `policy_risk_amount`、`risk_evaluation`；
- `turnover_facts[]`：由业务线 metric facts 提供的周转值和变化，缺失为 null；选中业务线时只返回该业务线，未筛选时返回全部授权业务线，始终排除 `scope_id=GROUP`；
- `amount_trend[]` 与 `over_180_trend[]`：按四别名顺序返回；
- `material_form_breakdown[]`、`business_line_breakdown[]`；
- `coverage`：当前/基期未知金额行数及完整性。

`summary`、`amount_trend`、`over_180_trend`、`material_form_breakdown` 与 `business_line_breakdown` 的金额都来自同一授权 `inventory_facts` 人口，单位固定为“演示万元”；它们不得复用 overview 的“演示亿元”标签或预计算管理指标值。

最小响应形状：

```json
{
  "selection": {
    "current_alias": "CURRENT",
    "current_snapshot_key": "demo-2026-10-22",
    "current_date": "2026-10-22",
    "baseline_alias": "YEAR_START",
    "baseline_snapshot_key": "demo-2025-12-31",
    "baseline_date": "2025-12-31",
    "business_line_id": null,
    "material_form": "ALL"
  },
  "summary": {
    "inventory_amount": "49788.00",
    "baseline_inventory_amount": "42100.00",
    "inventory_delta": "7688.00",
    "over_180_amount": "1981.56",
    "baseline_over_180_amount": "2210.25",
    "over_180_delta": "-228.69",
    "over_180_share": "0.0398",
    "baseline_over_180_share": "0.0525",
    "over_180_share_delta": "-0.0127",
    "policy_risk_amount": null,
    "risk_evaluation": "unclassified",
    "unit": "演示万元"
  },
  "turnover_facts": [
    {
      "business_line_id": "DEMO-BL-A",
      "business_line_label": "演示业务线A",
      "current": "31.7",
      "baseline": "32.0",
      "delta": "-0.3",
      "unit": "天",
      "coverage_state": "complete"
    }
  ],
  "amount_trend": [
    {
      "alias": "YEAR_START",
      "snapshot_key": "demo-2025-12-31",
      "exact_date": "2025-12-31",
      "value": "42100.00",
      "unit": "演示万元",
      "coverage_state": "complete"
    }
  ],
  "over_180_trend": [
    {
      "alias": "YEAR_START",
      "snapshot_key": "demo-2025-12-31",
      "exact_date": "2025-12-31",
      "amount": "2210.25",
      "share": "0.0525",
      "unit": "演示万元",
      "coverage_state": "complete"
    }
  ],
  "material_form_breakdown": [
    {
      "key": "finished",
      "label": "成品",
      "inventory_amount": "16360.34",
      "share": "0.3286",
      "over_180_amount": "830.00",
      "policy_risk_amount": "1940.00",
      "unit": "演示万元",
      "risk_evaluation": "evaluated"
    }
  ],
  "business_line_breakdown": [
    {
      "key": "DEMO-BL-A",
      "label": "演示业务线A",
      "inventory_amount": "16360.34",
      "share": "0.3286",
      "over_180_amount": "830.00",
      "unit": "演示万元",
      "coverage_state": "complete"
    }
  ],
  "coverage": {
    "current_unknown_amount_count": 0,
    "baseline_unknown_amount_count": 0,
    "current_state": "complete",
    "baseline_state": "complete"
  }
}
```

样例数字仅说明字段关系，不是照片或 V6 正式值；Data Worker 可以生成不同的确定性合成值，但必须满足同样的勾稽规则。

库存金额、>180 天金额和占比由同一授权集合计算；占比分母为已知库存金额。分母为 0 或存在影响完整性的未知金额时，比例按契约返回 null 或 `partial`，不能显示为完整结论。

### 4. `GET /api/v1/management/inventory-table`

参数：

- `version_id`、`snapshot_alias`；
- 可选 `business_line_id`、`material_form`、`risk_view=all | policy_hit | over_180 | unclassified`、`search`；
- `parent_key`：空值返回业务线层；业务线 key 返回项目层；项目 key 返回物料小类层；
- `sort_by = inventory_amount | over_180_amount | quantity | name`、`sort_dir`、`page`、`size`。

返回：

```json
{
  "resolved_snapshot": {},
  "totals": {
    "aging_amounts": {
      "D0_7": "28226.44",
      "D8_14": "7460.00",
      "D15_30": "9370.00",
      "D31_60": "1530.00",
      "D61_90": "720.00",
      "D91_180": "500.00",
      "D181_PLUS": "1981.56",
      "UNKNOWN": "0"
    },
    "aging_quantities": {
      "D0_7": null,
      "D8_14": null,
      "D15_30": null,
      "D31_60": null,
      "D61_90": null,
      "D91_180": null,
      "D181_PLUS": null,
      "UNKNOWN": null
    },
    "inventory_amount": "49788.00",
    "quantity": null,
    "quantity_unit": null,
    "quantity_status": "non_additive",
    "over_180_amount": "1981.56",
    "policy_risk_amount": null,
    "risk_evaluation": "partially_evaluated",
    "unknown_amount_count": 0,
    "coverage_state": "complete",
    "unit": "演示万元"
  },
  "rows": [
    {
      "row_key": "...",
      "parent_key": null,
      "level": "business_line",
      "label": "演示业务线A",
      "has_children": true,
      "aging_amounts": {
        "D0_7": "...",
        "D8_14": "...",
        "D15_30": "...",
        "D31_60": "...",
        "D61_90": "...",
        "D91_180": "...",
        "D181_PLUS": "...",
        "UNKNOWN": "0"
      },
      "aging_quantities": {
        "D0_7": null,
        "D8_14": null,
        "D15_30": null,
        "D31_60": null,
        "D61_90": null,
        "D91_180": null,
        "D181_PLUS": null,
        "UNKNOWN": null
      },
      "inventory_amount": "...",
      "quantity": null,
      "quantity_unit": null,
      "quantity_status": "non_additive",
      "over_180_amount": "...",
      "policy_risk_amount": null,
      "risk_evaluation": "unclassified",
      "unknown_amount_count": 0,
      "coverage_state": "complete"
    }
  ],
  "total": 0,
  "page": 1,
  "size": 50
}
```

`totals` 与 `rows` 使用相同筛选和授权人口。`totals` 是当前完整人口总计，不因当前页分页而变化；根层所有授权 rows 跨全部分页合计应与 totals 勾稽。子层请求的 rows 只与对应父节点勾稽，不重新定义全局 totals。

金额/数量分布切换的字段规则固定如下：

- 金额视图读取 `aging_amounts`，数量视图读取 `aging_quantities`；两者必须使用完全相同的八个库龄桶 key，前端不得自行换桶或换算。
- 每个 `aging_quantities.<bucket>` 只在该桶内事实均可加且单位唯一时返回十进制字符串；混合单位、任一事实不可加或不可判定时，该桶返回 `null`，不能返回 `0`。
- `quantity`、`quantity_unit`、`quantity_status` 同时出现在 `totals` 页脚和每个聚合 row；页脚描述完整筛选人口，不随当前分页变化。
- `quantity_unit` 仅在完整聚合人口单位唯一且可加时返回单位，否则为 `null`；`quantity_status = complete | partial | mixed_unit | non_additive | unavailable`，且状态必须解释数量为何可用或为空。
- 数量视图可以同时包含有效桶和 `null` 桶；出现任一 `null` 桶时总数量不得伪造，`quantity` 返回 `null`，`quantity_status` 返回对应的不完整原因。

授权、快照、搜索和风险筛选先在服务端限定事实人口；随后按请求层级聚合，再按 `sort_by/sort_dir` 对同一父节点下的聚合 sibling rows 排序，最后分页。默认排序为 `inventory_amount desc`。展开请求必须保留当前筛选；前端不能用初始全量结果本地伪造子层级。

### 5. `GET /api/v1/management/export`

与库存表使用同一筛选（不带 `parent_key/page/size`），导出授权后的末级演示事实或明确的当前聚合层；本轮默认导出末级事实。CSV 必须包含数据版本、快照别名与精确日期、演示标识、当前筛选和 UTF-8 BOM，并继续防公式注入。

### 6. 来源与版本

继续使用现有 `/sources`、`/evidence`、`/datasets/{id}/versions`。若一个合成值没有逐格来源，`source_ref` 指向合成生成清单及规则说明，不伪造工作表、单元格或业务文件。

## 产品与交互契约

### 主导航

`趋势总览 | 明细分析 | 库存数据表 | 来源与专题`

“来源与专题”内部包含：历史转录、MWD、数据版本与来源、合成导入。旧能力不删除，但不会把历史 aggregate 与 management demo 明细无提示混合。

### 趋势总览

- 首屏展示四 KPI；每张卡包含实际、基期变化、精确匹配的目标/预测状态。
- 选中卡后，下方主趋势同时显示实际、目标和预测；图例写清 Actual/Target/Forecast。
- 顶部筛选只放全页有效的期间、基期、范围和物料形态；单选值不能伪装为多选。
- 目标缺失显示“未提供”，预测缺失显示“未提供”，不隐藏空行制造完成感。

### 明细分析

- 当前/基期先选快照别名；UI 同时显示别名与精确日期。
- 业务线和物料形态筛选作用于金额、>180、规则风险、趋势和构成的同一人口。
- 总览行优先显示库存金额、>180 金额、>180 占比、规则风险金额；后者未知时明确显示“规则待确认/无法分类”。
- 业务线周转以预计算事实列表或小趋势呈现，不允许求和或按库存金额加权猜测集团周转。

### 库存数据表

- 默认展示业务线，逐层展开项目和物料小类；展开状态是 UI 状态，不改变统计人口。
- 桶列使用固定语义和顺序；未知桶与 0 分开。
- “风险范围”同时提供“>180 天”和“规则命中”，标签清楚区分；未配置规则的物料形态进入“未分类”。
- 宽表只在表格内部横向滚动；首列与汇总行可黏性展示，但不能遮盖数值。

### 可访问性和窄屏

- 所有筛选有 label，树形展开按钮提供 `aria-expanded`；
- 颜色不能作为 Actual/Target/Forecast 或风险的唯一编码；
- 390px 下 KPI 与图表纵向排列，库存表内部滚动，文档本身不产生横向滚动；
- 加载、空人口、部分覆盖、无权限和服务错误必须有不同状态。

## Acceptance Impact

旧的“V4 五页可打开”验收不再足以判定当前目标完成。当前阶段必须增加以下证据：

- 新 management_demo 版本真正写入 DuckDB，重启后仍存在；
- 四个别名都由版本 manifest 解析，测试更换 CURRENT 映射无需改服务代码；
- overview 对目标/预测执行精确维度匹配，并覆盖缺失、基期 0/null；
- analysis 的金额、>180 金额、占比和筛选人口一致；
- inventory-table 的三个层级逐层展开，父子勾稽、风险概念分离、服务端排序分页导出一致；
- management 接口经过 AccessPolicy，受限业务线不会出现在 KPI、趋势、树表、来源和导出；
- 主三页桌面与 390px 浏览器旅程通过，控制台无未捕获错误；
- 旧历史、MWD、版本及导入仍能从辅助入口访问；
- 数据证据等级始终为 `SYNTHETIC_MANAGEMENT_DEMO`，不得出现“V6 已验证”或“业务正式数据”。

## Downstream Tasks

1. Data Worker：生成确定性 `management_demo_v1` 源文件、生成清单与数值勾稽说明；
2. Backend Worker：新增 seed、management 服务/API、授权过滤、CSV 与契约测试；
3. Frontend Worker：重建主导航和三页，接真实 API，保留辅助入口；
4. QA：独立检查契约、数值、权限、错误/空态、桌面/窄屏、重启持久化；
5. Final Reviewer：仅在 QA 修复闭环后判定本地合成管理候选版是否可交付。

## Task Breakdown

| Ticket | 依赖 | 可并行 | 输出 | 门禁 |
| --- | --- | --- | --- | --- |
| V6-D01 合成管理数据 | 本契约 | 与后端骨架并行 | JSON + manifest + 勾稽报告 | schema 校验、确定性哈希 |
| V6-B01 API 与授权 | 本契约 | 是 | service/routes/types/tests | 隔离 DuckDB 测试 |
| V6-F01 三页重构 | API 类型冻结 | 可先用契约类型，集成时串行 | React/CSS/api types | build + 浏览器 |
| V6-I01 集成 | D01/B01/F01 | 否 | migration/seed/runtime | readiness + 重启 |
| V6-Q01 独立 QA | I01 | 否 | finding report | P0/P1 清零 |
| V6-G01 Final Gate | QA PASS | 否 | PASS/PASS WITH FINDINGS/BLOCKED/FAIL | root 交付决定 |

## Agent Assignment

- accountable_owner：Root / Orchestrator；
- contract_owner：Planner；
- data_generation：Data Worker；
- API、聚合、授权、导出：Backend Worker；
- 三页与辅助入口：Frontend Worker；
- 回归与 UX：QA（不得由实现者自审替代）；
- delivery verdict：Final Reviewer，最终交付决定仍由 Root 作出。

实现者不得通过前端常量补齐服务端缺失字段，也不得修改本契约中的证据等级、指标可加性、目标匹配或风险语义。语义冲突返回 Planner。

## Risks

| 风险 | 处理 |
| --- | --- |
| 用户工作电脑上的 V6 规则无法取得 | 本轮只承诺“按恢复上下文重构的合成候选版”；把未知项留在 UI/契约 |
| 合成数值看起来像真实经营数据 | 使用独立 dataset、演示单位、页面持续标签和来源限制 |
| 照片的风险阈值被过度推断 | 只配置成品 >60 天演示规则；其余未分类；>180 单独显示 |
| 周转/平均库存被错误重算 | 只消费 precomputed facts；禁止从四点或业务线相加 |
| 树形表重复合计 | 服务端按 parent_key 聚合，前端不合计父子 |
| DuckDB JSON 聚合性能不足 | 合成版数据有界；真实规模接入前用 EXPLAIN/压测决定关系表和 Mart，不预建几十张表 |
| 旧页面与新系列混域 | 主流程固定 management_demo；辅助入口显式切系列且保留数据类型标签 |
| 权限漏到导出/汇总 | 同一 AccessPolicy 先过滤事实人口，再聚合、来源和导出 |

## Acceptance Criteria

1. 默认打开趋势总览，四 KPI、主趋势、Actual/Target/Forecast 和演示标签完整；
2. 更改分析期、基期、范围或物料形态后，四卡与主趋势来自同一 API 返回人口；
3. Target/Forecast 缺失不会跨范围回填；基期 0/null 不产生无穷或伪百分比；
4. 明细分析能在四个 manifest 别名之间比较，显示精确日期、库存、>180、占比与规则风险状态；
5. 业务线/物料形态筛选同步更新所有分析组件；
6. 库存表可从业务线展开到项目再到物料小类，桶、金额、数量、长库龄和规则风险口径符合契约；
7. 数量不可加时返回 null；未知金额不变 0；父子层不重复加总；
8. 排序、分页、风险筛选和 CSV 与屏幕人口一致；
9. 受限业务线在所有 management 端点均不可见；
10. DuckDB 重启后 management_demo 版本和查询结果不变；
11. 现有 legacy、MWD、版本/来源和导入入口仍可用；
12. 后端测试、前端构建、真实浏览器桌面/390px 与无控制台错误全部有证据；
13. 所有用户可见位置均不声称真实 V6 数据或业务验收完成。

## Rollback Plan

- 实施前保留当前 `frontend/src`、`backend/app`、迁移、docs 与 DuckDB 备份；
- 新功能使用独立 `management_demo` series 和新增路由，不修改既有 legacy/inventory_detail 版本内容；
- 若新主流程阻断，可回退前端导航到当前已验收五页，同时保留但不选择 management_demo；
- 若 seed/API 有缺陷，停用 management 路由和当前版本指针，不删除不可变 DatasetVersion；修复后生成新版本，禁止原地改已提交 payload；
- 数据库变更若不可避免，先在隔离 DuckDB 迁移并验证备份恢复；不得自动删除开发库、旧版本或休眠 PostgreSQL 资产。

## 待真实 V6/业务确认

- 正式快照日期与快照别名定义；
- 正式币种、金额单位和数量单位；
- 集团、业务线、物料形态的正式编码和 Target 匹配维度；
- 周转与平均库存的正式字典、五点平均规则和目标/预测来源；
- 原材料与半成品的风险阈值，以及成品 >60 天规则是否仍有效；
- 物料级重复字段、批次粒度、数量可加性和正式业务主键；
- PO、MWD、AI 摘要和 Action 闭环是否进入后续产品范围。
