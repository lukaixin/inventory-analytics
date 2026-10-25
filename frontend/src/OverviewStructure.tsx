import type { ManagementAnalysisQuery, ManagementCatalog, OverviewConclusions, OverviewStructureData, StructureHistory, StructureMetric, StructureValue } from './api';

const number = (value:string|null|undefined) => value == null ? '暂无数据' : Number(value).toLocaleString('zh-CN',{maximumFractionDigits:4});
const delta = (value:string|null|undefined) => value == null ? '—' : `${Number(value)>0?'+':''}${number(value)}`;
const percent = (value:string|null|undefined) => value == null ? '—' : `${(Number(value)*100).toFixed(1)}%`;
const coverage = (value:string) => ({complete:'完整',partial:'部分覆盖',unavailable:'数据不可用'}[value] || value);
const rowCoverage = (row:StructureValue) => {
  if(row.current_coverage_state==='unavailable')return '当前数据不可用，差值暂不比较';
  if(row.current_coverage_state==='partial')return row.baseline_coverage_state==='partial'?'当前与基期部分覆盖，差值暂不比较':'当前部分覆盖，差值暂不比较';
  if(row.baseline_coverage_state==='partial')return '基期部分覆盖，差值暂不比较';
  if(row.baseline_coverage_state==='unavailable')return '基期数据不可用，差值暂不比较';
  return row.coverage_state==='complete'?'完整':row.coverage_state==='partial'?'当前或基期部分覆盖，差值暂不比较':'数据不可用，差值暂不比较';
};
const knownSubtotal = (row:StructureValue, amount:boolean) => amount && row.current_coverage_state==='partial';
const shareText = (row:StructureValue) => row.share_status==='available' ? percent(row.share) : ({not_applicable:'不适用',partial:'覆盖不完整',zero_denominator:'分母为零',unavailable:'暂无数据'}[row.share_status] || '—');
const ruleConditions:Record<string,string> = {
  OVR_DATA_COVERAGE_INCOMPLETE_V1:'当前或基期所需数据覆盖不完整，停止受影响的比较与排名。',
  OVR_FORM_MAX_POSITIVE_INVENTORY_DELTA_V1:'比较三种物料形态的库存绝对增量，仅报告大于零的最大值；完全并列时保留全部形态。',
  OVR_LINE_MAX_POSITIVE_INVENTORY_DELTA_V1:'比较当前范围内业务线的库存绝对增量，仅报告大于零的最大值；完全并列时保留全部业务线。',
  OVR_OVER180_AMOUNT_SHARE_DIRECTION_V1:'同时比较超过180天库存金额与占比的变化方向，至少一项发生变化时显示。',
  OVR_TURNOVER_ABOVE_TARGET_V1:'当前周转天数高于精确匹配期间、业务范围及物料形态的目标值。',
};
const operatorConditions:Record<string,string> = {
  REQUIRED_COVERAGE_COMPLETE:'检查当前与基期所需数据是否完整；不完整时停止受影响的业务比较。',
  MAX_POSITIVE_ABSOLUTE_DELTA_WITH_TIES:'仅比较完整数据的正向绝对增量，保留所有并列最高项。',
  OVER180_AMOUNT_AND_SHARE_DIRECTION:'同时比较超过180天金额与占比的实际变化方向。',
  ACTUAL_MINUS_EXACT_TARGET_GT_ZERO:'当前值与精确匹配目标的差额大于零。',
};


function Sources({ refs }: {refs:string[]}) {
  return <details className="overview-sources"><summary>来源引用（{refs.length}）</summary><ul>{refs.map((ref)=><li key={ref}><code>{ref}</code></li>)}</ul></details>;
}

function Sparkline({ history, unit }: {history:StructureHistory[];unit:string}) {
  const known=history.filter((point)=>point.value!==null && Number.isFinite(Number(point.value)));
  if(known.length<2)return <span className="overview-spark-empty">趋势数据不足</span>;
  const values=known.map((point)=>Number(point.value));const min=Math.min(...values),max=Math.max(...values),span=max-min||1;
  const dates=history.map((point)=>Date.parse(point.exact_date));const start=Math.min(...dates),end=Math.max(...dates);
  const x=(date:string)=>4+(Date.parse(date)-start)/(end-start||1)*132;
  const y=(value:string)=>34-(Number(value)-min)/span*28;
  let pen=false;const path=history.map((point)=>{if(point.value===null){pen=false;return '';}const command=pen?'L':'M';pen=true;return `${command}${x(point.exact_date)},${y(point.value)}`;}).join(' ');
  return <svg className="overview-spark" viewBox="0 0 140 40" role="img" aria-label={`实际历史，${known[0].exact_date} ${number(known[0].value)} 至 ${known.at(-1)!.exact_date} ${number(known.at(-1)!.value)} ${unit}；可展开查看全部日期和值`}><path d={path} fill="none" stroke="currentColor" strokeWidth="1.8"/><circle cx={x(known.at(-1)!.exact_date)} cy={y(known.at(-1)!.value!)} r="2.5" fill="currentColor"/></svg>;
}

export default function OverviewStructure({data, conclusions, catalog, metric, onMetric, onForm, onAnalysis}: {
  data:OverviewStructureData;conclusions:OverviewConclusions|undefined;catalog:ManagementCatalog;metric:StructureMetric;onMetric:(metric:StructureMetric)=>void;onForm:(form:string)=>void;onAnalysis:(selection?:Partial<Omit<ManagementAnalysisQuery,"version_id">>)=>void;
}) {
  const amount=data.metric_id==='point_inventory';
  const scopeName=(id:string)=>id==='GROUP'?'集团':catalog.business_lines.find((line)=>line.id===id)?.label || id;
  const formName=(id:string)=>catalog.material_forms.find((form)=>form.id===id)?.label || id;
  const metricName=(id:string)=>catalog.metrics.find((item)=>item.id===id)?.label || ({over_180_amount:'>180 天库存金额',over_180_share:'>180 天占比'}[id] || id);
  const selection=data.form_options.find((form)=>form.selected)?.label || '全部';
  return <>
    <section className="management-panel overview-structure" aria-labelledby="overview-structure-title">
      <div className="overview-structure-heading"><div><h3 id="overview-structure-title">库存结构概况</h3><p>{data.scope_summary.label} · {selection} · {data.analysis.exact_date} 较 {data.baseline.exact_date}</p></div><label>结构指标<select aria-label="结构指标" value={metric} onChange={(event)=>onMetric(event.target.value as StructureMetric)}><option value="turnover_days">库存周转</option><option value="point_inventory">时点库存金额</option></select></label></div>
      <div className="overview-scope-value"><span>当前范围{data.label}{knownSubtotal(data.scope_summary,amount)?' · 已知金额小计':''}</span><strong>{number(data.scope_summary.value)} <small>{data.unit}</small></strong><span>较基期 {delta(data.scope_summary.absolute_delta)} {data.unit}</span><span>{rowCoverage(data.scope_summary)}</span></div>
      <p className="overview-structure-note">{amount?'同一快照内的库存金额可比较构成；形态卡占比以全部形态金额为分母，业务线占比以所选范围及形态金额为分母。':'周转来自各范围的预计算事实，不相加、不平均、不按库存加权；占比不适用。'}</p>
      <div className="overview-form-options" aria-label="结构物料形态">{data.form_options.map((form)=><button key={form.id} className={form.selected?'selected':''} aria-pressed={form.selected} onClick={()=>onForm(form.id)}><span>{form.label}{form.selected&&<small>已选</small>}</span>{knownSubtotal(form,amount)&&<span>已知金额小计</span>}<strong>{number(form.value)} <small>{data.unit}</small></strong><span>较基期 {delta(form.absolute_delta)}</span>{amount&&<span>占全部形态 {shareText(form)}</span>}{form.coverage_state!=='complete'&&<span>{rowCoverage(form)}</span>}</button>)}</div>
      <div className="overview-lines-heading"><span>业务线</span><span>当前 / 较基期</span><span>{amount?'占当前形态 / 范围':'占比不适用'}</span><span>实际历史 · 展开查看</span></div>
      <div className="overview-business-lines">{data.business_lines.map((line)=><details className="overview-business-line" onToggle={(event)=>event.currentTarget.querySelector('summary')?.setAttribute('aria-expanded',String(event.currentTarget.open))} key={`${data.metric_id}-${line.id}-${data.analysis.period_key}-${data.baseline.period_key}-${selection}`}><summary aria-expanded="false"><span className="overview-line-name">{line.label}</span><span className="overview-line-value">{knownSubtotal(line,amount)&&<small>已知金额小计</small>}<strong>{number(line.value)} <small>{data.unit}</small></strong><small>较基期 {delta(line.absolute_delta)} {data.unit}</small>{line.coverage_state!=='complete'&&<small>{rowCoverage(line)}</small>}</span><span className="overview-line-share">{amount?shareText(line):'—'}</span><Sparkline history={line.history} unit={data.unit}/></summary><div className="overview-history"><p>截止 {data.analysis.exact_date} 的已提供实际记录；未提供月份不补值。</p><div className="overview-history-table"><table><thead><tr><th>日期</th><th>时点</th><th>{data.label}（{data.unit}）</th><th>覆盖</th></tr></thead><tbody>{line.history.map((point)=><tr key={point.period_key}><td>{point.exact_date}</td><td>{point.snapshot_alias ? catalog.snapshot_aliases.find((item)=>item.alias===point.snapshot_alias)?.label || point.snapshot_alias : point.label}</td><td>{number(point.value)}</td><td>{coverage(point.coverage_state)}</td></tr>)}</tbody></table></div><Sources refs={[...new Set(line.history.flatMap((point)=>point.source_refs))]}/></div></details>)}</div>
      {!data.business_lines.length&&<p className="overview-structure-note">当前范围没有可显示的业务线记录。</p>}
      {data.reconciliation&&<details className="overview-reconciliation"><summary>库存金额与总览核对 · {{matched:'一致',mismatch:'存在差额',partial:'覆盖不完整',unavailable:'无法核对'}[data.reconciliation.status] || data.reconciliation.status}</summary><p>明细 {number(data.reconciliation.detail_value)} {data.reconciliation.detail_unit} × {number(data.reconciliation.conversion_factor)} = {number(data.reconciliation.converted_value)} {data.reconciliation.overview_unit}；总览 {number(data.reconciliation.overview_fact_value)} {data.reconciliation.overview_unit}；差额 {delta(data.reconciliation.gap)} {data.reconciliation.overview_unit}。</p><Sources refs={data.reconciliation.source_refs}/></details>}
    </section>
    <section className="management-panel overview-conclusions" aria-labelledby="overview-conclusions-title"><div className="overview-structure-heading"><div><h3 id="overview-conclusions-title">重点结论与关注</h3><p>基于同一数据版本的确定性规则；当前为本地候选规则，不代表已恢复完整 V6 规则。</p></div><button onClick={()=>onAnalysis()}>查看明细分析</button></div>
      {conclusions ? <><ol>{conclusions.items.map((item)=><li key={item.rule_id}><strong>{item.title}</strong><p>{item.summary}</p><div className="overview-rule-scope">{item.rule_id==='OVR_FORM_MAX_POSITIVE_INVENTORY_DELTA_V1'?'评估范围：当前业务范围内的原材料、半成品、成品（不受选中形态限制）':`评估范围：${data.scope_summary.label} · ${selection}`}</div><details className="overview-rule-evidence"><summary>查看规则条件与数值依据</summary><dl><dt>规则版本</dt><dd>{conclusions.ruleset_id}</dd><dt>规则编号</dt><dd>{item.rule_id}</dd><dt>触发条件</dt><dd>{ruleConditions[item.rule_id] || operatorConditions[String(item.condition.operator)] || '服务端已按该版本规则判定触发，请结合下方数值证据查看。'}</dd><dt>分析 / 基期</dt><dd>{String(item.condition.current_period || data.analysis.period_key)} / {String(item.condition.baseline_period || data.baseline.period_key)}</dd><dt>作用范围</dt><dd>{data.scope_summary.label} · {item.rule_id==='OVR_FORM_MAX_POSITIVE_INVENTORY_DELTA_V1'?'原材料、半成品、成品三种形态':selection}</dd><dt>数据要求</dt><dd>{item.rule_id==='OVR_DATA_COVERAGE_INCOMPLETE_V1'?'数据覆盖不完整；本条为数据质量提示，受影响的业务结论已停止输出。':item.rule_id==='OVR_TURNOVER_ABOVE_TARGET_V1'?'当前周转事实与精确匹配的目标必须完整；无匹配目标时不作比较。':'所需当前、基期及比较事实必须完整；缺失值不参与排名或补为零。'}</dd></dl>{item.evidence.map((evidence,index)=><div className="overview-evidence-item" key={`${evidence.entity_id}-${evidence.metric_id}-${index}`}><strong>{item.entities.find((entity)=>entity.id===evidence.entity_id)?.label || scopeName(evidence.entity_id)} · {metricName(evidence.metric_id)}</strong><p>{scopeName(evidence.scope_id)} · {formName(evidence.material_form)}；{evidence.current_period} 较 {evidence.baseline_period}</p><p>当前 {number(evidence.current)} {evidence.unit}；基期 {number(evidence.baseline)} {evidence.unit}；差值 {delta(evidence.absolute_delta)} {evidence.unit}；相对变化 {percent(evidence.relative_delta)}</p>{evidence.current_share!=null&&<p>&gt;180 天占比：当前 {percent(evidence.current_share)}，基期 {percent(evidence.baseline_share)}；变化 {evidence.share_delta==null?'—':`${(Number(evidence.share_delta)*100).toFixed(2)} 个百分点`}</p>}{evidence.target!=null&&<p>目标 {evidence.target_period}：{number(evidence.target)} {evidence.unit}；较目标差值 {delta(evidence.gap)} {evidence.unit}</p>}<Sources refs={evidence.source_refs}/></div>)}</details>{item.drilldown?.page==='management-analysis'&&<button className="overview-rule-drilldown" onClick={()=>onAnalysis(item.drilldown!.query)}>查看对应明细</button>}</li>)}</ol>{!conclusions.items.length&&<p className="overview-rule-empty">未触发已配置规则。</p>}</>:<p className="overview-rule-empty">本版本尚未提供规则结论。</p>}
    </section>
  </>;
}
