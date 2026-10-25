# API契约 v1.0

2026-10-25扩展：新增`/management/catalog`、`overview`、`analysis`、`inventory-table`和`export`，完整字段及匹配/筛选语义见[V6重构契约](V6_RECONSTRUCTION_CONTRACT.md)。本文件原接口保留供来源与专题使用。

总览补齐扩展：`GET /management/overview` 增加可选 `structure_metric=turnover_days|point_inventory`，默认周转；响应保留原四卡并新增同人口 `structure` 与 `conclusions`。确定性规则、来源证据、份额分母和部分覆盖抑制规则见[库存结构与规则契约](OVERVIEW_STRUCTURE_RULES.md)。无数据迁移或payload变更。

基础路径`/api/v1`，服务端8170。成功`{"data":...,"meta":{"version_id":...,"evidence_level":...,"limitations":[]}}`；无版本的元数据接口meta可为空。错误`{"error":{"code":"...","message":"可读中文","details":{},"trace_id":"..."}}`。金额/数量字符串，未知null；page从1起，size默认20上限100。404无资源、422验证失败、403无授权、409冲突、503依赖不可用。

所有下列数据形状为data内部内容；ID为服务端UUID。GET所需version_id必须属于对应series kind；未知或跨域版本返回422/404，不自动混换。

| 接口 | 参数/响应 |
| --- | --- |
| GET /health/live（不带api前缀） | `{status:"ok"}` |
| GET /health/ready | 真实数据库SELECT 1及迁移表检查；失败503 |
| GET /datasets | 数组`[{id,code,title,kind,current_version_id}]` |
| GET /datasets/{id}/versions | 数组`[{id,label,evidence_level,schema_version,created_at,source_file_id,limitations}]` |
| GET /legacy/dashboard | version_id, scope可选；`{periods:[{id,label,order}],scopes:[],metrics:[{id,label,unit}],rows:[{scope,period,month_order,inventory,average_inventory,ship_cost,turnover,old,old_share,sources}],checks:[],reconciliations:[]}`。所有scope均被授权过滤。四KPI对比由相同scope/period的原值显示差值，不重推指标。 |
| GET /legacy/aging | version_id；`{records:[原aging记录]}`；buckets每项label/value/unit/source，总计与old_total分开；reconciliation_gap按来源total引用匹配原核对记录，缺失为null。 |
| GET /legacy/mwd | version_id；`{summary:[原记录],details:[原记录],note}`。原记录含scope,item,inventory,stock,po,total,provision,unit,note,sources。 |
| GET /sources | version_id；`{id,filename,sha256,evidence_level,metadata,limitations}`。不返回本机绝对路径/密钥。 |
| GET /evidence | version_id, ref；`{ref,sheet,row,image,original_cell,original_row,unit,raw_value,raw_text,note}` |
| GET /inventory/snapshots | version_id；数组`[{id,label,exact_date,ordinal,row_count}]` |
| GET /inventory/explore | version_id,snapshot_id,baseline_id（可选）,group_by=`material_category|pdt|customer|project|material_code`；共同筛选pdt/customer/project/material_category/search。返回`{current_total,baseline_total,delta,unit:"演示元",unknown_count,baseline_unknown_count,groups:[{key,current,baseline,delta,share}],trend:[{snapshot_id,label,total}],filters:{pdt:[],customer:[],project:[],material_category:[]}}`。baseline省略时baseline_total/delta为null；总数包含全量筛选，unknown_count>0提示已知金额小计。 |
| GET /inventory/items | version_id,snapshot_id,共同筛选,page,size；`{items:[{id,record_key,material_code,material_description,pdt,customer,project,material_category,subinventory_code,quantity,unit_cost,total_cost_amount}],total,page,size}` |
| GET /inventory/export | 同items筛选，无分页；CSV下载，授权同查询，UTF8 BOM，防公式注入 |
| GET /imports/template | canonical_json_v1合成JSON文件下载 |
| POST /imports/preview | multipart `file`；`{id,status:"preview"或"rejected",sha256,row_count,snapshot_count,errors:[],warnings:[],sample:[],existing_version_id:null或UUID}`；内容错误返回200+rejected，解析/大小错误422/413。预览不写正式表。 |
| GET /imports/{id} | 与预览相同及committed_version_id |
| POST /imports/{id}/commit | JSON`{set_current:false}`；`{version_id,series_id,already_committed:boolean}`。校验失败409；原子持久化，重复提交幂等，只有显式true切current。首个版本初始化current可例外。 |

身份预留：ActorContext由服务端配置创建，前端只显示“本地演示：全范围”或受限说明，不提供伪造用户选项。可在meta携带access_note。当前不提供更新/删除已提交版本的API。

OpenAPI以运行时`/docs`和`/openapi.json`为准，但不得默默偏离本契约。任何差异须在此记录并同步前端/测试。
