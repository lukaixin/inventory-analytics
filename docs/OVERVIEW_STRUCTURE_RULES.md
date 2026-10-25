# 总览库存结构与规则结论契约 v1

冻结日期：2026-10-25。适用于 `management_demo` 的“趋势总览”，上位契约为 `V6_RECONSTRUCTION_CONTRACT.md`、`DATA_CONTRACT.md` 和 `API_CONTRACT.md`。

## Decision

在现有 `GET /api/v1/management/overview` 上做向后兼容扩展。保留原参数，并新增可选参数：

```text
structure_metric=turnover_days|point_inventory
```

默认 `turnover_days`。原响应字段与 `cards[]` 不变，新增同一次请求返回的 `structure` 和 `conclusions`。页面在主趋势下依次直接展示“库存结构概况”和“重点结论与关注”；现有“查看明细分析”只能作为次级入口，不能继续代替这两个模块。

本契约只确认旧对话中的“结构化数据 + 确定性规则”方向。工作电脑最新版 V6 的规则正文不可取得，所以下列规则是 V7 本地候选规则，不声称是 V6 原规则逐项恢复。

## Rationale

- Photo 2 的阅读路径是同页查看集团/物料形态、比较业务线、展开月度趋势，再阅读有数值依据的结论。
- 周转是预计算不可加指标，库存金额是单快照可加构成；两者必须共用交互外壳但保留不同计算语义。
- 后端版本化规则可重复、可测试、可追溯；数据不完整时应停止排名，而不是由前端或 LLM 猜结论。
- 单请求保证 KPI、结构、结论共用版本、权限、范围和期间，也便于前端防止慢旧请求覆盖新筛选。

## Scope Impact

当前阶段包含：两种结构指标、四个物料形态选项、已授权业务线、截止分析期的实际历史、同源展开明细、最多 5 条规则结论、权限/空值/并列/部分覆盖语义，以及桌面和 390px 验收。

当前阶段不包含：修改不可变 payload、数据库迁移或 seed；项目级假下钻；数量规则；PO/MWD 混入；周转求和/平均/库存加权；任意风险阈值、“高/中/低”标签、原因推断、建议动作或 LLM 摘要。

## API Contract

### 请求

```http
GET /api/v1/management/overview
 ?version_id=<management_demo UUID>
 &scope_id=GROUP|<authorized business_line_id>
 &material_form=ALL|raw|semi_finished|finished
 &analysis_period=<actual period_key>
 &baseline_period=<actual period_key>
 &structure_metric=turnover_days|point_inventory
```

- 非法 `structure_metric` 返回 422，不回退。
- `structure_metric` 只改变 `structure`，不改变 `cards` 或规则人口。
- `material_form` 是结构业务线与历史的当前形态；`form_options` 仍返回 `ALL/raw/semi_finished/finished` 供对照和选择。
- `scope_id=GROUP` 返回全部已授权业务线；单业务线 scope 只返回该业务线。
- 金额结构和金额规则只能使用与请求 period 的 `exact_date` 精确匹配的快照，禁止最近值回填。

### 响应字段

```json
{
  "scope_id": "GROUP",
  "material_form": "ALL",
  "analysis_period": "2026-10-22",
  "baseline_period": "2026-09-30",
  "cards": [],
  "structure": {
    "metric_id": "turnover_days",
    "label": "库存周转",
    "unit": "天",
    "value_source": "PRECOMPUTED_METRIC_FACT",
    "aggregation_rule": "PRECOMPUTED_NON_ADDITIVE",
    "share_applicability": "not_applicable",
    "analysis": {"period_key": "2026-10-22", "exact_date": "2026-10-22"},
    "baseline": {"period_key": "2026-09-30", "exact_date": "2026-09-30"},
    "scope_summary": {
      "id": "GROUP", "label": "集团",
      "value": "60.9", "baseline": "54.7",
      "absolute_delta": "6.2", "relative_delta": "0.113345521023765996",
      "share": null, "share_status": "not_applicable",
      "coverage_state": "complete",
      "source_refs": ["synthetic:metric:turnover:group:2026-10-22"]
    },
    "form_options": [
      {
        "id": "ALL", "label": "全部", "selected": true,
        "value": "60.9", "baseline": "54.7",
        "absolute_delta": "6.2", "relative_delta": "0.113345521023765996",
        "share": null, "share_status": "not_applicable",
        "coverage_state": "complete", "source_refs": ["synthetic:metric:turnover:group:2026-10-22"]
      }
    ],
    "business_lines": [
      {
        "id": "DEMO-BL-A", "label": "演示业务线A",
        "value": "19.3", "baseline": "21.4",
        "absolute_delta": "-2.1", "relative_delta": "-0.098130841121495327",
        "share": null, "share_status": "not_applicable",
        "coverage_state": "complete",
        "source_refs": ["synthetic:metric:turnover:DEMO-BL-A:2026-10-22"],
        "history": [
          {
            "period_key": "2026-10-22", "label": "2026-10-22",
            "exact_date": "2026-10-22", "snapshot_alias": "CURRENT",
            "value": "19.3", "coverage_state": "complete",
            "source_refs": ["synthetic:metric:turnover:DEMO-BL-A:2026-10-22"]
          }
        ]
      }
    ],
    "reconciliation": null
  },
  "conclusions": {
    "ruleset_id": "management_overview_rules_v1",
    "max_items": 5,
    "items": [
      {
        "rule_id": "OVR_FORM_MAX_POSITIVE_INVENTORY_DELTA_V1",
        "rank": 1,
        "category": "inventory_change",
        "title": "原材料、半成品并列为库存增量贡献最高形态",
        "summary": "较基期均增加 3120 演示万元。",
        "condition": {
          "operator": "MAX_POSITIVE_ABSOLUTE_DELTA_WITH_TIES",
          "current_period": "2026-10-22", "baseline_period": "2026-09-30",
          "required_coverage": "complete"
        },
        "entities": [
          {"id": "raw", "label": "原材料"},
          {"id": "semi_finished", "label": "半成品"}
        ],
        "evidence": [
          {
            "metric_id": "point_inventory", "entity_id": "raw",
            "current": "12000", "baseline": "8880", "absolute_delta": "3120",
            "relative_delta": "0.351351351351351351", "unit": "演示万元",
            "scope_id": "GROUP", "material_form": "raw",
            "current_period": "2026-10-22", "baseline_period": "2026-09-30",
            "source_refs": ["synthetic:inventory:raw:current", "synthetic:inventory:raw:baseline"]
          }
        ],
        "drilldown": null
      }
    ]
  }
}
```

示例数字只说明字段关系，不是 Photo 2、V6 或当前 fixture 的验收常量。金额、天数、比例均以十进制字符串传输；未知是 `null`，已知零是 `"0"`。`source_refs` 必须完整覆盖该数值的授权输入事实并稳定去重，不能包含未授权业务线。

### 通用数值语义

- `scope_summary` 表示当前 `scope_id + material_form`；`form_options` 固定顺序为 `ALL, raw, semi_finished, finished`，是对照项，不代表可以相加。
- `absolute_delta=value-baseline`，仅当前与基期都存在且覆盖完整时返回。
- `relative_delta=absolute_delta/baseline`，仅在上述条件且 `baseline>0` 时返回。基期为 0 时保留绝对差、比例为 null，不能显示无穷或“增长 100%”。
- `coverage_state=complete|partial|unavailable`。数值行的该字段是**当前与基期比较人口的最差状态**：任一期 partial 则至少为 partial，任一期 unavailable 则为 unavailable；不能因当前值完整就把基期 partial 的比较标为 complete。当前期 `value` 在 partial 时仍可显示“已知金额小计”，但 `absolute_delta/relative_delta/share` 及排名结论按规则返回 null 或被抑制。存在 baseline 时，`source_refs` 同时覆盖当前与基期的授权输入事实。
- 请求中的日期、scope 或 form 存在但没有匹配 fact，默认是 `unavailable`，不是已知 0。只有存在明确的零值 fact，或版本/人口元数据明确证明该精确人口“完整且为空”时，才可返回已知零。不得用空数组、过滤后无行或缺字段推断 0。
- `share_status=available|partial|zero_denominator|unavailable|not_applicable`。分子已知为 0、分母大于 0 时 share 为 `"0"`；分母为 0 时 share 为 null。

### 周转结构

- 只读取完全匹配 `metric_id=turnover_days + observation_type=actual + period_key + scope_id + material_form` 的预计算 fact。
- 集团、形态、业务线及各历史点分别读取自己的 fact；不得求和、平均或按库存金额加权。
- `unit=天`、`value_source=PRECOMPUTED_METRIC_FACT`、`aggregation_rule=PRECOMPUTED_NON_ADDITIVE`。
- 周转 share 没有定义，固定 `share=null, share_status=not_applicable`。缺 fact 时 unavailable，不从集团、ALL 或邻期回填。

### 时点库存结构

- 使用 AccessPolicy 过滤后的 `inventory_facts`，按精确快照、范围、物料形态服务端聚合。
- `unit=unit_policy.detail_amount`、`value_source=AUTHORIZED_INVENTORY_FACTS`、`aggregation_rule=ADDITIVE_WITHIN_ONE_SNAPSHOT`。
- 完整人口下 scope 总额应分别与业务线之和、三形态之和勾稽；前端不得再次合计父子。
- share 只在对应分子、分母都完整且分母大于 0 时返回；三类位置使用不同且固定的分母：
  - `scope_summary.share`：当前 `scope_id + selected material_form` ÷ 当前 `scope_id + ALL`。因此选择 finished 时表示该范围内成品占全部形态的比例；选择 ALL 且人口完整、分母大于 0 时为 1。
  - `form_options[i].share`：当前 `scope_id + 该形态` ÷ 当前 `scope_id + ALL`。raw、semi_finished、finished 在完整互斥人口下合计为 1；ALL 项自身为 1。
  - `business_lines[i].share`：该业务线 + 当前 selected material form ÷ 当前 `scope_id` 下全部已返回业务线 + 当前 selected material form。`scope_id=GROUP, material_form=finished` 时，各业务线表示“占当前范围全部成品”，完整人口下合计为 1；单业务线 scope 只返回该行，完整且非零时为 1。
- 上述两组占比不能交叉勾稽：形态卡比较同一 scope 内的形态构成，业务线行比较 selected form 在当前 scope 内的业务线构成。UI 统一使用“占当前范围”或更明确的动态标签，不得把业务线 share 固定标成“集团占比”。
- `reconciliation` 必须包含 `detail_value, detail_unit, conversion_factor, converted_value, overview_fact_value, overview_unit, gap, status, source_refs`；`status=matched|mismatch|partial|unavailable`。换算因子必须来自服务端明确单位规则，缺失时不猜换算。勾稽差不能被静默抹平，也不能反向覆盖明细结构或 KPI fact。

### 历史与展开

- `history[]` 只含同 metric、scope、form 的 actual 点，且 `exact_date<=analysis.exact_date`，按日期升序。
- 周转历史来自预计算 facts；库存历史来自相同授权人口的精确快照。不得插值、补 0、复制上一值或混源。
- `snapshot_alias` 仅在精确命中 manifest 四锚点时返回，否则 null。
- 缩略图和展开表使用同一数组。少于两个已知值时显示“趋势数据不足”，展开仍列已有点；展开不请求或生成项目数据。

## Deterministic Rules

共通要求：`ruleset_id=management_overview_rules_v1`；语义改变必须升版本。规则只在后端执行，不调用 LLM，不由前端重算。先授权再聚合和排名。`items` 最多 5 条、无最低条数；无触发时返回空数组，UI 只能说“未触发已配置规则”，不能说“库存健康/无风险”。每条必须含 `rule_id, rank, category, title, summary, condition, entities, evidence, drilldown`，并给出数值、单位、期间、范围、形态及来源。不得返回 severity 或高/中/低。

`evidence[]` 使用同一个稳定的可空字段超集，前端不得按自由文本反解析数值：

```json
{
  "metric_id": "point_inventory",
  "entity_id": "raw",
  "entity_label": "原材料",
  "current": "12000",
  "baseline": "8880",
  "absolute_delta": "3120",
  "relative_delta": "0.351351351351351351",
  "current_share": null,
  "baseline_share": null,
  "share_delta": null,
  "amount_direction": "up",
  "share_direction": null,
  "target": null,
  "target_period": null,
  "gap": null,
  "unit": "演示万元",
  "share_unit": "ratio",
  "scope_id": "GROUP",
  "material_form": "raw",
  "current_period": "2026-10-22",
  "baseline_period": "2026-09-30",
  "coverage_state": "complete",
  "source_refs": ["synthetic:inventory:raw:current", "synthetic:inventory:raw:baseline"]
}
```

不适用字段必须显式为 null：排名规则使用 current/baseline/delta；长库龄方向规则同时使用 amount delta、current/baseline share、share delta 与两个 direction；目标规则使用 current/target/gap/target_period；覆盖提示把**全部数值字段**设为 null，在 `condition.affected_rule_ids[]` 列出被抑制规则，并保留 `current_period/baseline_period/coverage_state/source_refs` 说明哪个精确人口缺失或不完整。缺失 fact 时来源引用指向可用的版本 manifest/人口证据，不伪造不存在的 fact 引用。`amount_direction/share_direction` 仅可为 `up|down|flat|null`。

`drilldown` 整体可为 null。只有当前 period 和基期 period **都能精确映射** manifest 的四个 alias、目标页支持同一授权范围，并且结论只对应一个可选择实体时，才返回 `{page:"management-analysis",query:{current_alias,baseline_alias,business_line_id,material_form}}`。规则 20/30 出现并列时必须返回 `drilldown:null`，因为 Analysis 只能选择单一实体；不能任取第一名作为跳转。任一期间不能精确映射时也必须返回 null，前端不显示规则具体跳转；不能省略 alias 后让 Analysis 使用默认 `CURRENT`。结论自身的 condition/evidence 展开仍可用。页面底部不带规则筛选的通用“查看明细分析”入口可以保留，但不能冒充该规则的同人口下钻。

| 优先级 | rule_id | 触发与抑制 |
| --- | --- | --- |
| 10 | `OVR_DATA_COVERAGE_INCOMPLETE_V1` | 任一后续规则所需当前/基期事实 partial 或 unavailable 时，合并为一条数据质量提示并返回 `affected_rule_ids`；抑制受影响业务规则。 |
| 20 | `OVR_FORM_MAX_POSITIVE_INVENTORY_DELTA_V1` | 当前 scope 下 raw/semi_finished/finished 三候选全部完整；取最大绝对库存增量且最大值严格大于 0。任一候选不完整或最大值 <=0 则不触发。 |
| 30 | `OVR_LINE_MAX_POSITIVE_INVENTORY_DELTA_V1` | 仅 GROUP 且至少两个已授权业务线候选；按当前 material form 取最大绝对库存增量且 >0。候选不完整、少于两个或单业务线 scope 不触发。 |
| 40 | `OVR_OVER180_AMOUNT_SHARE_DIRECTION_V1` | 当前 scope + form 的 >180 金额 delta 与 share delta 都可完整计算，且至少一项非 0 时触发；返回两个方向字段，不使用任意幅度阈值。 |
| 50 | `OVR_TURNOVER_ABOVE_TARGET_V1` | 沿用 overview 的 exact reference 和完整维度匹配；turnover actual 覆盖完整、target exact matched 且非 null、`actual-target>0` 时触发。缺目标、维度不符、actual 不完整或 gap<=0 不触发。 |

规则 20 固定评估三种实体形态，不受当前 form 选中值裁掉；规则 30/40/50 使用当前 form。区别必须写入 condition 和 UI 范围标签。

### 并列、零值、partial 与长库龄方向

- 规则 20/30 用未舍入 Decimal 绝对增量判断；完全并列时返回一个 item，`entities/evidence` 包含全部并列项，标题写“并列最高”，且 `drilldown=null`；不能取数组第一项冒充唯一最大或单实体跳转。单一胜出者仅在两个期间均精确映射 alias 时可提供对应实体下钻。
- 排名不使用相对增幅。基期为 0 且覆盖完整时可按绝对增量参评，但 relative delta 为 null，summary 不生成百分比。当前和基期均为 0 不触发正增长；最大值为 0 或负数不输出“增长最大”。
- 任一候选 partial/unavailable 时，不能从剩余候选声称“全范围最高”；输出规则 10 并抑制该排名。
- 规则 40 返回 `amount_delta, amount_direction, share_delta, share_direction`。方向固定为 `up|down|flat`，按未舍入值与 0 比较；share 用同一完整人口的 `over_180_amount/inventory_amount`，两个分母都必须大于 0。
- 非持平的四个主组合均可形成中性事实结论：`up/up`、`up/down`、`down/up`、`down/down`。边界 flat 也按实际方向展示。`up/down` 必须明确写“占比下降，但 >180 天绝对金额仍增加，不能理解为绝对额改善”。不得从任何组合推断原因、风险等级或管理动作。
- 规则 50 只陈述“周转天数高于目标 X 天”，不增加容差阈值。现有 target schema 没有强制 `coverage_state`：完全维度匹配、`match_status=matched` 且 value 非 null 的 target 视为可用，除非来源显式提供 `coverage_state=partial|unavailable`；不得因 coverage 字段未提供而把所有目标判为不完整。

## Product Placement

页面顺序：全局筛选 → 四 KPI → 主趋势 → 库存结构概况 → 重点结论与关注 → 辅助入口/来源。

- 结构顶部显示范围、分析/基期日期、单位和两项指标选择；form options 展示文字选中态而非只靠颜色。
- 业务线行显示当前值、基期差；仅 point inventory 显示 share。其标签使用“占当前范围”：GROUP 下表示该行占所选形态的全部已授权业务线，单业务线 scope 下该行完整且非零时为 100%，不得固定写“集团占比”。缩略图有可访问文本，展开按钮有 `aria-expanded`，展开表显示日期、值、单位和覆盖状态。
- 结论按 rank 展示 0–5 条，并可查看 condition 与 evidence；数据质量项使用中性文案。仅 `drilldown` 非 null 时显示规则具体跳转；null 时仍可展开依据，不能跳到 Analysis 默认期间。
- 切换指标、范围、形态或期间时发出新的单一 overview 请求；前端必须 abort 或以 request token 忽略旧响应。失败/无权限时清除旧结构和结论。
- 390px 下纵向重排；展开表只在模块内部滚动，文档不能横向溢出。

## Acceptance Impact

旧的“四卡和趋势可用”不再足够。本轮增加结构数值源、不可加行为、库存勾稽、规则决策表、权限裁剪、并列/零/null/partial、异步竞态和同页真实渲染证据。不可变 payload 前后哈希一致是门禁。

## Downstream Tasks

1. Backend：同一 overview 服务新增结构、历史、勾稽及 ruleset，原 cards 行为不变。
2. Frontend：新增同页模块、选择、缩略图、月度展开、规则依据与请求竞态保护。
3. QA：独立复算结构、share、周转 fact、目标 gap 和规则，验证权限、并列、0/null/partial、1440/390。
4. Root：同步 API 文档、任务状态和证据；Final Reviewer 再作门禁。

## Task Breakdown

| Ticket | 输出 | 门禁 |
| --- | --- | --- |
| OSR-B01 | overview additive fields、规则、类型与测试 | 隔离 DuckDB；旧 overview 回归 |
| OSR-F01 | 同页结构与结论 UI | build；真实 API；快速切换 |
| OSR-Q01 | 独立数据与浏览器报告 | P0/P1 清零；payload hash 不变 |
| OSR-G01 | Final Gate 意见 | Root 作交付决定 |

## Agent Assignment

- Contract：Planner；Accountable/Integration：Root；API/规则：Backend Worker；页面/交互：Frontend Worker；独立回归：QA；门禁意见：Final Reviewer。
- 实现者不得用前端常量补后端结论，不得为触发规则修改 fixture，不得撤销其他代理或用户改动；语义冲突回 Planner。

## Risks

| 风险 | 控制 |
| --- | --- |
| 把候选规则冒称 V6 原规则 | 明示 V7 本地 candidates 和证据限制 |
| 周转错误合计/加权 | 只读完全匹配 precomputed fact；share 不适用 |
| 库存结构与 KPI 单位混淆 | detail unit + 显式换算勾稽，互不覆盖 |
| partial 产生虚假排名 | 可显示已知小计，抑制受影响排名并报数据质量 |
| 并列被写成唯一最大 | 未舍入 Decimal 判定，一个 item 返回全部并列实体 |
| 权限泄漏 | 授权先于聚合/排名/来源，受限实体完全不进入输出 |
| 稀疏历史伪连续 | 只返回 actual exact dates，不插值、不补 0 |
| 异步错位 | 单请求 + abort/request token；错误时清旧数据 |

## Acceptance Criteria

1. 新参数两值成功，非法值 422；旧请求默认成功，原 cards 字段和值不变。
2. turnover 只读完全匹配 facts，不相加/平均/加权，share 全部不适用。
3. point inventory 来自授权精确快照；完整人口下，三形态 share 以当前 scope 的 ALL 为分母并合计 1，业务线 share 以当前 scope + selected form 的全部返回业务线为分母并合计 1；单业务线 scope 的业务线行 share 为 1。两组分母不混用，并返回与 KPI fact 的显式 reconciliation。
4. GROUP 仅含已授权业务线；单业务线 scope 仅含该行；受限实体不出现在历史、结论、文案或来源。
5. history 只含截止分析日的实际提供点，四 manifest 锚点准确；缩略图与展开同源，不补月份。
6. 数值行 coverage 取当前/基期最差状态；complete 才比较，partial 当前值可显示已知小计但不参加排名；无 fact 默认 unavailable，只有明确零 fact 或完整空人口元数据才返回 0；基期 0 的 relative 为 null。
7. 形态/业务线正增量并列返回全部并列项且 drilldown 为 null；单一胜出者满足 alias 条件才可下钻；最大值 <=0 不写“增长最大”；数量不参与。
8. 长库龄规则返回金额与 share 的实际方向；up/down 明确不代表绝对额改善；不推断原因或风险。
9. turnover target 仅 exact match、非 null 且 gap>0 触发，不跨 scope/form/period 回填；target 未定义 coverage 字段时不因此判为不完整，显式 partial/unavailable 除外。
10. 结论最多 5 条、顺序稳定、无触发为空；每条有版本化 ID、条件和完整数值证据；无 LLM、无风险等级。仅当前/基期均精确映射 manifest alias 时返回规则 drilldown，否则为 null 且 UI 不显示具体跳转。
11. 页面在主趋势下真实显示两个模块；业务线可展开/收起；快速切换只保留末次请求。
12. 1440px 与 390px 无文档横向溢出，键盘可操作；后端测试、前端 build、真实 API、浏览器控制台证据齐全；payload 和旧版本 hash 不变。

## Rollback Plan

- 无迁移、无数据写入。回滚只移除 overview 新增参数/字段和前端两个模块，保留原四卡、趋势、分析页及次级入口。
- 结构/规则实现与原 cards 计算隔离；失败时回退调用，不改不可变 DatasetVersion。
- 回滚前后运行旧 overview 合同测试并核对 payload/source hash；不删除 DuckDB、版本、备份或休眠 PostgreSQL 资产。
