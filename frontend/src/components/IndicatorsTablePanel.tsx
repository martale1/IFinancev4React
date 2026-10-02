import { useMemo, useState } from "react";
import type { WatchlistRow } from "../types";

type Column = {
  key: string;
  label: string;
  kind?: "text" | "number" | "percent" | "date";
  digits?: number;
  group?: string;
};

type Props = {
  rows: WatchlistRow[];
  market: string;
  loading?: boolean;
  error?: string;
  sourcePath?: string | null;
  sourceUpdatedAt?: string | null;
  onChart: (row: WatchlistRow) => void;
  onAi: (row: WatchlistRow) => void;
};

const COLUMNS: Column[] = [
  { key: "Ticker", label: "Ticker", kind: "text", group: "Titolo" },
  { key: "Name", label: "Nome", kind: "text", group: "Titolo" },
  { key: "Date", label: "Data", kind: "date", group: "Titolo" },
  { key: "Entry_Signal", label: "Segnale", kind: "text", group: "Scenario" },
  { key: "Market_Phase", label: "Scenario", kind: "text", group: "Scenario" },
  { key: "Trend_Phase_Detail", label: "Dettaglio trend", kind: "text", group: "Scenario" },
  { key: "Close", label: "Prezzo", kind: "number", digits: 3, group: "Prezzo" },
  { key: "PCTV_1D", label: "1D", kind: "percent", group: "Performance" },
  { key: "PCTV_5D", label: "5D", kind: "percent", group: "Performance" },
  { key: "PCTV_10D", label: "10D", kind: "percent", group: "Performance" },
  { key: "PCTV_30D", label: "30D", kind: "percent", group: "Performance" },
  { key: "PCTV_180D", label: "180D", kind: "percent", group: "Performance" },
  { key: "TECH_SCORE", label: "TECH", kind: "number", digits: 0, group: "Score" },
  { key: "TECH_STRUCTURE", label: "Struttura", kind: "number", digits: 0, group: "Score" },
  { key: "TECH_MOMENTUM", label: "Momentum", kind: "number", digits: 0, group: "Score" },
  { key: "TECH_PARTICIPATION", label: "Partecipazione", kind: "number", digits: 0, group: "Score" },
  { key: "TECH_EXTENSION_PENALTY", label: "Penalità", kind: "number", digits: 0, group: "Score" },
  { key: "RSI", label: "RSI", kind: "number", digits: 1, group: "Oscillatori" },
  { key: "Stoch_K", label: "Stoch K", kind: "number", digits: 1, group: "Oscillatori" },
  { key: "Stoch_D", label: "Stoch D", kind: "number", digits: 1, group: "Oscillatori" },
  { key: "Stoch_KvsD", label: "K-D", kind: "number", digits: 2, group: "Oscillatori" },
  { key: "Williams_R", label: "Will %R", kind: "number", digits: 1, group: "Oscillatori" },
  { key: "MACD", label: "MACD", kind: "number", digits: 3, group: "MACD" },
  { key: "MACD_Signal", label: "Signal", kind: "number", digits: 3, group: "MACD" },
  { key: "MACD_Hist", label: "Hist", kind: "number", digits: 3, group: "MACD" },
  { key: "MACD_vs_Signal", label: "MACD-Signal", kind: "number", digits: 3, group: "MACD" },
  { key: "ADX", label: "ADX", kind: "number", digits: 1, group: "DMI" },
  { key: "PLUS_DI", label: "DI+", kind: "number", digits: 1, group: "DMI" },
  { key: "MINUS_DI", label: "DI-", kind: "number", digits: 1, group: "DMI" },
  { key: "DI_diff", label: "DI diff", kind: "number", digits: 1, group: "DMI" },
  { key: "SIG_MA_SAR", label: "SARMA", kind: "number", digits: 0, group: "Trend" },
  { key: "Signal6", label: "Alligator", kind: "text", group: "Trend" },
  { key: "Signal6_Trend_Days", label: "Alligator giorni", kind: "number", digits: 0, group: "Trend" },
  { key: "EMA_9", label: "EMA9", kind: "number", digits: 3, group: "Medie" },
  { key: "EMA_21", label: "EMA21", kind: "number", digits: 3, group: "Medie" },
  { key: "EMA_30", label: "EMA30", kind: "number", digits: 3, group: "Medie" },
  { key: "EMA_50", label: "EMA50", kind: "number", digits: 3, group: "Medie" },
  { key: "SMA200", label: "SMA200", kind: "number", digits: 3, group: "Medie" },
  { key: "SAR", label: "SAR", kind: "number", digits: 3, group: "Trend" },
  { key: "Volume", label: "Volume", kind: "number", digits: 0, group: "Volume" },
  { key: "Volume_MA20", label: "Vol MA20", kind: "number", digits: 0, group: "Volume" },
  { key: "Vol_Perc_vs_MA20", label: "Vol vs MA20", kind: "percent", group: "Volume" },
  { key: "Liquidity", label: "Liquidità", kind: "text", group: "Volume" },
  { key: "Pattern_Type", label: "Pattern", kind: "text", group: "Pattern" },
  { key: "Pattern_Days_Ago", label: "Pattern giorni", kind: "number", digits: 0, group: "Pattern" },
  { key: "Pattern_S2_Days_Ago", label: "S2 giorni", kind: "number", digits: 0, group: "Pattern" },
  { key: "Pattern_S3_Days_Ago", label: "S3 giorni", kind: "number", digits: 0, group: "Pattern" },
  { key: "Pattern_S4_Days_Ago", label: "S4 giorni", kind: "number", digits: 0, group: "Pattern" },
  { key: "Pattern_S5_Days_Ago", label: "S5 giorni", kind: "number", digits: 0, group: "Pattern" },
  { key: "Pattern_S6_Days_Ago", label: "S6 giorni", kind: "number", digits: 0, group: "Pattern" },
  { key: "Pattern_S7_CONFIRMED_Days_Ago", label: "S7 conf giorni", kind: "number", digits: 0, group: "Pattern" },
  { key: "Pattern_S7_STRONG_Days_Ago", label: "S7 strong giorni", kind: "number", digits: 0, group: "Pattern" },
  { key: "Pattern_S8_Days_Ago", label: "S8 giorni", kind: "number", digits: 0, group: "Pattern" },
  { key: "Pattern_S9_CONFIRMED_Days_Ago", label: "S9 conf giorni", kind: "number", digits: 0, group: "Pattern" },
  { key: "Data_Quality", label: "Qualità dati", kind: "text", group: "Dati" },
  { key: "History_Rows", label: "Storico", kind: "number", digits: 0, group: "Dati" },
];

const GROUPS = ["Tutte", ...Array.from(new Set(COLUMNS.map((column) => column.group ?? "Altro")))];

function numericValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value.replace("%", "").replace(",", "."));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function formatValue(row: WatchlistRow, column: Column): string {
  const value = row[column.key];
  if (value === null || value === undefined || value === "") return "-";
  if (column.kind === "date") return String(value).slice(0, 10);
  const parsed = numericValue(value);
  if (column.kind === "percent") {
    if (parsed === null) return String(value);
    return `${parsed > 0 ? "+" : ""}${parsed.toFixed(2)}%`;
  }
  if (column.kind === "number") {
    if (parsed === null) return String(value);
    return parsed.toLocaleString("it-IT", {
      minimumFractionDigits: column.digits ?? 0,
      maximumFractionDigits: column.digits ?? 0,
    });
  }
  return String(value).replace(/_/g, " ");
}

function valueClass(row: WatchlistRow, column: Column): string {
  const parsed = numericValue(row[column.key]);
  if (parsed === null || parsed === 0) return "";
  if (["PCTV_1D", "PCTV_5D", "PCTV_10D", "PCTV_30D", "PCTV_180D", "MACD_vs_Signal", "MACD_Hist", "DI_diff", "Vol_Perc_vs_MA20"].includes(column.key)) {
    return parsed > 0 ? "positive" : "negative";
  }
  if (column.key === "PLUS_DI") return "positive";
  if (column.key === "MINUS_DI") return "negative";
  return "";
}

function compareRows(a: WatchlistRow, b: WatchlistRow, key: string, dir: "asc" | "desc"): number {
  const av = a[key];
  const bv = b[key];
  const an = numericValue(av);
  const bn = numericValue(bv);
  let result = 0;
  if (an !== null || bn !== null) result = (an ?? Number.NEGATIVE_INFINITY) - (bn ?? Number.NEGATIVE_INFINITY);
  else result = String(av ?? "").localeCompare(String(bv ?? ""), "it", { sensitivity: "base" });
  return dir === "asc" ? result : -result;
}

function hasAnyValue(rows: WatchlistRow[], column: Column): boolean {
  if (["Ticker", "Name", "Date"].includes(column.key)) return true;
  return rows.some((row) => row[column.key] !== null && row[column.key] !== undefined && row[column.key] !== "");
}

function fmtSourceTs(value?: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("it-IT");
}

export default function IndicatorsTablePanel({ rows, market, loading, error, sourcePath, sourceUpdatedAt, onChart, onAi }: Props) {
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState("Tutte");
  const [hideEmpty, setHideEmpty] = useState(true);
  const [sortKey, setSortKey] = useState("Ticker");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const filteredRows = useMemo(() => {
    const term = search.trim().toLowerCase();
    const base = term
      ? rows.filter((row) => `${String(row.Ticker ?? "")} ${String(row.Name ?? "")}`.toLowerCase().includes(term))
      : rows;
    return [...base].sort((a, b) => compareRows(a, b, sortKey, sortDir));
  }, [rows, search, sortKey, sortDir]);

  const columns = useMemo(() => {
    return COLUMNS.filter((column) => {
      if (group !== "Tutte" && column.group !== group) return false;
      if (hideEmpty && !hasAnyValue(rows, column)) return false;
      return true;
    });
  }, [group, hideEmpty, rows]);

  function handleSort(key: string) {
    if (sortKey === key) setSortDir((current) => current === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("asc"); }
  }

  return (
    <section className="indicators-panel">
      <div className="indicators-heading">
        <div>
          <h2>📈 Indicatori calcolati · {market}</h2>
          <p className="muted">Tabella tecnica generata dai valori già calcolati da main.py e salvati nelle analisi del mercato/lista selezionata.</p>
          <p className="source-meta compact">Last update: {fmtSourceTs(sourceUpdatedAt)} · Source: <span className="source-path">{sourcePath ?? "-"}</span></p>
        </div>
        <div className="indicator-stats">
          <strong>{filteredRows.length}</strong>
          <span>ticker visualizzati</span>
        </div>
      </div>

      <div className="indicators-toolbar">
        <label>
          Cerca
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Ticker o nome" />
        </label>
        <label>
          Gruppo colonne
          <select value={group} onChange={(event) => setGroup(event.target.value)}>
            {GROUPS.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="indicator-check">
          <input type="checkbox" checked={hideEmpty} onChange={(event) => setHideEmpty(event.target.checked)} />
          Nascondi colonne vuote
        </label>
      </div>

      {loading ? <p>Carico indicatori...</p> : null}
      {error ? <p className="err">{error}</p> : null}
      {!loading && !error ? (
        <div className="indicators-table-wrap">
          <table className="indicators-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column.key}>
                    <button className={sortKey === column.key ? "table-sort active" : "table-sort"} onClick={() => handleSort(column.key)}>
                      <small>{column.group}</small>
                      {column.label}{sortKey === column.key ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                    </button>
                  </th>
                ))}
                <th>Azioni</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row, index) => (
                <tr key={`${String(row.Ticker ?? "-")}-${index}`}>
                  {columns.map((column) => (
                    <td key={column.key} className={`${column.kind === "number" || column.kind === "percent" ? "numeric" : ""} ${valueClass(row, column)}`}>
                      {formatValue(row, column)}
                    </td>
                  ))}
                  <td className="table-actions sticky-actions">
                    <button className="btn" onClick={() => onChart(row)}>Grafico</button>
                    <button className="btn ghost" onClick={() => onAi(row)}>AI</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!filteredRows.length ? <p className="muted empty-indicators">Nessun ticker trovato con questi filtri.</p> : null}
        </div>
      ) : null}
    </section>
  );
}


