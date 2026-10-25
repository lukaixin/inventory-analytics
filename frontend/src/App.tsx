import { useEffect, useMemo, useRef, useState } from "react";
import * as A from "./api";
import OverviewStructure from "./OverviewStructure";

type Page = "overview" | "explore" | "aging" | "mwd" | "versions";
const pageNames: Record<Page, string> = {
  overview: "总览",
  explore: "库存探索",
  aging: "库龄",
  mwd: "MWD 专题",
  versions: "数据版本与来源",
};
const n = (v: unknown, digits = 2) => {
  if (v === null || v === undefined) return "暂无数据";
  const value = Number(v);
  const precision = value !== 0 && Math.abs(value) < 0.01 ? 4 : digits;
  return value.toLocaleString("zh-CN", { maximumFractionDigits: precision });
};
const pct = (v: unknown) =>
  v === null || v === undefined ? "—" : `${(Number(v) * 100).toFixed(1)}%`;
const sourceRef = (row: A.TrendRow, key: string) => row.sources?.[key];

function Loading({ label = "正在读取数据" }: { label?: string }) {
  return <div className="state loading">{label}…</div>;
}
function ErrorState({ error, retry }: { error: unknown; retry: () => void }) {
  return (
    <div className="state error">
      <strong>无法加载</strong>
      <span>{error instanceof Error ? error.message : "请求失败"}</span>
      <button onClick={retry}>重新加载</button>
    </div>
  );
}
function Empty({ label = "暂无数据" }: { label?: string }) {
  return <div className="state">{label}</div>;
}
function Panel({
  title,
  children,
  aside,
}: {
  title: string;
  children: React.ReactNode;
  aside?: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-title">
        <h2>{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}
function Badge({
  children,
  tone = "cyan",
}: {
  children: React.ReactNode;
  tone?: "cyan" | "orange" | "muted";
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
function DataHeader({
  dataset,
  version,
  period,
  synthetic = false,
}: {
  dataset?: A.Dataset;
  version?: A.Version;
  period?: string;
  synthetic?: boolean;
}) {
  return (
    <div className="data-header">
      <Badge tone={synthetic ? "orange" : "cyan"}>
        {synthetic ? "合成演示数据" : "来源转录初稿"}
      </Badge>
      <span>{dataset?.title || "未选择数据系列"}</span>
      <span>{version?.label || "未选择版本"}</span>
      {period && <span>{period}</span>}
      <span className="access">本地演示：全范围</span>
    </div>
  );
}
function MiniChart({
  points,
  highlight,
  unit,
}: {
  points: { label: string; value: unknown }[];
  highlight?: string;
  unit?: string;
}) {
  const [selected, setSelected] = useState(highlight || "");
  const chartRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState(560);
  useEffect(() => {
    if (highlight) setSelected(highlight);
  }, [highlight]);
  useEffect(() => {
    const element = chartRef.current;
    if (!element) return;
    const update = () =>
      setChartWidth(Math.max(280, Math.round(element.clientWidth)));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  const known = points
    .map((x, i) => ({
      ...x,
      i,
      value: x.value === null || x.value === undefined ? null : Number(x.value),
    }))
    .filter(
      (x): x is { label: string; i: number; value: number } =>
        x.value !== null && Number.isFinite(x.value),
    );
  if (!known.length) return <Empty />;
  const selectedPoint =
    known.find((point) => point.label === selected) ||
    known.find((point) => point.label === highlight) ||
    known.at(-1)!;
  const rawMin = Math.min(...known.map((x) => x.value)),
    rawMax = Math.max(...known.map((x) => x.value));
  const padding = (rawMax - rawMin || Math.max(Math.abs(rawMax), 1)) * 0.12;
  const roughSpan = rawMax + padding - (rawMin - padding);
  const magnitude = 10 ** Math.floor(Math.log10(roughSpan || 1));
  const step =
    (roughSpan / magnitude <= 2 ? 0.2 : roughSpan / magnitude <= 5 ? 0.5 : 1) *
    magnitude;
  const min = Math.floor((rawMin - padding) / step) * step,
    max = Math.ceil((rawMax + padding) / step) * step,
    span = max - min || 1;
  const chartHeight = Math.max(
    116,
    Math.min(146, Math.round(chartWidth * 0.24)),
  );
  const left = 58,
    right = 12,
    top = 23,
    bottom = 25;
  const plotWidth = chartWidth - left - right,
    plotHeight = chartHeight - top - bottom;
  const x = (index: number) =>
    left + (index / Math.max(points.length - 1, 1)) * plotWidth;
  const y = (value: number) =>
    top + plotHeight - ((value - min) / span) * plotHeight;
  let previous = -2;
  const path = known
    .map((point) => {
      const command = point.i === previous + 1 ? "L" : "M";
      previous = point.i;
      return `${command}${x(point.i).toFixed(1)},${y(point.value).toFixed(1)}`;
    })
    .join(" ");
  return (
    <div className="mini-chart" ref={chartRef}>
      <div className="chart-summary">
        <span>{selectedPoint.label}</span>
        <strong>
          {n(selectedPoint.value)}
          {unit && <small>{unit}</small>}
        </strong>
      </div>
      <svg
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        role="img"
        aria-label={`趋势图${unit ? `，单位${unit}` : ""}：${known.map((p) => `${p.label} ${n(p.value)}`).join("；")}`}
      >
        <title>
          {known
            .map((p) => `${p.label} ${n(p.value)}${unit ? ` ${unit}` : ""}`)
            .join("；")}
        </title>
        {unit && (
          <text className="chart-unit" x="0" y="12">
            {unit}
          </text>
        )}
        <line
          className="chart-grid"
          x1={left}
          x2={chartWidth - right}
          y1={top}
          y2={top}
        />
        <line
          className="chart-grid"
          x1={left}
          x2={chartWidth - right}
          y1={top + plotHeight / 2}
          y2={top + plotHeight / 2}
        />
        <line
          className="chart-grid"
          x1={left}
          x2={chartWidth - right}
          y1={top + plotHeight}
          y2={top + plotHeight}
        />
        <text x="0" y={top + 4}>
          {n(max)}
        </text>
        <text x="0" y={top + plotHeight / 2 + 4}>
          {n((min + max) / 2)}
        </text>
        <text x="0" y={top + plotHeight + 4}>
          {n(min)}
        </text>
        <path d={path} fill="none" className="chart-line" />
        {known.map((point) => (
          <g key={point.label}>
            <circle
              tabIndex={0}
              role="button"
              aria-label={`${point.label}：${n(point.value)}${unit ? ` ${unit}` : ""}`}
              onClick={() => setSelected(point.label)}
              onFocus={() => setSelected(point.label)}
              className={point.label === selectedPoint.label ? "selected" : ""}
              cx={x(point.i)}
              cy={y(point.value)}
              r={point.label === selectedPoint.label ? 4 : 3}
            />
            <title>{`${point.label}：${n(point.value)}${unit ? ` ${unit}` : ""}`}</title>
          </g>
        ))}
        {points.map((point, index) => (
          <text
            className="chart-x"
            key={point.label}
            x={x(index)}
            y={chartHeight - 5}
            textAnchor="middle"
          >
            {chartWidth < 420 && /^\d{4}-\d{2}-\d{2}$/.test(point.label)
              ? point.label.slice(5)
              : point.label}
          </text>
        ))}
      </svg>
    </div>
  );
}

function LegacyWorkspace() {
  const [page, setPage] = useState<Page>("overview");
  const [datasets, setDatasets] = useState<A.Dataset[]>([]);
  const [versions, setVersions] = useState<Record<string, A.Version[]>>({});
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState(true);
  const [legacyVersion, setLegacyVersion] = useState("");
  const [detailDatasetId, setDetailDatasetId] = useState("");
  const [detailVersions, setDetailVersions] = useState<Record<string, string>>(
    {},
  );
  const load = (quiet = false) => {
    if (!quiet) setBusy(true);
    setError(undefined);
    A.getDatasets()
      .then(async (x) => {
        const all = await Promise.all(
          x.data.map(
            async (d) => [d.id, (await A.getVersions(d.id)).data] as const,
          ),
        );
        const map = Object.fromEntries(all);
        setDatasets(x.data);
        setVersions(map);
        const legacy = x.data.find((d) => d.kind === "legacy");
        const details = x.data.filter((d) => d.kind === "inventory_detail");
        setLegacyVersion((v) =>
          (map[legacy?.id || ""] || []).some((q) => q.id === v)
            ? v
            : legacy?.current_version_id ||
              map[legacy?.id || ""]?.[0]?.id ||
              "",
        );
        setDetailDatasetId((v) =>
          details.some((q) => q.id === v) ? v : details[0]?.id || "",
        );
        setDetailVersions((old) =>
          Object.fromEntries(
            details.map((d) => [
              d.id,
              map[d.id].some((v) => v.id === old[d.id])
                ? old[d.id]
                : d.current_version_id || map[d.id]?.[0]?.id || "",
            ]),
          ),
        );
      })
      .catch(setError)
      .finally(() => setBusy(false));
  };
  useEffect(() => {
    let alive = true;
    const wrapped = async () => {
      if (!alive) return;
      load();
    };
    wrapped();
    return () => {
      alive = false;
    };
  }, []);
  const legacy = datasets.find((d) => d.kind === "legacy"),
    detailSets = datasets.filter((d) => d.kind === "inventory_detail"),
    detail = detailSets.find((d) => d.id === detailDatasetId),
    detailVersion = detailVersions[detailDatasetId] || "";
  const legacyV = (versions[legacy?.id || ""] || []).find(
    (x) => x.id === legacyVersion,
  );
  const detailV = (versions[detail?.id || ""] || []).find(
    (x) => x.id === detailVersion,
  );
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <header className="top">
          <div>
            <p className="eyebrow">远途 · 库存分析</p>
            <h1>库存健康看板</h1>
            <p className="subtitle">按数据版本追溯库存趋势、构成与来源</p>
          </div>
          <div className="top-meta">
            <span>本地演示环境</span>
          </div>
        </header>
        <nav aria-label="主导航">
          {(Object.keys(pageNames) as Page[]).map((k) => (
            <button
              aria-current={page === k ? "page" : undefined}
              className={page === k ? "active" : ""}
              onClick={() => setPage(k)}
              key={k}
            >
              {pageNames[k]}
            </button>
          ))}
        </nav>
      </aside>
      <section className="workspace" aria-label={pageNames[page]}>
        <h2 className="workspace-title">{pageNames[page]}</h2>
        {busy ? (
          <Loading />
        ) : error ? (
          <ErrorState error={error} retry={load} />
        ) : (
          <>
            {page === "overview" && (
              <Overview
                dataset={legacy}
                version={legacyV}
                versions={versions[legacy?.id || ""] || []}
                setVersion={setLegacyVersion}
              />
            )}{" "}
            {page === "explore" && (
              <Explore
                dataset={detail}
                detailSets={detailSets}
                version={detailV}
                versions={versions[detail?.id || ""] || []}
                setDataset={setDetailDatasetId}
                setVersion={(v) =>
                  setDetailVersions((x) => ({ ...x, [detailDatasetId]: v }))
                }
              />
            )}{" "}
            {page === "aging" && <Aging dataset={legacy} version={legacyV} />}{" "}
            {page === "mwd" && <Mwd dataset={legacy} version={legacyV} />}{" "}
            {page === "versions" && (
              <Versions
                datasets={datasets}
                versions={versions}
                legacyVersion={legacyVersion}
                detailDatasetId={detailDatasetId}
                detailVersion={detailVersion}
                setLegacyVersion={setLegacyVersion}
                setDetailDatasetId={setDetailDatasetId}
                setDetailVersion={(v) =>
                  setDetailVersions((x) => ({ ...x, [detailDatasetId]: v }))
                }
                reload={() => load(true)}
              />
            )}
          </>
        )}
      </section>
    </main>
  );
}

function Overview({
  dataset,
  version,
  versions,
  setVersion,
}: {
  dataset?: A.Dataset;
  version?: A.Version;
  versions: A.Version[];
  setVersion: (v: string) => void;
}) {
  const [scope, setScope] = useState("BG整体");
  const [result, setResult] = useState<A.LegacyDashboard>();
  const [error, setError] = useState<unknown>();
  const [analysis, setAnalysis] = useState("");
  const [baseline, setBaseline] = useState("");
  const [evidence, setEvidence] = useState<{
    ref: string;
    data?: A.Evidence;
    error?: string;
  } | null>(null);
  const load = () => {
    if (!version) return;
    setResult(undefined);
    setError(undefined);
    A.getLegacyDashboard(version.id, scope)
      .then((x) => {
        setResult(x.data);
        setAnalysis((a) => a || x.data.periods.at(-1)?.id || "");
        setBaseline((b) => b || x.data.periods[0]?.id || "");
      })
      .catch(setError);
  };
  useEffect(() => {
    let stale = false;
    if (!version) return;
    setResult(undefined);
    setError(undefined);
    A.getLegacyDashboard(version.id, scope)
      .then((x) => {
        if (stale) return;
        setResult(x.data);
        setAnalysis((a) =>
          x.data.periods.some((p) => p.id === a)
            ? a
            : x.data.periods.at(-1)?.id || "",
        );
        setBaseline((b) =>
          x.data.periods.some((p) => p.id === b)
            ? b
            : x.data.periods[0]?.id || "",
        );
      })
      .catch((e) => !stale && setError(e));
    return () => {
      stale = true;
    };
  }, [version?.id, scope]);
  const rows = (result?.rows || []).filter((r) => r.scope === scope);
  const a = rows.find((r) => r.period === analysis),
    b = rows.find((r) => r.period === baseline);
  const showEvidence = async (ref?: string) => {
    if (ref && version) {
      setEvidence({ ref });
      try {
        setEvidence({ ref, data: (await A.getEvidence(version.id, ref)).data });
      } catch (e) {
        setEvidence({
          ref,
          error: e instanceof Error ? e.message : "无法读取来源",
        });
      }
    }
  };
  if (!version)
    return (
      <Empty label="当前没有历史转录版本，可先查看库存探索中的合成数据。" />
    );
  return (
    <>
      <DataHeader dataset={dataset} version={version} period="月度实际 1–8月" />
      <Panel
        title="趋势总览"
        aside={
          <label>
            版本{" "}
            <select
              value={version?.id || ""}
              onChange={(e) => setVersion(e.target.value)}
            >
              {versions.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.label}
                </option>
              ))}
            </select>
          </label>
        }
      >
        <div className="filters">
          <label>
            范围{" "}
            <select value={scope} onChange={(e) => setScope(e.target.value)}>
              {(result?.scopes || [scope]).map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <label>
            分析月{" "}
            <select
              value={analysis}
              onChange={(e) => setAnalysis(e.target.value)}
            >
              {(result?.periods || []).map((x) => (
                <option key={x.id}>{x.id}</option>
              ))}
            </select>
          </label>
          <label>
            基期月{" "}
            <select
              value={baseline}
              onChange={(e) => setBaseline(e.target.value)}
            >
              {(result?.periods || []).map((x) => (
                <option key={x.id}>{x.id}</option>
              ))}
            </select>
          </label>
        </div>
        {error ? (
          <ErrorState error={error} retry={load} />
        ) : !result ? (
          <Loading />
        ) : (
          <>
            <p className="scale-note">
              各指标按自身数据范围使用独立刻度；金额、天数不作跨卡图形比较。
            </p>
            <div className="metric-grid">
              {result.metrics
                .filter((m) =>
                  [
                    "turnover",
                    "average_inventory",
                    "inventory",
                    "ship_cost",
                  ].includes(m.id),
                )
                .map((m) => {
                  const current = a?.[m.id],
                    base = b?.[m.id],
                    delta =
                      current === undefined ||
                      base === undefined ||
                      current === null ||
                      base === null
                        ? null
                        : Number(current) - Number(base);
                  const ratio =
                    delta === null ||
                    base === null ||
                    base === undefined ||
                    Number(base) === 0
                      ? null
                      : delta / Number(base);
                  return (
                    <article className="metric" key={m.id}>
                      <div>
                        <span>
                          {m.id === "turnover" ? "周转天数" : m.label}
                        </span>
                        <button
                          className="link"
                          onClick={() => a && showEvidence(sourceRef(a, m.id))}
                        >
                          查看来源
                        </button>
                      </div>
                      <strong>
                        {n(current)} <i>{m.unit}</i>
                      </strong>
                      <p>
                        {analysis} 对比 {baseline}：
                        <b className="neutral">
                          {delta === null
                            ? "暂无数据"
                            : `${delta >= 0 ? "+" : ""}${n(delta)}`}
                        </b>
                        （{ratio === null ? "—" : pct(ratio)}）
                      </p>
                      <MiniChart
                        points={rows.map((r) => ({
                          label: r.period,
                          value: r[m.id],
                        }))}
                        highlight={analysis}
                        unit={m.unit}
                      />
                    </article>
                  );
                })}
            </div>
          </>
        )}
      </Panel>
      <Panel title="口径与核对事项">
        <p className="notice">
          四项指标均保留来源原值；这里不重算平均库存或周转。月份、0829 库龄和
          MWD 使用不同时间域。
        </p>
        <div className="check-list">
          {(result?.checks || []).slice(0, 6).map((c) => (
            <article key={c.id}>
              <Badge tone="orange">{c.id}</Badge>
              <b>{c.category}</b>
              <span>{c.impact}</span>
              <small>{c.recommendation}</small>
            </article>
          ))}
        </div>
      </Panel>
      {evidence && (
        <EvidenceModal item={evidence} close={() => setEvidence(null)} />
      )}
    </>
  );
}

function Explore({
  dataset,
  detailSets,
  version,
  versions,
  setDataset,
  setVersion,
}: {
  dataset?: A.Dataset;
  detailSets: A.Dataset[];
  version?: A.Version;
  versions: A.Version[];
  setDataset: (v: string) => void;
  setVersion: (v: string) => void;
}) {
  const [snapshots, setSnapshots] = useState<A.Snapshot[]>([]);
  const [snapshot, setSnapshot] = useState("");
  const [baseline, setBaseline] = useState("");
  const [groupBy, setGroupBy] = useState("material_category");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Record<string, string>>({});
  const [data, setData] = useState<A.Explore>();
  const [items, setItems] = useState<A.Items>();
  const [error, setError] = useState<unknown>();
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setError(undefined);
    setData(undefined);
    setItems(undefined);
    if (!version) {
      setSnapshots([]);
      return;
    }
    A.getSnapshots(version.id)
      .then((x) => {
        if (cancelled) return;
        setSnapshots(x.data);
        setSnapshot(x.data.at(-1)?.id || "");
        setBaseline(x.data[0]?.id || "");
        setPage(1);
      })
      .catch((e) => !cancelled && setError(e));
    return () => {
      cancelled = true;
    };
  }, [version?.id]);
  const load = () => {
    if (!version || !snapshot) return;
    setLoading(true);
    setError(undefined);
    const q = {
      version_id: version.id,
      snapshot_id: snapshot,
      baseline_id: baseline,
      group_by: groupBy,
      search: query,
      ...filter,
    };
    Promise.all([A.getExplore(q), A.getItems({ ...q, page, size: 10 })])
      .then(([x, y]) => {
        setData(x.data);
        setItems(y.data);
      })
      .catch(setError)
      .finally(() => setLoading(false));
  };
  useEffect(() => {
    let cancelled = false;
    if (!version || !snapshot) return;
    setLoading(true);
    setError(undefined);
    const q = {
      version_id: version.id,
      snapshot_id: snapshot,
      baseline_id: baseline,
      group_by: groupBy,
      search: query,
      ...filter,
    };
    Promise.all([A.getExplore(q), A.getItems({ ...q, page, size: 10 })])
      .then(([x, y]) => {
        if (!cancelled) {
          setData(x.data);
          setItems(y.data);
        }
      })
      .catch((e) => !cancelled && setError(e))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [version?.id, snapshot, baseline, groupBy, query, filter, page]);
  const groupedLabel: Record<string, string> = {
    material_category: "库存大类",
    pdt: "组织 / PDT",
    customer: "客户",
    project: "项目",
    material_code: "物料",
  };
  const setGroup = (key: string) => {
    const field = groupBy === "material_code" ? "search" : groupBy;
    setFilter((f) => ({ ...f, [field]: key }));
    setQuery(groupBy === "material_code" ? key : query);
    setPage(1);
  };
  const clear = () => {
    setFilter({});
    setQuery("");
    setPage(1);
  };
  const exportCsv = () => {
    if (!version || !snapshot) return;
    const qs = A.params({
      version_id: version.id,
      snapshot_id: snapshot,
      baseline_id: baseline,
      group_by: groupBy,
      search: query,
      ...filter,
    });
    window.open(
      `${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/inventory/export?${qs}`,
      "_blank",
      "noopener",
    );
  };
  if (!version)
    return (
      <Empty label="当前没有库存明细版本，请在数据版本与来源中导入样例。" />
    );
  return (
    <>
      <DataHeader
        dataset={dataset}
        version={version}
        period={`${snapshots.length} 个可选时点 · 合成演示`}
        synthetic
      />
      <Panel
        title="库存构成与变化"
        aside={
          <div className="inline-selects">
            <label>
              系列{" "}
              <select
                value={dataset?.id || ""}
                onChange={(e) => setDataset(e.target.value)}
              >
                {detailSets.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              版本{" "}
              <select
                value={version?.id || ""}
                onChange={(e) => setVersion(e.target.value)}
              >
                {versions.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        }
      >
        <div className="filters">
          <label>
            分析时点{" "}
            <select
              value={snapshot}
              onChange={(e) => {
                setSnapshot(e.target.value);
                setPage(1);
              }}
            >
              {snapshots.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            比较时点{" "}
            <select
              value={baseline}
              onChange={(e) => {
                setBaseline(e.target.value);
                setPage(1);
              }}
            >
              <option value="">不比较</option>
              {snapshots.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            分解维度{" "}
            <select
              value={groupBy}
              onChange={(e) => {
                setGroupBy(e.target.value);
                clear();
              }}
            >
              {Object.entries(groupedLabel).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label>
            搜索{" "}
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              placeholder="物料名称或编码"
            />
          </label>
        </div>
        {error ? (
          <ErrorState error={error} retry={load} />
        ) : loading || !data ? (
          <Loading />
        ) : data.groups.length === 0 ? (
          <Empty label="当前筛选没有可展示的库存记录" />
        ) : (
          <>
            <div className="totals">
              <div>
                <span>
                  {data.unknown_count > 0 ? "已知金额小计" : "分析时点合计"}
                </span>
                <strong>
                  {n(data.current_total)} <i>{data.unit}</i>
                </strong>
              </div>
              <div>
                <span>
                  {(data.baseline_unknown_count || 0) > 0
                    ? "比较时点已知金额小计"
                    : "比较时点合计"}
                </span>
                <strong>
                  {n(data.baseline_total)} <i>{data.unit}</i>
                </strong>
              </div>
              <div>
                <span>变化</span>
                <strong className="orange">
                  {data.delta === null
                    ? "—"
                    : `${Number(data.delta) >= 0 ? "+" : ""}${n(data.delta)}`}{" "}
                  <i>{data.unit}</i>
                </strong>
              </div>
              <div>
                <span>未知金额行</span>
                <strong>{data.unknown_count}</strong>
              </div>
            </div>
            <>
              {(data.unknown_count > 0 ||
                (data.baseline_unknown_count || 0) > 0) && (
                <p className="notice">
                  变化仅比较已知金额，含未知金额的快照不代表完整库存差额。
                </p>
              )}
            </>
            <div className="breadcrumb">
              {Object.entries(filter)
                .filter(([, v]) => v)
                .map(([k, v]) => (
                  <span key={k}>
                    {groupedLabel[k] || k}：{v}
                  </span>
                ))}
              {(query || Object.keys(filter).length > 0) && (
                <button className="link" onClick={clear}>
                  清除筛选
                </button>
              )}
            </div>
            <div className="group-bars">
              {data.groups.map((g) => {
                const width = Math.max(
                  0,
                  Math.min(100, Number(g.share || 0) * 100),
                );
                return groupBy === "material_code" ? (
                  <div key={g.key}>
                    <span>{g.key}（已到最细层级）</span>
                    <span className="bar-track">
                      <b style={{ width: `${width}%` }} />
                    </span>
                    <em>
                      {n(g.current)} / {pct(g.share)}
                    </em>
                    <small>
                      {g.delta === null
                        ? ""
                        : `${Number(g.delta) >= 0 ? "+" : ""}${n(g.delta)}`}
                    </small>
                  </div>
                ) : (
                  <button key={g.key} onClick={() => setGroup(g.key)}>
                    <span>{g.key}</span>
                    <span className="bar-track">
                      <b style={{ width: `${width}%` }} />
                    </span>
                    <em>
                      {n(g.current)} / {pct(g.share)}
                    </em>
                    <small>
                      {g.delta === null
                        ? ""
                        : `${Number(g.delta) >= 0 ? "+" : ""}${n(g.delta)}`}
                    </small>
                  </button>
                );
              })}
            </div>
            <MiniChart
              points={data.trend.map((x) => ({
                label: x.label,
                value: x.total,
              }))}
              unit={data.unit}
            />
            <p className="scale-note">
              快照按记录顺序等距展示，间距不代表实际时间跨度。
            </p>
          </>
        )}
      </Panel>
      <Panel
        title="末级明细"
        aside={<button onClick={exportCsv}>导出当前筛选</button>}
      >
        {loading || !items ? (
          <Loading />
        ) : items.items.length === 0 ? (
          <Empty label="当前筛选没有末级明细" />
        ) : (
          <>
            <div className="table-wrap">
              <table className="inventory-table">
                <thead>
                  <tr>
                    <th>物料</th>
                    <th>组织/PDT</th>
                    <th>客户</th>
                    <th>项目</th>
                    <th>库存大类</th>
                    <th>数量</th>
                    <th>单价</th>
                    <th>金额</th>
                  </tr>
                </thead>
                <tbody>
                  {items.items.map((x) => (
                    <tr key={x.id}>
                      <td>
                        <b>{x.material_code}</b>
                        <small>{x.material_description}</small>
                      </td>
                      <td>{x.pdt || "暂无数据"}</td>
                      <td>{x.customer || "暂无数据"}</td>
                      <td>{x.project || "暂无数据"}</td>
                      <td>{x.material_category || "暂无数据"}</td>
                      <td>{n(x.quantity)}</td>
                      <td>{n(x.unit_cost)}</td>
                      <td>{n(x.total_cost_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pager">
              <span>共 {items.total} 条</span>
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                上一页
              </button>
              <span>{items.page}</span>
              <button
                disabled={page * items.size >= items.total}
                onClick={() => setPage((p) => p + 1)}
              >
                下一页
              </button>
            </div>
          </>
        )}
      </Panel>
    </>
  );
}

function Aging({
  dataset,
  version,
}: {
  dataset?: A.Dataset;
  version?: A.Version;
}) {
  const [data, setData] = useState<A.AgingRecord[]>();
  const [error, setError] = useState<unknown>();
  const [chosen, setChosen] = useState(0);
  const [evidence, setEvidence] = useState<{
    ref: string;
    data?: A.Evidence;
    error?: string;
  } | null>(null);
  const load = () => {
    if (!version) return;
    setError(undefined);
    A.getAging(version.id)
      .then((x) => setData(x.data.records))
      .catch(setError);
  };
  useEffect(() => {
    let stale = false;
    if (!version) return;
    setData(undefined);
    setError(undefined);
    A.getAging(version.id)
      .then((x) => !stale && setData(x.data.records))
      .catch((e) => !stale && setError(e));
    return () => {
      stale = true;
    };
  }, [version?.id]);
  const r = data?.[chosen];
  const maxBucket = Math.max(
    ...(r?.buckets.map((b) => Number(b.value || 0)) || []),
    1,
  );
  const show = async (ref?: string) => {
    if (!ref || !version) return;
    setEvidence({ ref });
    try {
      setEvidence({ ref, data: (await A.getEvidence(version.id, ref)).data });
    } catch (e) {
      setEvidence({
        ref,
        error: e instanceof Error ? e.message : "无法读取来源",
      });
    }
  };
  if (!version)
    return (
      <Empty label="当前没有历史转录版本，可先查看库存探索中的合成数据。" />
    );
  return (
    <>
      <DataHeader dataset={dataset} version={version} period="0829 来源快照" />
      <Panel title="库龄结构">
        <p className="notice">
          仅展示来源 0829
          快照。总计、超180天合计和桶值为独立原值，差额及空值不自动补齐。
        </p>
        {error ? (
          <ErrorState error={error} retry={load} />
        ) : !data ? (
          <Loading />
        ) : data.length === 0 ? (
          <Empty />
        ) : (
          <>
            <label>
              来源组{" "}
              <select
                value={chosen}
                onChange={(e) => setChosen(Number(e.target.value))}
              >
                {data.map((x, i) => (
                  <option value={i} key={i}>
                    {x.form} / {x.scope} / {x.category}
                  </option>
                ))}
              </select>
            </label>
            <div className="totals">
              <div>
                <span>总计</span>
                <strong>
                  {n(r?.total)} <i>{r?.unit || "亿"}</i>
                </strong>
              </div>
              <div>
                <span>超180天合计</span>
                <strong className="orange">
                  {n(r?.old_total)} <i>{r?.unit || "亿"}</i>
                </strong>
              </div>
              <div>
                <span>来源差额</span>
                <strong>
                  {n(r?.reconciliation_gap)} <i>{r?.unit || "亿"}</i>
                </strong>
              </div>
              <div>
                <span>时间</span>
                <strong>{r?.snapshot || "0829"}</strong>
              </div>
            </div>
            <div className="group-bars aging-bars">
              {r?.buckets.map((x) => {
                const width = Math.max(
                  0,
                  Math.min(100, (Number(x.value || 0) / maxBucket) * 100),
                );
                return (
                  <div key={x.label}>
                    <span>{x.label}</span>
                    <span className="bar-track">
                      <b style={{ width: `${width}%` }} />
                    </span>
                    <em>
                      {n(x.value)} {x.unit}
                    </em>
                    <small>
                      {x.source && (
                        <button className="link" onClick={() => show(x.source)}>
                          查看来源
                        </button>
                      )}
                    </small>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </Panel>
      {evidence && (
        <EvidenceModal item={evidence} close={() => setEvidence(null)} />
      )}
    </>
  );
}

function Mwd({
  dataset,
  version,
}: {
  dataset?: A.Dataset;
  version?: A.Version;
}) {
  const [data, setData] = useState<A.MwdData>();
  const [error, setError] = useState<unknown>();
  const [scope, setScope] = useState("");
  const [evidence, setEvidence] = useState<{
    ref: string;
    data?: A.Evidence;
    error?: string;
  } | null>(null);
  const load = () => {
    if (!version) return;
    setError(undefined);
    A.getMwd(version.id)
      .then((x) => {
        setData(x.data);
        setScope((s) => s || x.data.summary[0]?.scope || "");
      })
      .catch(setError);
  };
  useEffect(() => {
    let stale = false;
    if (!version) return;
    setData(undefined);
    setError(undefined);
    A.getMwd(version.id)
      .then((x) => {
        if (!stale) {
          setData(x.data);
          setScope(x.data.summary[0]?.scope || "");
        }
      })
      .catch((e) => !stale && setError(e));
    return () => {
      stale = true;
    };
  }, [version?.id]);
  const rows = (data?.summary || []).filter((x) => !scope || x.scope === scope);
  const show = async (ref?: string) => {
    if (!ref || !version) return;
    setEvidence({ ref });
    try {
      setEvidence({ ref, data: (await A.getEvidence(version.id, ref)).data });
    } catch (e) {
      setEvidence({
        ref,
        error: e instanceof Error ? e.message : "无法读取来源",
      });
    }
  };
  const first = (x: A.MwdRow) => Object.values(x.sources || {})[0];
  if (!version)
    return (
      <Empty label="当前没有历史转录版本，可先查看库存探索中的合成数据。" />
    );
  return (
    <>
      <DataHeader
        dataset={dataset}
        version={version}
        period="MWD 独立来源时间域"
      />
      <Panel title="MWD 汇总">
        <p className="notice">
          MWD层级可能相互覆盖，页面不把各范围相加。清单对应总库存与MWD库存分别展示。
        </p>
        {error ? (
          <ErrorState error={error} retry={load} />
        ) : !data ? (
          <Loading />
        ) : (
          <>
            <label>
              范围{" "}
              <select value={scope} onChange={(e) => setScope(e.target.value)}>
                {data.summary.map((x) => (
                  <option key={x.scope}>{x.scope}</option>
                ))}
              </select>
            </label>
            <div className="table-wrap">
              <table className="mwd-table mwd-summary-table">
                <thead>
                  <tr>
                    <th>范围</th>
                    <th>项目</th>
                    <th>清单对应总库存</th>
                    <th>MWD库存</th>
                    <th>PO</th>
                    <th>来源合计</th>
                    <th>计提</th>
                    <th>来源</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((x, i) => (
                    <tr key={i}>
                      <td>{x.scope}</td>
                      <td>{x.item}</td>
                      <td>
                        {n(x.inventory)} {x.unit}
                      </td>
                      <td className="orange">
                        {n(x.stock)} {x.unit}
                      </td>
                      <td>{n(x.po)}</td>
                      <td>{n(x.total)}</td>
                      <td>{n(x.provision)}</td>
                      <td>
                        <button className="link" onClick={() => show(first(x))}>
                          查看
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Panel>
      <Panel title="来源可见明细">
        <div className="table-wrap">
          <table className="mwd-table mwd-detail-table">
            <thead>
              <tr>
                <th>范围</th>
                <th>项目</th>
                <th>MWD库存</th>
                <th>PO</th>
                <th>来源合计</th>
                <th>备注</th>
                <th>来源</th>
              </tr>
            </thead>
            <tbody>
              {(data?.details || []).map((x, i) => (
                <tr key={i}>
                  <td>{x.scope}</td>
                  <td>{x.item}</td>
                  <td>
                    {n(x.stock)} {x.unit}
                  </td>
                  <td>{n(x.po)}</td>
                  <td>{n(x.total)}</td>
                  <td>{x.note || "—"}</td>
                  <td>
                    <button className="link" onClick={() => show(first(x))}>
                      查看
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      {evidence && (
        <EvidenceModal item={evidence} close={() => setEvidence(null)} />
      )}
    </>
  );
}

function Versions({
  datasets,
  versions,
  legacyVersion,
  detailDatasetId,
  detailVersion,
  setLegacyVersion,
  setDetailDatasetId,
  setDetailVersion,
  reload,
}: {
  datasets: A.Dataset[];
  versions: Record<string, A.Version[]>;
  legacyVersion: string;
  detailDatasetId: string;
  detailVersion: string;
  setLegacyVersion: (x: string) => void;
  setDetailDatasetId: (x: string) => void;
  setDetailVersion: (x: string) => void;
  reload: () => void;
}) {
  const [source, setSource] = useState<A.Source>();
  const [checks, setChecks] = useState<A.Check[]>();
  const [file, setFile] = useState<File>();
  const [preview, setPreview] = useState<any>();
  const [message, setMessage] = useState("");
  const [current, setCurrent] = useState(false);
  const [sourceDatasetId, setSourceDatasetId] = useState("");
  const legacy = datasets.find((x) => x.kind === "legacy");
  const sourceDataset =
    datasets.find((x) => x.id === sourceDatasetId) || legacy;
  const sourceVersion =
    sourceDataset?.kind === "legacy"
      ? legacyVersion
      : sourceDataset?.id === detailDatasetId
        ? detailVersion
        : (versions[sourceDataset?.id || ""] || [])[0]?.id || "";
  const loadSource = async () => {
    if (!sourceVersion) return;
    try {
      setSource((await A.getSource(sourceVersion)).data);
      if (sourceDataset?.kind === "legacy")
        setChecks(
          (await A.getLegacyDashboard(sourceVersion)).data.checks || [],
        );
      else setChecks([]);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "无法获取来源");
    }
  };
  useEffect(() => {
    setSource(undefined);
    setChecks(undefined);
    loadSource();
  }, [sourceVersion, sourceDataset?.id]);
  const chooseVersion = (dataset: A.Dataset, id: string) => {
    if (dataset.kind === "legacy") setLegacyVersion(id);
    else {
      setDetailDatasetId(dataset.id);
      setDetailVersion(id);
    }
    setSourceDatasetId(dataset.id);
  };
  const download = async () => {
    const r = await fetch(
      `${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/imports/template`,
    );
    if (!r.ok) {
      setMessage("模板下载失败");
      return;
    }
    const blob = await r.blob(),
      url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = "canonical_json_v1_template.json";
    a.click();
    URL.revokeObjectURL(url);
  };
  const previewFile = async () => {
    if (!file) return;
    setPreview(undefined);
    setMessage("");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || "/api/v1"}/imports/preview`,
        { method: "POST", body: fd },
      );
      const b = await r.json();
      if (!r.ok) throw new Error(b?.error?.message || "预览失败");
      setPreview(b.data);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "预览失败");
    }
  };
  const commit = async () => {
    if (!preview?.id) return;
    try {
      const r = await A.api<{
        version_id: string;
        series_id?: string;
        already_committed: boolean;
      }>(`/imports/${preview.id}/commit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ set_current: current }),
      });
      if (r.data.series_id) {
        setDetailDatasetId(r.data.series_id);
        setSourceDatasetId(r.data.series_id);
      }
      setDetailVersion(r.data.version_id);
      setMessage(
        `已提交版本 ${r.data.version_id}${r.data.already_committed ? "（重复提交已复用）" : ""}`,
      );
      reload();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "提交失败");
    }
  };
  return (
    <>
      <DataHeader
        dataset={sourceDataset}
        version={(versions[sourceDataset?.id || ""] || []).find(
          (x) => x.id === sourceVersion,
        )}
        period="来源、版本和导入"
      />
      <div className="two-col">
        <Panel title="数据系列与版本">
          <div className="version-list">
            {datasets.map((d) => (
              <article key={d.id}>
                <div>
                  <Badge tone={d.kind === "legacy" ? "cyan" : "orange"}>
                    {d.kind === "legacy" ? "转录初稿" : "合成演示"}
                  </Badge>
                  <h3>{d.title}</h3>
                  <small>{d.code}</small>
                </div>
                <label>
                  选择版本{" "}
                  <select
                    value={
                      d.kind === "legacy"
                        ? legacyVersion
                        : d.id === detailDatasetId
                          ? detailVersion
                          : ""
                    }
                    onChange={(e) => chooseVersion(d, e.target.value)}
                  >
                    {(versions[d.id] || []).map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.label} / {v.evidence_level}
                      </option>
                    ))}
                  </select>
                </label>
              </article>
            ))}
          </div>
        </Panel>
        <Panel title="来源与限制">
          <label>
            查看系列{" "}
            <select
              value={sourceDataset?.id || ""}
              onChange={(e) => {
                const d = datasets.find((x) => x.id === e.target.value);
                if (d) {
                  setSourceDatasetId(d.id);
                  if (d.kind === "inventory_detail") setDetailDatasetId(d.id);
                }
              }}
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.title}
                </option>
              ))}
            </select>
          </label>
          <button onClick={loadSource}>刷新来源信息</button>
          {source ? (
            <dl className="source">
              <dt>文件</dt>
              <dd>{source.filename}</dd>
              <dt>SHA-256</dt>
              <dd className="hash">{source.sha256}</dd>
              <dt>证据等级</dt>
              <dd>{source.evidence_level}</dd>
              <dt>限制</dt>
              <dd>{source.limitations?.join("；") || "暂无附加限制"}</dd>
            </dl>
          ) : (
            <Loading />
          )}
        </Panel>
      </div>
      <Panel title="导入合成演示数据">
        <p className="notice">
          当前仅接收 canonical_json_v1
          的合成数据。预览不会创建正式版本，提交默认不切换当前版本。
        </p>
        <div className="import-row">
          <button onClick={download}>下载规范模板</button>
          <label>
            选择 JSON{" "}
            <input
              type="file"
              accept="application/json,.json"
              onChange={(e) => {
                setFile(e.target.files?.[0]);
                setPreview(undefined);
                setMessage("");
              }}
            />
          </label>
          <button disabled={!file} onClick={previewFile}>
            开始预览
          </button>
        </div>
        {preview && (
          <div className="preview">
            <Badge tone={preview.status === "preview" ? "cyan" : "orange"}>
              {preview.status}
            </Badge>
            <span>
              记录 {preview.row_count} 条，快照 {preview.snapshot_count} 个
            </span>
            <span>SHA {preview.sha256}</span>
            {preview.errors?.length > 0 && (
              <ul>
                {preview.errors.map((x: string) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            )}
            {preview.warnings?.length > 0 && (
              <ul>
                {preview.warnings.map((x: string) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            )}
            {preview.sample?.length > 0 && (
              <div className="table-wrap preview-table">
                <table>
                  <thead>
                    <tr>
                      <th>快照</th>
                      <th>物料</th>
                      <th>金额</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.sample.slice(0, 3).map((x: any, i: number) => (
                      <tr key={i}>
                        <td>{x.snapshot_key ?? x.snapshot ?? "—"}</td>
                        <td>{x.material_code ?? x.record_key ?? "—"}</td>
                        <td>{x.total_cost_amount ?? x.amount ?? "暂无数据"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {preview.status === "preview" && preview.errors?.length === 0 && (
              <div>
                <label>
                  <input
                    type="checkbox"
                    checked={current}
                    onChange={(e) => setCurrent(e.target.checked)}
                  />{" "}
                  提交后设为当前版本
                </label>
                <button onClick={commit}>确认提交</button>
              </div>
            )}
          </div>
        )}
        {message && <p className="notice">{message}</p>}
      </Panel>
      <Panel title="转录核对事项">
        <div className="check-list">
          {checks === undefined ? (
            <Loading />
          ) : checks.length === 0 ? (
            <Empty
              label={
                sourceDataset?.kind === "legacy"
                  ? "当前版本没有可显示的核对事项"
                  : "该合成系列不含历史转录核对事项"
              }
            />
          ) : (
            checks.map((c) => (
              <article key={c.id}>
                <Badge tone="orange">{c.id}</Badge>
                <b>{c.category}</b>
                <span>{c.evidence}</span>
                <small>
                  {c.status}：{c.recommendation}
                </small>
              </article>
            ))
          )}
        </div>
      </Panel>
    </>
  );
}

function EvidenceModal({
  item,
  close,
}: {
  item: { ref: string; data?: A.Evidence; error?: string };
  close: () => void;
}) {
  useEffect(() => {
    const f = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", f);
    return () => window.removeEventListener("keydown", f);
  }, [close]);
  const x = item.data;
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={close}>
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-title"
        className="modal"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="panel-title">
          <h2 id="evidence-title">来源明细</h2>
          <button autoFocus onClick={close}>
            关闭
          </button>
        </div>
        {item.error ? (
          <div className="state error">
            <strong>无法读取来源</strong>
            <span>{item.error}</span>
          </div>
        ) : !x ? (
          <Loading label="正在读取来源" />
        ) : (
          <dl className="source">
            <dt>引用</dt>
            <dd>{x.ref}</dd>
            <dt>工作表 / 行</dt>
            <dd>
              {x.sheet || "—"} / {x.row || "—"}
            </dd>
            <dt>来源图片索引</dt>
            <dd>{x.image ?? "—"}</dd>
            <dt>原始单元格</dt>
            <dd>{x.original_cell || "—"}</dd>
            <dt>原始值</dt>
            <dd>
              {x.raw_text ?? x.raw_value ?? "暂无数据"} {x.unit || ""}
            </dd>
            <dt>说明</dt>
            <dd>{x.note || "暂无补充说明"}</dd>
          </dl>
        )}
      </section>
    </div>
  );
}

type ManagementPage = "management-overview" | "management-analysis" | "management-table" | "sources";
const managementPageNames: Record<ManagementPage, string> = {
  "management-overview": "趋势总览",
  "management-analysis": "明细分析",
  "management-table": "库存数据表",
  sources: "来源与专题",
};
const managementNumber = (value: string | number | null | undefined, digits = 2) =>
  value === null || value === undefined ? "暂无数据" : n(value, digits);
const managementDelta = (value: string | null | undefined, unit = "") =>
  value === null || value === undefined ? "—" : `${Number(value) >= 0 ? "+" : ""}${managementNumber(value)}${unit ? ` ${unit}` : ""}`;
const managementPercent = (value: string | null | undefined) =>
  value === null || value === undefined ? "—" : `${(Number(value) * 100).toFixed(1)}%`;
const coverageLabel = (value: string) => value === "complete" ? "完整" : value === "partial" ? "部分覆盖" : "暂无数据";
const riskLabel = (value: string) => value === "unclassified" ? "规则待确认" : value === "evaluated" ? "已按规则评估" : value === "partially_evaluated" ? "部分规则可评估" : "暂无数据";
const quantityStatusLabel = (value: string) => value === "additive" ? "可加" : value === "mixed_unit" ? "单位不一致" : value === "partial" ? "部分覆盖" : value === "unavailable" ? "暂无数据" : "不可加";

export function App() {
  const [page, setPage] = useState<ManagementPage>("management-overview");
  const [analysisSelection,setAnalysisSelection]=useState<Partial<Omit<A.ManagementAnalysisQuery,"version_id">>>();
  const [datasets, setDatasets] = useState<A.Dataset[]>([]);
  const [versionId, setVersionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>();
  const load = () => {
    setLoading(true); setError(undefined);
    A.getDatasets().then(({ data }) => {
      const management = data.find((item) => item.kind === "management_demo");
      setDatasets(data); setVersionId(management?.current_version_id || "");
    }).catch(setError).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);
  const management = datasets.find((item) => item.kind === "management_demo");
  return <main className="management-shell">
    <header className="management-topbar">
      <div><p>远途 · 库存管理</p><h1>库存管理驾驶舱</h1></div>
      <div className="management-topbar-meta"><Badge tone="orange">合成管理演示</Badge><span>本地 DuckDB · 全范围</span></div>
    </header>
    <nav className="management-nav" aria-label="库存管理主导航">
      {(Object.keys(managementPageNames) as ManagementPage[]).map((key) => <button key={key} onClick={() => {setAnalysisSelection(undefined);setPage(key);}} className={page === key ? "active" : ""} aria-current={page === key ? "page" : undefined}>{managementPageNames[key]}</button>)}
    </nav>
    <section className="management-workspace" aria-label={managementPageNames[page]}>
      {loading ? <Loading label="正在定位合成管理数据版本" /> : error ? <ErrorState error={error} retry={load} /> : !management || !versionId ? <ManagementEmpty onRetry={load} /> : <>
        {page === "management-overview" && <ManagementOverview versionId={versionId} goAnalysis={(selection) => {setAnalysisSelection(selection);setPage("management-analysis");}} />}
        {page === "management-analysis" && <ManagementAnalysis versionId={versionId} initialSelection={analysisSelection} />}
        {page === "management-table" && <ManagementTable versionId={versionId} />}
        {page === "sources" && <SourcesTopics />}
      </>}
    </section>
  </main>;
}

function ManagementEmpty({ onRetry }: { onRetry: () => void }) {
  return <section className="management-empty"><h2>合成管理演示数据尚未就绪</h2><p>当前没有可用的 management_demo 数据版本。种子数据写入后，这里会显示趋势、四时点分析和分层库存表。</p><button onClick={onRetry}>重新检查数据版本</button></section>;
}

function ManagementHeader({ catalog, versionId, detailAmount = false }: { catalog: A.ManagementCatalog; versionId: string; detailAmount?: boolean }) {
  return <div className="management-data-header"><Badge tone="orange">SYNTHETIC_MANAGEMENT_DEMO</Badge><span>合成管理演示</span><span>数据截至 {catalog.data_as_of}</span><span>{detailAmount ? catalog.unit_policy.detail_amount : catalog.unit_policy.inventory_amount}</span><span className="access">版本 {versionId.slice(0, 8)}</span></div>;
}

function useCatalog(versionId: string) {
  const [catalog, setCatalog] = useState<A.ManagementCatalog>(); const [error, setError] = useState<unknown>();
  const reload = () => { setError(undefined); A.getManagementCatalog(versionId).then((x) => setCatalog(x.data)).catch(setError); };
  useEffect(() => { setCatalog(undefined); reload(); }, [versionId]);
  return { catalog, error, reload };
}

function ManagementOverview({ versionId, goAnalysis }: { versionId: string; goAnalysis: (selection?:Partial<Omit<A.ManagementAnalysisQuery,"version_id">>) => void }) {
  const { catalog, error: catalogError, reload: reloadCatalog } = useCatalog(versionId);
  const [result, setResult] = useState<A.ManagementOverview>(); const [error, setError] = useState<unknown>();
  const requestVersion = useRef(0);
  const [structureMetric,setStructureMetric]=useState<A.StructureMetric>('turnover_days');
  const [selected, setSelected] = useState(""); const [scope, setScope] = useState("GROUP"); const [form, setForm] = useState("ALL"); const [analysisPeriod, setAnalysisPeriod] = useState(""); const [baselinePeriod, setBaselinePeriod] = useState("");
  const load = () => { const request = ++requestVersion.current; setError(undefined); setResult(undefined); return A.getManagementOverview({ version_id: versionId, scope_id: scope, material_form: form, analysis_period: analysisPeriod || undefined, baseline_period: baselinePeriod || undefined,structure_metric:structureMetric }).then((x) => { if (request !== requestVersion.current) return; setResult(x.data); setSelected((current) => x.data.cards.some((card) => card.metric_id === current) ? current : x.data.cards[0]?.metric_id || ""); }).catch((reason) => request === requestVersion.current && setError(reason)); };
  useEffect(() => { setResult(undefined); setError(undefined); load(); return()=>{++requestVersion.current;}; }, [versionId, scope, form, analysisPeriod, baselinePeriod,structureMetric]);
  if (catalogError) return <ErrorState error={catalogError} retry={reloadCatalog} />;
  if (!catalog) return <Loading label="正在读取管理口径" />;
  const periods = catalog.periods.filter((item) => item.observation_type === "actual");
  const active = result?.cards.find((card) => card.metric_id === selected);
  const defaultAnalysis = result?.cards[0]?.series.filter((point) => point.observation_type === "actual").at(-1)?.label || "当前期间";
  const defaultBaseline = result?.cards[0]?.series.find((point) => point.observation_type === "actual")?.label || "比较基期";
  return <>
    <ManagementHeader catalog={catalog} versionId={versionId} />
    <section className="management-page-head"><div><p className="management-kicker">管理层视图</p><h2>趋势总览</h2><p>实际、精确匹配的目标和预测分开呈现；指标按各自口径预计算。</p></div></section>
    <section className="management-controls" aria-label="趋势总览筛选">
      <label>范围<select value={scope} onChange={(e) => setScope(e.target.value)}><option value="GROUP">集团</option>{catalog.business_lines.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <label>物料形态<select value={form} onChange={(e) => setForm(e.target.value)}>{catalog.material_forms.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <label>分析期<select value={analysisPeriod} onChange={(e) => setAnalysisPeriod(e.target.value)}><option value="">{defaultAnalysis}</option>{periods.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
      <label>基期<select value={baselinePeriod} onChange={(e) => setBaselinePeriod(e.target.value)}><option value="">{defaultBaseline}</option>{periods.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}</select></label>
    </section>
    {error ? <ErrorState error={error} retry={load} /> : !result ? <Loading /> : <>
      <div className="management-kpi-grid">{result.cards.map((card) => <button key={card.metric_id} className={`management-kpi ${selected === card.metric_id ? "selected" : ""}`} onClick={() => setSelected(card.metric_id)} aria-pressed={selected === card.metric_id}>
        <span className="management-kpi-title">{card.label}</span><strong>{managementNumber(card.actual)} <small>{card.unit}</small></strong>
        <span className="management-kpi-delta">较基期 {managementDelta(card.absolute_delta)} {card.relative_delta === null ? "（—）" : `（${managementPercent(card.relative_delta)}）`}</span>
        <span>目标 {card.target.match_status === "matched" ? `${card.target.period_key} · ${managementNumber(card.target.value)} · 差 ${managementDelta(card.target.gap)}` : "未提供"}</span>
        <span>预测 {card.forecast.match_status === "matched" ? `${card.forecast.period_key} · ${managementNumber(card.forecast.value)} · 差 ${managementDelta(card.forecast.gap)}` : "未提供"}</span>
      </button>)}</div>
      {active && <section className="management-panel"><div className="management-panel-title"><div><h3>{active.label}趋势</h3><p>实际为实线；目标为阶梯虚线；预测为虚线。点击或使用键盘选取数据点。</p></div><Badge tone="muted">周转与平均库存按预计算口径展示</Badge></div><ManagementChart series={active.series} unit={active.unit} /></section>}
      {result.structure ? <OverviewStructure data={result.structure} conclusions={result.conclusions} catalog={catalog} metric={structureMetric} onMetric={setStructureMetric} onForm={setForm} onAnalysis={goAnalysis}/> : <section className="management-panel"><h3>库存结构概况</h3><p>当前接口尚未提供库存结构与规则结论。</p></section>}
    </>}
  </>;
}

function ManagementChart({ series, unit, mode = "overview" }: { series: A.ManagementPoint[]; unit: string; mode?: "overview" | "analysis" }) {
  const ref = useRef<HTMLDivElement>(null); const [width, setWidth] = useState(760); const [index, setIndex] = useState(-1);
  useEffect(() => { const el = ref.current; if (!el) return; const resize = () => setWidth(Math.max(280, Math.round(el.clientWidth))); resize(); const observer = new ResizeObserver(resize); observer.observe(el); return () => observer.disconnect(); }, []);
  const source = series;
  const displayed = source.map((item, i) => {
    const quarter = item.observation_type === "target" ? item.period_key.match(/^(\d{4})-Q([1-4])$/) : null;
    const start = quarter ? Date.UTC(Number(quarter[1]), (Number(quarter[2]) - 1) * 3, 1) : null;
    const nextStart = quarter ? Date.UTC(Number(quarter[1]), Number(quarter[2]) * 3, 1) : null;
    const time = mode === "analysis" ? item.order : start ?? Date.parse(item.exact_date || item.period_key);
    return { ...item, i, time, end: nextStart === null ? time : nextStart - 86400000, nextStart, numeric: item.value === null ? null : Number(item.value) };
  }).filter((item) => Number.isFinite(item.time)).sort((a,b) => a.time-b.time);
  const known = displayed.filter((item): item is typeof item & {numeric:number} => item.numeric !== null && Number.isFinite(item.numeric));
  if (!known.length) return <Empty label="当前筛选下暂无可绘制的趋势数据" />;
  const current = known.find((item) => item.i === index) || known.filter((item) => item.observation_type === "actual").at(-1) || known.at(-1)!; const values = known.map((item) => item.numeric); const min = Math.min(0, ...values); const max = Math.max(...values); const span = max - min || 1; const h = Math.max(210, Math.min(300, width * .34)); const left = 52, right = 28, top = 28, bottom = 42; const firstTime = Math.min(...displayed.map((item)=>item.time)); const lastTime = Math.max(...displayed.map((item)=>item.end)); const x = (time:number) => left + (time-firstTime) / (lastTime-firstTime || 1) * (width-left-right); const y = (value:number) => top + (max-value) / span * (h-top-bottom); const isRatio = unit === "比例";
  const byObservation = (name:string) => {
    const points=displayed.filter((item) => item.observation_type === name); let penDown=false;
    return points.map((item, position) => {
      if(item.numeric === null || !Number.isFinite(item.numeric)){penDown=false;return "";}
      if(name === "target" && item.nextStart !== null){
        const previous=points[position-1]; const adjacent=penDown && previous?.nextStart===item.time;
        penDown=true;
        return `${adjacent ? `H${x(item.time)}V${y(item.numeric)}` : `M${x(item.time)},${y(item.numeric)}`}H${x(item.end)}`;
      }
      const command=penDown ? "L" : "M"; penDown=true; return `${command}${x(item.time)},${y(item.numeric)}`;
    }).join(" ");
  };
  const read = (i:number) => { if (known.some((item)=>item.i===i)) setIndex(i); };
  const ticks = displayed.filter((item)=>item.observation_type!=="target").filter((item,i,rows)=>rows.findIndex((row)=>row.time===item.time)===i);
  const visibleTicks: typeof ticks = [];
  const minTickGap = Math.max(62,(width-left-right)/(width < 520 ? 3 : 6));
  for(const tick of ticks){if(mode === "analysis" || !visibleTicks.length || x(tick.time)-x(visibleTicks.at(-1)!.time)>=minTickGap)visibleTicks.push(tick);}
  const lastTick=ticks.at(-1);
  if(lastTick && visibleTicks.at(-1)!==lastTick){
    if(visibleTicks.length>1 && x(lastTick.time)-x(visibleTicks.at(-1)!.time)<minTickGap)visibleTicks.pop();
    visibleTicks.push(lastTick);
  }
  const visibleTickTimes=new Set(visibleTicks.map((item)=>item.time));
  const kinds = (["actual","target","forecast"] as const).filter((kind)=>known.some((item)=>item.observation_type===kind));
  const valueLabel = (value:string|number|null) => isRatio ? managementPercent(value === null ? null : String(value)) : managementNumber(value);
  return <div ref={ref} className="management-chart"><div className="management-chart-readout"><span>{current.label}</span><strong>{valueLabel(current.value)} <small>{unit}</small></strong></div><div className="management-legend">{kinds.map((kind)=><span key={kind} className={kind}>{{actual:"实际 Actual",target:"目标 Target",forecast:"预测 Forecast"}[kind]}</span>)}{mode === "analysis" && <span>四快照等距展示，日期间隔不同</span>}</div><svg viewBox={`0 0 ${width} ${h}`} role="img" aria-label={`${mode === "overview" ? "Actual Target Forecast 趋势，按实际日期间隔" : "四快照等距趋势"}，单位 ${unit}`} onPointerMove={(event) => { const box = event.currentTarget.getBoundingClientRect(); const pointer=(event.clientX-box.left)*width/box.width; const closest=known.reduce((picked,item)=>Math.abs(x(item.time)-pointer)<Math.abs(x(picked.time)-pointer)?item:picked,known[0]); setIndex(closest.i); }}>
    {[0,.5,1].map((ratio) => <g key={ratio}><line className="management-gridline" x1={left} x2={width-right} y1={top+(h-top-bottom)*ratio} y2={top+(h-top-bottom)*ratio}/><text x="2" y={top+(h-top-bottom)*ratio+4}>{valueLabel(max-span*ratio)}</text></g>)}
    {kinds.map((kind) => <path key={kind} className={`management-line ${kind}`} d={byObservation(kind)} fill="none" />)}
    {known.map((item) => <g key={`${item.period_key}-${item.observation_type}`}><circle className={`management-point ${item.observation_type} ${current.i === item.i ? "selected" : ""}`} tabIndex={0} role="button" aria-label={`${item.label} ${item.observation_type} ${valueLabel(item.value)} ${unit}`} onFocus={() => read(item.i)} onClick={() => read(item.i)} cx={x(item.time)} cy={y(item.numeric)} r={current.i === item.i ? 4.5 : 3.5} /><title>{`${item.label} ${valueLabel(item.value)} ${unit}`}</title></g>)}
    {ticks.map((item, i) => <text key={item.time} className="management-x-label" x={x(item.time)} y={h-11} textAnchor={i===0 ? "start" : i===ticks.length-1 ? "end" : "middle"}>{visibleTickTimes.has(item.time) ? (mode === "analysis" ? item.label.split(" ")[0] : (item.exact_date || item.label).slice(0,7)) : ""}</text>)}
  </svg></div>;
}

function ManagementAnalysis({ versionId, initialSelection }: { versionId: string;initialSelection?:Partial<Omit<A.ManagementAnalysisQuery,"version_id">> }) {
  const { catalog, error: catalogError, reload: reloadCatalog } = useCatalog(versionId);
  const [data, setData] = useState<A.ManagementAnalysis>(); const [error, setError] = useState<unknown>();
  const requestVersion = useRef(0);
  const [currentAlias, setCurrentAlias] = useState(initialSelection?.current_alias || "CURRENT"); const [baselineAlias, setBaselineAlias] = useState(initialSelection?.baseline_alias || "YEAR_START"); const [line, setLine] = useState(initialSelection?.business_line_id || ""); const [form, setForm] = useState(initialSelection?.material_form || "ALL");
  const load = () => { const request = ++requestVersion.current; setError(undefined); setData(undefined); return A.getManagementAnalysis({version_id:versionId, current_alias:currentAlias, baseline_alias:baselineAlias, business_line_id:line || undefined, material_form:form}).then((x) => request === requestVersion.current && setData(x.data)).catch((reason) => request === requestVersion.current && setError(reason)); };
  useEffect(() => { setData(undefined); setError(undefined); load(); }, [versionId, currentAlias, baselineAlias, line, form]);
  if (catalogError) return <ErrorState error={catalogError} retry={reloadCatalog} />; if (!catalog) return <Loading label="正在读取分析口径" />;
  const makeSeries = (values: {alias:string;exact_date:string;value?:string|null;amount?:string|null}[]) => values.map((item, order) => ({period_key:item.alias,label:catalog.snapshot_aliases.find((snapshot)=>snapshot.alias===item.alias)?.label || item.exact_date,order,value:item.value ?? item.amount ?? null,observation_type:"actual"}));
  return <>
    <ManagementHeader catalog={catalog} versionId={versionId} detailAmount />
    <section className="management-page-head"><div><p className="management-kicker">四时点诊断</p><h2>明细分析</h2><p>比较库存规模、长库龄与业务线变化，筛选后的各组件使用同一数据范围。</p></div></section>
    <section className="management-controls" aria-label="明细分析筛选">
      <label>当前快照<select value={currentAlias} onChange={(e) => setCurrentAlias(e.target.value)}>{catalog.snapshot_aliases.map((item) => <option key={item.alias} value={item.alias}>{item.label}</option>)}</select></label>
      <label>比较基期<select value={baselineAlias} onChange={(e) => setBaselineAlias(e.target.value)}>{catalog.snapshot_aliases.map((item) => <option key={item.alias} value={item.alias}>{item.label}</option>)}</select></label>
      <label>业务线<select value={line} onChange={(e) => setLine(e.target.value)}><option value="">全部业务线</option>{catalog.business_lines.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
      <label>物料形态<select value={form} onChange={(e) => setForm(e.target.value)}>{catalog.material_forms.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
    </section>
    {error ? <ErrorState error={error} retry={load} /> : !data ? <Loading /> : <>
      <div className="management-selection"><strong>{catalog.snapshot_aliases.find((item)=>item.alias===data.selection.current_alias)?.label || data.selection.current_alias}</strong><span>对比 {catalog.snapshot_aliases.find((item)=>item.alias===data.selection.baseline_alias)?.label || data.selection.baseline_alias}</span><span>金额单位：{data.summary.unit}</span></div>
      <div className="management-summary-grid">
        <ManagementSummary label="库存金额" value={data.summary.inventory_amount} delta={data.summary.inventory_delta} unit={data.summary.unit} />
        <ManagementSummary label=">180 天金额" value={data.summary.over_180_amount} delta={data.summary.over_180_delta} unit={data.summary.unit} />
        <ManagementSummary label=">180 天占比" value={data.summary.over_180_share} displayValue={managementPercent(data.summary.over_180_share)} delta={data.summary.over_180_share_delta} displayDelta={data.summary.over_180_share_delta === null ? "—" : `${(Number(data.summary.over_180_share_delta) * 100).toFixed(1)} 个百分点`} />
        <ManagementSummary label="规则风险金额" value={data.summary.policy_risk_amount} unit={data.summary.unit} note={data.summary.policy_risk_amount === null ? (data.summary.risk_evaluation === "unclassified" ? "规则待确认 / 无法分类" : "暂无数据") : "按演示规则命中"} />
      </div>
      <div className="management-three-charts">
        <section className="management-panel"><h3>库存金额 · 四时点</h3><ManagementChart mode="analysis" series={makeSeries(data.amount_trend)} unit={data.summary.unit} /></section>
        <section className="management-panel"><h3>&gt;180 天金额 · 四时点</h3><ManagementChart mode="analysis" series={makeSeries(data.over_180_trend)} unit={data.summary.unit} /></section>
        <section className="management-panel"><h3>&gt;180 天占比 · 四时点</h3><ManagementChart mode="analysis" series={data.over_180_trend.map((item, order) => ({period_key:item.alias,label:catalog.snapshot_aliases.find((snapshot)=>snapshot.alias===item.alias)?.label || item.exact_date,order,value:item.share,observation_type:"actual"}))} unit="比例" /></section>
      </div>
      <section className="management-panel"><div className="management-panel-title"><div><h3>业务线周转</h3><p>预计算的业务线事实，不跨业务线相加或加权。</p></div><Badge tone="muted">预计算口径</Badge></div><div className="management-breakdown">{data.turnover_facts.filter((item)=>item.business_line_id!=="GROUP").map((item) => <article key={item.business_line_id}><span>{catalog.business_lines.find((line)=>line.id===item.business_line_id)?.label || item.business_line_label}</span><strong>{managementNumber(item.current)} <small>{item.unit}</small></strong><small>较基期 {managementDelta(item.delta, item.unit)} · {coverageLabel(item.coverage_state)}</small></article>)}{!data.turnover_facts.length && <Empty />}</div></section>
      <div className="management-breakdowns"><ManagementBreakdown title="物料形态构成" rows={data.material_form_breakdown.map((item) => ({...item, label:catalog.material_forms.find((form)=>form.id===item.key)?.label || item.label, subtitle:`>180 ${managementNumber(item.over_180_amount)}；规则风险 ${item.policy_risk_amount === null ? "规则待确认" : managementNumber(item.policy_risk_amount)}`}))} unit={data.summary.unit}/><ManagementBreakdown title="业务线构成" rows={data.business_line_breakdown.map((item) => ({...item, subtitle:`>180 ${managementNumber(item.over_180_amount)}；${coverageLabel(item.coverage_state)}`}))} unit={data.summary.unit}/></div>
      <p className="management-coverage">覆盖状态：当前 {coverageLabel(data.coverage.current_state)}（未知金额 {data.coverage.current_unknown_amount_count} 行）；基期 {coverageLabel(data.coverage.baseline_state)}（未知金额 {data.coverage.baseline_unknown_amount_count} 行）。</p>
    </>}
  </>;
}

function ManagementSummary({ label, value, delta, unit, note, displayValue, displayDelta }: {label:string;value:string|null;delta?:string|null;unit?:string;note?:string;displayValue?:string;displayDelta?:string}) { return <article className="management-summary"><span>{label}</span><strong>{displayValue ?? managementNumber(value)} {unit && <small>{unit}</small>}</strong>{delta !== undefined && <small>较基期 {displayDelta ?? managementDelta(delta, unit)}</small>}{note && <small>{note}</small>}</article>; }

function ManagementBreakdown({title, rows, unit}: {title:string;rows:{key:string;label:string;inventory_amount:string|null;share:string|null;subtitle:string}[];unit:string}) { const maximum=Math.max(...rows.map((item)=>Number(item.inventory_amount)||0),1); return <section className="management-panel"><h3>{title}</h3><div className="management-breakdown-bars">{rows.map((item)=><div key={item.key}><span>{item.label}</span><b><i style={{width:`${(Number(item.inventory_amount)||0)/maximum*100}%`}}/></b><strong>{managementNumber(item.inventory_amount)} <small>{unit}</small></strong><small>{managementPercent(item.share)} · {item.subtitle}</small></div>)}{!rows.length&&<Empty/>}</div></section>; }

const agingColumns = ["D0_7","D8_14","D15_30","D31_60","D61_90","D91_180","D181_PLUS","UNKNOWN"] as const;
const agingNames: Record<(typeof agingColumns)[number], string> = {D0_7:"0–7天",D8_14:"8–14天",D15_30:"15–30天",D31_60:"31–60天",D61_90:"61–90天",D91_180:"91–180天",D181_PLUS:">180天",UNKNOWN:"未知"};

function ManagementTable({ versionId }: { versionId:string }) {
  const {catalog, error:catalogError, reload:reloadCatalog}=useCatalog(versionId); const [root,setRoot]=useState<A.ManagementInventoryTable>(); const [children,setChildren]=useState<Record<string,A.ManagementInventoryRow[]>>({}); const [expanded,setExpanded]=useState<Set<string>>(new Set()); const [error,setError]=useState<unknown>(); const [loading,setLoading]=useState(false);
  const requestVersion=useRef(0); const expansionVersion=useRef(0);
  const [snapshot,setSnapshot]=useState("CURRENT"), [line,setLine]=useState(""), [form,setForm]=useState("ALL"), [risk,setRisk]=useState<A.ManagementTableQuery["risk_view"]>("all"), [search,setSearch]=useState(""), [sortBy,setSortBy]=useState<A.ManagementTableQuery["sort_by"]>("inventory_amount"), [sortDir,setSortDir]=useState<A.ManagementTableQuery["sort_dir"]>("desc"), [measure,setMeasure]=useState<"amount"|"quantity">("amount");
  const query = (parent_key?:string):A.ManagementTableQuery => ({version_id:versionId,snapshot_alias:snapshot,business_line_id:line||undefined,material_form:form,risk_view:risk,search:search||undefined,sort_by:sortBy,sort_dir:sortDir,parent_key,page:1,size:100});
  const loadRoot=()=>{const request=++requestVersion.current; ++expansionVersion.current; setLoading(true);setError(undefined);setChildren({});setExpanded(new Set());return A.getManagementInventoryTable(query()).then((x)=>{if(request===requestVersion.current)setRoot(x.data);}).catch((reason)=>{if(request===requestVersion.current)setError(reason);}).finally(()=>{if(request===requestVersion.current)setLoading(false);});};
  useEffect(()=>{setRoot(undefined);loadRoot();return()=>{++requestVersion.current;++expansionVersion.current;};},[versionId,snapshot,line,form,risk,search,sortBy,sortDir]);
  const collapseAll=()=>{++expansionVersion.current;setExpanded(new Set());};
  const expand=async(row:A.ManagementInventoryRow)=>{
    if(!row.has_children || loading)return;
    const request=requestVersion.current; const expansion=expansionVersion.current;
    const valid=()=>request===requestVersion.current && expansion===expansionVersion.current;
    if(expanded.has(row.row_key)){++expansionVersion.current;setExpanded((previous)=>{const next=new Set(previous);next.delete(row.row_key);return next;});return;}
    try {let rows=children[row.row_key];if(!rows){rows=(await A.getManagementInventoryTable(query(row.row_key))).data.rows;if(!valid())return;setChildren((old)=>({...old,[row.row_key]:rows!}));}if(valid())setExpanded((previous)=>new Set(previous).add(row.row_key));}catch(reason){if(valid())setError(reason);}
  };
  const expandAll=async()=>{
    if(!root || loading)return;
    const request=requestVersion.current; const expansion=++expansionVersion.current;
    const valid=()=>request===requestVersion.current && expansion===expansionVersion.current;
    const loaded={...children}; const keys=new Set<string>();
    const collect=async(rows:A.ManagementInventoryRow[])=>{for(const row of rows){if(!valid())return;if(!row.has_children)continue;keys.add(row.row_key);let next=loaded[row.row_key];if(!next){next=(await A.getManagementInventoryTable(query(row.row_key))).data.rows;if(!valid())return;loaded[row.row_key]=next;}await collect(next);}};
    try{await collect(root.rows);if(valid()){setChildren(loaded);setExpanded(keys);}}catch(reason){if(valid())setError(reason);}
  };
  if(catalogError)return <ErrorState error={catalogError} retry={reloadCatalog}/>;if(!catalog)return <Loading label="正在读取表格口径"/>;
  const flat=(rows:A.ManagementInventoryRow[], depth=0):{row:A.ManagementInventoryRow;depth:number}[]=>rows.flatMap((row)=>[{row,depth},...(expanded.has(row.row_key)?flat(children[row.row_key]||[],depth+1):[])]);
  const rows=root?flat(root.rows):[]; const value=(row:A.ManagementInventoryRow,key:string)=>measure==="quantity"?row.aging_quantities[key]:row.aging_amounts[key];
  return <><ManagementHeader catalog={catalog} versionId={versionId} detailAmount/><section className="management-page-head"><div><p className="management-kicker">分层核对</p><h2>库存数据表</h2><p>按业务线 → 项目 → 物料小类服务端展开；金额和数量不在前端重算。</p></div></section>
    <section className="management-controls management-table-controls" aria-label="库存数据表筛选"><label>快照<select value={snapshot} onChange={(e)=>setSnapshot(e.target.value)}>{catalog.snapshot_aliases.map((item)=><option key={item.alias} value={item.alias}>{item.label}</option>)}</select></label><label>业务线<select value={line} onChange={(e)=>setLine(e.target.value)}><option value="">全部业务线</option>{catalog.business_lines.map((item)=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label><label>物料形态<select value={form} onChange={(e)=>setForm(e.target.value)}>{catalog.material_forms.map((item)=><option key={item.id} value={item.id}>{item.label}</option>)}</select></label><label>风险范围<select value={risk} onChange={(e)=>setRisk(e.target.value as typeof risk)}><option value="all">全部</option><option value="over_180">&gt;180 天</option><option value="policy_hit">规则命中</option><option value="unclassified">未分类</option></select></label><label>库龄展示<select value={measure} onChange={(e)=>setMeasure(e.target.value as typeof measure)}><option value="amount">金额</option><option value="quantity">数量</option></select></label><label>搜索<input value={search} onChange={(e)=>setSearch(e.target.value)} placeholder="业务线、项目或物料小类"/></label><label>排序<select value={`${sortBy}-${sortDir}`} onChange={(e)=>{const [field,direction]=e.target.value.split("-");setSortBy(field as typeof sortBy);setSortDir(direction as typeof sortDir);}}><option value="inventory_amount-desc">库存金额（高到低）</option><option value="inventory_amount-asc">库存金额（低到高）</option><option value="over_180_amount-desc">&gt;180 天金额（高到低）</option><option value="quantity-desc">数量（高到低）</option><option value="name-asc">名称（A–Z）</option></select></label></section>
    <div className="management-table-actions"><button onClick={expandAll} disabled={loading}>展开全部</button><button onClick={collapseAll}>收起全部</button><button onClick={()=>window.open(A.managementExportUrl(query()),"_blank","noopener")}>导出 CSV</button><span>&gt;180 天与规则命中为两种独立口径；规则待确认将显示未分类。</span></div>
    {error?<ErrorState error={error} retry={loadRoot}/>:loading||!root?<Loading/>:<section className="management-panel management-table-panel"><div className="management-table-wrap"><table className="management-table"><thead><tr><th>业务线 / 项目 / 物料小类</th>{agingColumns.map((key)=><th key={key}>{agingNames[key]}</th>)}<th>库存金额</th><th>数量</th><th>&gt;180 天</th><th>规则风险</th><th>状态</th></tr></thead><tbody>{rows.length ? rows.map(({row,depth})=><tr key={row.row_key} className={`level-${row.level}`}><td style={{paddingLeft:`${14+depth*24}px`}}>{row.has_children?<button className="tree-toggle" onClick={()=>expand(row)} aria-expanded={expanded.has(row.row_key)} aria-label={`展开 ${row.label}`}>{expanded.has(row.row_key)?"−":"+"}</button>:<span className="tree-spacer"/>}{row.label}</td>{agingColumns.map((key)=><td className="num" key={key}>{managementNumber(value(row,key))}</td>)}<td className="num">{managementNumber(row.inventory_amount)}</td><td className="num">{managementNumber(row.quantity)}<small>{row.quantity === null ? quantityStatusLabel(row.quantity_status) : row.quantity_unit || ""}</small></td><td className="num">{managementNumber(row.over_180_amount)}</td><td className="num">{row.policy_risk_amount===null?"规则待确认":managementNumber(row.policy_risk_amount)}</td><td><small>{riskLabel(row.risk_evaluation)}</small><small>{coverageLabel(row.coverage_state)}</small></td></tr>) : <tr><td className="management-table-empty" colSpan={14}>当前筛选无记录</td></tr>}</tbody><tfoot><tr><th>当前筛选总计</th>{agingColumns.map((key)=><th className="num" key={key}>{managementNumber(measure==="quantity"?root.totals.aging_quantities[key]:root.totals.aging_amounts[key])}</th>)}<th className="num">{managementNumber(root.totals.inventory_amount)}</th><th className="num">{managementNumber(root.totals.quantity)}</th><th className="num">{managementNumber(root.totals.over_180_amount)}</th><th className="num">{root.totals.policy_risk_amount===null?"规则待确认":managementNumber(root.totals.policy_risk_amount)}</th><th>{coverageLabel(root.totals.coverage_state)}</th></tr></tfoot></table></div><p className="management-table-foot">共 {root.total} 个根层节点。金额单位：{root.totals.unit}；数量为 null 时表示单位或可加性不一致，不以 0 替代。</p></section>}</>;
}

function SourcesTopics() { return <><section className="management-page-head"><div><p className="management-kicker">辅助入口</p><h2>来源与专题</h2><p>旧 V4 转录、MWD、数据版本和合成导入仍保留在这里；它们不与当前合成管理演示混合。</p></div></section><div className="management-source-note"><Badge tone="orange">SOURCE_TRANSCRIPTION_DRAFT</Badge><span>历史转录初稿只用于来源核对；当前主流程的数据证据等级为 SYNTHETIC_MANAGEMENT_DEMO。</span></div><LegacyWorkspace/></>; }
