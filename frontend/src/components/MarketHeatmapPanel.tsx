import { useMemo, useState } from "react";
import type { WatchlistRow } from "../types";
import mib30Sectors from "../data/mib30_sectors.json";

type PeriodKey = "PCTV_1D" | "PCTV_5D" | "PCTV_10D" | "PCTV_30D" | "PCTV_180D";
type ViewMode = "performance" | "technical";
type LayoutMode = "sections" | "sectorGrid";
type Props = { market: string; rows: WatchlistRow[]; alertMap: Record<string, boolean>; loading?: boolean; error?: string; onChart: (row: WatchlistRow) => void };

const PERIODS: Array<{ key: PeriodKey; label: string }> = [
  { key: "PCTV_1D", label: "1D" }, { key: "PCTV_5D", label: "5D" }, { key: "PCTV_10D", label: "10D" },
  { key: "PCTV_30D", label: "30D" }, { key: "PCTV_180D", label: "180D" },
];
const SECTORS = mib30Sectors as Record<string, string>;

function num(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") { const parsed = Number(value.replace(",", ".").trim()); return Number.isFinite(parsed) ? parsed : null; }
  return null;
}
function bool(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["true", "1", "yes", "si", "sì"].includes(normalized)) return true;
    if (["false", "0", "no"].includes(normalized)) return false;
  }
  return null;
}
const tickerOf = (row: WatchlistRow) => String(row.Ticker ?? "").trim().toUpperCase();
const alertKey = (market: string, ticker: string) => `${market.trim().toUpperCase()}::${ticker.trim().toUpperCase()}`;
const isUptrend = (row: WatchlistRow) => String(row.Signal6 ?? "").toLowerCase().startsWith("uptrend");
function isAboveSar(row: WatchlistRow): boolean {
  const flag = bool(row.SAR_Above_Price);
  if (flag !== null) return !flag;
  const sar = num(row.SAR); const close = num(row.Close);
  return sar !== null && close !== null && close > sar;
}
function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b); const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}
function technicalScore(row: WatchlistRow): number {
  let score = Number(isAboveSar(row)) + Number(isUptrend(row)) + Number((num(row.ADX) ?? -Infinity) >= 20);
  const plus = num(row.PLUS_DI); const minus = num(row.MINUS_DI);
  if (plus !== null && minus !== null && plus > minus) score += 1;
  return score;
}
function isDirectionalPositive(row: WatchlistRow): boolean {
  const plus = num(row.PLUS_DI); const minus = num(row.MINUS_DI);
  return plus !== null && minus !== null && plus > minus;
}
function hasRecentPattern(row: WatchlistRow): boolean {
  return [row.Pattern_S2_Days_Ago, row.Pattern_S3_Days_Ago, row.Pattern_S4_Days_Ago, row.Pattern_Combined_Days_Ago, row.Pattern_Days_Ago]
    .some((value) => { const days = num(value); return days !== null && days >= 0 && days <= 3; });
}

export default function MarketHeatmapPanel({ market, rows, alertMap, loading, error, onChart }: Props) {
  const [period, setPeriod] = useState<PeriodKey>("PCTV_1D");
  const [mode, setMode] = useState<ViewMode>("performance");
  const [layout, setLayout] = useState<LayoutMode>("sectorGrid");
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const isMib = market.toUpperCase() === "MIB30";
  const mappedRows = useMemo(() => isMib ? rows.filter((row) => Boolean(SECTORS[tickerOf(row)])) : rows, [isMib, rows]);
  const groups = useMemo(() => {
    const result = new Map<string, WatchlistRow[]>();
    mappedRows.forEach((row) => { const sector = isMib ? SECTORS[tickerOf(row)] : "Tutti i titoli"; result.set(sector, [...(result.get(sector) ?? []), row]); });
    return [...result.entries()].sort(([a], [b]) => a.localeCompare(b, "it"));
  }, [isMib, mappedRows]);
  const visibleGroups = selectedSector ? groups.filter(([sector]) => sector === selectedSector) : groups;
  const stats = useMemo(() => {
    const values = mappedRows.map((row) => num(row[period])).filter((value): value is number => value !== null);
    const sortedAbs = values.map(Math.abs).sort((a, b) => a - b);
    return {
      scale: Math.max(sortedAbs[Math.max(0, Math.ceil(sortedAbs.length * 0.9) - 1)] ?? 0, 0.25),
      positive: values.filter((value) => value > 0).length, negative: values.filter((value) => value < 0).length,
      aboveSar: mappedRows.filter(isAboveSar).length, uptrend: mappedRows.filter(isUptrend).length,
      alerts: mappedRows.filter((row) => alertMap[alertKey(String(row.WL_Source_Market ?? market), tickerOf(row))]).length,
    };
  }, [alertMap, mappedRows, market, period]);

  if (loading) return <p>Carico heatmap {market}...</p>;
  if (error) return <p className="err">{error}</p>;
  if (!rows.length) return <p>Nessun titolo disponibile per la heatmap di {market}.</p>;
  const pct = (value: number) => mappedRows.length ? Math.round(value / mappedRows.length * 100) : 0;

  return <section className="heatmap-panel">
    <div className="heatmap-header">
      <div><h2>Heatmap · {market}{isMib ? " per settore" : ""}</h2><div className="muted">Dati dall'ultimo Excel di analisi. Clicca un titolo per aprire il grafico.</div></div>
      <div className="heatmap-controls">
        <div className="heatmap-periods">
          <button className={mode === "performance" ? "quick-bar active" : "quick-bar"} onClick={() => setMode("performance")}>Performance</button>
          <button className={mode === "technical" ? "quick-bar active" : "quick-bar"} onClick={() => setMode("technical")}>Trend tecnico</button>
        </div>
        {isMib ? <div className="heatmap-periods heatmap-layout-switch" aria-label="Formato heatmap">
          <button className={layout === "sections" ? "quick-bar active" : "quick-bar"} onClick={() => setLayout("sections")}>☰ Sezioni</button>
          <button className={layout === "sectorGrid" ? "quick-bar active" : "quick-bar"} onClick={() => setLayout("sectorGrid")}>▦ Griglia settoriale</button>
        </div> : null}
        {mode === "performance" ? <div className="heatmap-periods">{PERIODS.map((item) => <button key={item.key} className={period === item.key ? "quick-bar active" : "quick-bar"} onClick={() => setPeriod(item.key)}>{item.label}</button>)}</div> : null}
      </div>
    </div>
    <div className="heatmap-summary">
      <div><strong>{pct(stats.positive)}%</strong><span>In rialzo</span></div><div><strong>{pct(stats.negative)}%</strong><span>In ribasso</span></div>
      <div><strong>{pct(stats.aboveSar)}%</strong><span>Sopra SAR</span></div><div><strong>{pct(stats.uptrend)}%</strong><span>Alligator Uptrend</span></div>
      <div><strong>{stats.alerts}</strong><span>Alert attivi</span></div>
    </div>
    {isMib ? <div className="sector-filter-row">
      <button className={!selectedSector ? "sector-filter active" : "sector-filter"} onClick={() => setSelectedSector(null)}>Tutti i settori</button>
      {groups.map(([sector, items]) => <button key={sector} className={selectedSector === sector ? "sector-filter active" : "sector-filter"} onClick={() => setSelectedSector(selectedSector === sector ? null : sector)}>{sector} <small>{items.length}</small></button>)}
    </div> : null}
    <div className={`sector-groups ${layout === "sectorGrid" && isMib ? "grid-layout" : "sections-layout"}`}>{visibleGroups.map(([sector, sectorRows]) => {
      const values = sectorRows.map((row) => num(row[period])).filter((value): value is number => value !== null);
      const sectorMedian = median(values);
      const adxMedian = median(sectorRows.map((row) => num(row.ADX)).filter((value): value is number => value !== null));
      const sorted = [...sectorRows].sort((a, b) => (num(b[period]) ?? -Infinity) - (num(a[period]) ?? -Infinity));
      const sectorAlerts = sectorRows.filter((row) => alertMap[alertKey(String(row.WL_Source_Market ?? market), tickerOf(row))]).length;
      return <article className="sector-group" key={sector}>
        <div className="sector-heading"><button onClick={() => isMib && setSelectedSector(selectedSector === sector ? null : sector)} title="Mostra solo questo settore"><strong>{sector}</strong><span>{sectorRows.length} titoli</span></button>
          <div className={`sector-median ${(sectorMedian ?? 0) >= 0 ? "positive" : "negative"}`}>Mediana {sectorMedian === null ? "n/d" : `${sectorMedian >= 0 ? "+" : ""}${sectorMedian.toFixed(2)}%`}</div></div>
        <details className="sector-details"><summary>Riepilogo settore</summary><div>
          <span>Positivi <b>{sectorRows.filter((row) => (num(row[period]) ?? 0) > 0).length}/{sectorRows.length}</b></span><span>Sopra SAR <b>{sectorRows.filter(isAboveSar).length}/{sectorRows.length}</b></span>
          <span>Alligator Up <b>{sectorRows.filter(isUptrend).length}/{sectorRows.length}</b></span><span>ADX mediano <b>{adxMedian?.toFixed(1) ?? "n/d"}</b></span>
          <span>Pattern ≤3gg <b>{sectorRows.filter(hasRecentPattern).length}</b></span><span>Alert <b>{sectorAlerts}</b></span>
          <span>Migliore <b>{tickerOf(sorted[0])} {num(sorted[0]?.[period])?.toFixed(2) ?? "n/d"}%</b></span><span>Peggiore <b>{tickerOf(sorted[sorted.length - 1] ?? {})} {num(sorted[sorted.length - 1]?.[period])?.toFixed(2) ?? "n/d"}%</b></span>
        </div></details>
        <div className="heatmap-grid">{sectorRows.map((row) => {
          const ticker = tickerOf(row) || "-"; const value = num(row[period]); const score = technicalScore(row);
          const intensity = value === null ? 0 : Math.min(Math.abs(value) / stats.scale, 1); const alpha = 0.18 + intensity * 0.7;
          const background = mode === "technical" ? ["#991b1b", "#c2410c", "#a16207", "#15803d", "#047857"][score] : value === null ? "rgba(100,116,139,.28)" : value >= 0 ? `rgba(22,163,74,${alpha})` : `rgba(220,38,38,${alpha})`;
          const sourceMarket = String(row.WL_Source_Market ?? market); const hasAlert = Boolean(alertMap[alertKey(sourceMarket, ticker)]);
          const variation = value === null ? "n/d" : `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
          return <button key={`${sourceMarket}-${ticker}`} className={hasAlert ? "heatmap-tile has-alert" : "heatmap-tile"} style={{ background }} onClick={() => onChart(row)} title={`${String(row.Name ?? ticker)} · ${variation} · clicca per il grafico`}>
            <span className="heatmap-ticker">{ticker} <small className={value !== null && value >= 0 ? "positive" : "negative"}>{variation}</small></span><span className="heatmap-value">{mode === "technical" ? `${score}/4 conferme` : variation}</span>
            <span className="heatmap-phase">{mode === "technical"
              ? `SAR ${isAboveSar(row) ? "✓" : "✕"} · Allig. ${isUptrend(row) ? "✓" : "✕"} · ADX ${(num(row.ADX) ?? -Infinity) >= 20 ? "✓" : "✕"} ${num(row.ADX)?.toFixed(0) ?? "-"} · DI ${isDirectionalPositive(row) ? "✓" : "✕"}`
              : String(row.Market_Phase ?? "-")}</span>{hasAlert ? <span className="heatmap-alert">🔔</span> : null}
          </button>;
        })}</div>
      </article>;
    })}</div>
    {isMib && rows.length > mappedRows.length ? <p className="heatmap-excluded">{rows.length - mappedRows.length} elementi non appartenenti al mapping MIB esclusi dalla vista settoriale.</p> : null}
    <div className="heatmap-legend"><span>{mode === "technical" ? "0 conferme" : "Ribasso forte"}</span><i className="legend-red"/><i className="legend-neutral"/><i className="legend-green"/><span>{mode === "technical" ? "4 conferme" : "Rialzo forte"}</span></div>
  </section>;
}
