import { useState } from "react";
import type { QuickAlertField, WatchlistRow } from "../types";

type AiAlertInfo = { enabled: boolean; verified: number; total: number };

type Props = {
  rows: WatchlistRow[];
  market: string;
  sortKey: string | null;
  sortDir: "asc" | "desc" | null;
  onSort: (key: string) => void;
  onChart: (row: WatchlistRow) => void;
  onAi: (row: WatchlistRow) => void;
  aiAlertMap: Record<string, AiAlertInfo>;
  aiLevelMap: Record<string, Array<{ verified: boolean }>>;
  alertMap: Record<string, boolean>;
  alertConfigMap: Record<string, { field: QuickAlertField; op: ">" | "<" | "==" | "!="; value: number | string | null }>;
  alertBusyMap: Record<string, boolean>;
  onCreateAlert: (input: { row: WatchlistRow; source_market: string; field: QuickAlertField; op: ">" | "<" | "==" | "!="; value: number | string }) => Promise<string>;
  onRemoveAlert: (input: { row: WatchlistRow; source_market: string }) => Promise<string>;
};

const ALERT_FIELDS: Array<{ value: QuickAlertField; label: string }> = [
  { value: "Close", label: "Prezzo" }, { value: "MACD_vs_Signal", label: "S3" },
  { value: "SIG_MA_SAR", label: "SARMA" }, { value: "RSI", label: "RSI" },
  { value: "Williams_R", label: "Williams %R" }, { value: "Stoch_K", label: "Stocastico K" },
  { value: "ADX", label: "ADX" },
];

function number(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const parsed = Number(String(value ?? "").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

function num(value: unknown, digits = 0): string {
  const parsed = number(value);
  return parsed === null ? "-" : parsed.toLocaleString("it-IT", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function pct(value: unknown): string {
  const parsed = number(value);
  if (parsed === null) return "-";
  return `${parsed > 0 ? "+" : ""}${parsed.toFixed(2)}%`;
}

function pctClass(value: unknown): string {
  const parsed = number(value);
  return parsed === null || parsed === 0 ? "neutral" : parsed > 0 ? "positive" : "negative";
}

function signalClass(value: unknown): string {
  const signal = String(value ?? "ATTENDI").toUpperCase();
  if (signal === "ENTRA") return "enter";
  if (signal === "OSSERVA") return "watch";
  if (signal === "EVITA") return "avoid";
  return "wait";
}

function keyFor(row: WatchlistRow, market: string): string {
  return `${String(row.WL_Source_Market ?? market).trim().toUpperCase()}::${String(row.Ticker ?? "").trim().toUpperCase()}`;
}

export default function WatchlistTable({ rows, market, sortKey, sortDir, onSort, onChart, onAi, aiAlertMap, aiLevelMap, alertMap, alertConfigMap, alertBusyMap, onCreateAlert, onRemoveAlert }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [alertEditor, setAlertEditor] = useState("");
  const [alertField, setAlertField] = useState<QuickAlertField>("Close");
  const [alertOp, setAlertOp] = useState<">" | "<" | "==" | "!=">(">");
  const [alertValue, setAlertValue] = useState("");
  const [alertMessage, setAlertMessage] = useState("");
  const heading = (label: string, key?: string) => key ? (
    <button className={sortKey === key ? "table-sort active" : "table-sort"} onClick={() => onSort(key)}>
      {label}{sortKey === key ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
    </button>
  ) : label;

  function toggleDetails(ticker: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(ticker)) next.delete(ticker); else next.add(ticker);
      return next;
    });
  }

  function toggleAlertEditor(rowKey: string, row: WatchlistRow, key: string) {
    if (alertEditor === rowKey) { setAlertEditor(""); return; }
    const config = alertConfigMap[key];
    setAlertEditor(rowKey);
    setAlertField(config?.field ?? "Close");
    setAlertOp(config?.op ?? ">");
    setAlertValue(String(config?.value ?? row.Close ?? ""));
    setAlertMessage("");
  }

  return (
    <div className="watchlist-table-wrap">
      <table className="watchlist-table">
        <thead><tr>
          <th>{heading("Titolo", "Ticker")}</th>
          <th>Segnale</th>
          <th>{heading("Prezzo", "Close")}</th>
          <th>{heading("1D", "PCTV_1D")}</th>
          <th>{heading("5D", "PCTV_5D")}</th>
          <th>30D</th>
          <th>180D</th>
          <th>{heading("TECH", "TECH_SCORE")}</th>
          <th>{heading("S3", "MACD_vs_Signal")}</th>
          <th>{heading("SARMA", "SIG_MA_SAR")}</th>
          <th>{heading("RSI", "RSI")}</th>
          <th>Scenario</th>
          <th>Liquidità</th>
          <th>Alert AI</th>
          <th>Azioni</th>
        </tr></thead>
        <tbody>{rows.map((row, index) => {
          const ticker = String(row.Ticker ?? "-");
          const rowKey = `${ticker}-${index}`;
          const alertKey = keyFor(row, market);
          const aiAlert = aiAlertMap[alertKey];
          const aiLevels = aiLevelMap[alertKey] ?? [];
          const signal = String(row.Entry_Signal ?? "ATTENDI").toUpperCase();
          const isExpanded = expanded.has(rowKey);
          return [
            <tr key={rowKey} className={isExpanded ? "expanded" : ""}>
              <td className="ticker-cell"><strong>{ticker}</strong><small>{String(row.Name ?? "-")}</small><div className="mobile-watchlist-summary"><span>Prezzo <b>{num(row.Close, 3)}</b></span><span className={pctClass(row.PCTV_1D)}>1D <b>{pct(row.PCTV_1D)}</b></span><span>TECH <b>{num(row.TECH_SCORE)}</b></span><span className={pctClass(row.MACD_vs_Signal)}>S3 <b>{num(row.MACD_vs_Signal)}</b></span><span>RSI <b>{num(row.RSI)}</b></span></div></td>
              <td><span className={`table-signal ${signalClass(signal)}`}>{signal}</span></td>
              <td className="numeric">{num(row.Close, 3)}</td>
              <td className={`numeric ${pctClass(row.PCTV_1D)}`}>{pct(row.PCTV_1D)}</td>
              <td className={`numeric ${pctClass(row.PCTV_5D)}`}>{pct(row.PCTV_5D)}</td>
              <td className={`numeric ${pctClass(row.PCTV_30D)}`}>{pct(row.PCTV_30D)}</td>
              <td className={`numeric ${pctClass(row.PCTV_180D)}`}>{pct(row.PCTV_180D)}</td>
              <td className="numeric">{num(row.TECH_SCORE)}</td>
              <td className={`numeric ${pctClass(row.MACD_vs_Signal)}`}>{num(row.MACD_vs_Signal)}</td>
              <td className="numeric">{num(row.SIG_MA_SAR)}</td>
              <td className="numeric">{num(row.RSI)}</td>
              <td><span className="scenario-label">{String(row.Market_Phase ?? "-").replace(/_/g, " ")}</span></td>
              <td><span className={String(row.Liquidity ?? "").toUpperCase() === "OK" ? "positive" : "negative"}>{String(row.Liquidity ?? "-")}</span></td>
              <td>{aiAlert ? <span className={aiAlert.enabled ? "ai-table-status active" : "ai-table-status"}>{aiAlert.verified}/{aiAlert.total}</span> : aiLevels.length ? <span className="ai-table-status active">Livelli {aiLevels.filter((item) => item.verified).length}/{aiLevels.length}</span> : "-"}</td>
              <td className="table-actions">
                <button className="btn" onClick={() => onChart(row)}>Grafico</button>
                <button className="btn ghost" onClick={() => onAi(row)}>AI</button>
                <button className="btn ghost" aria-expanded={isExpanded} onClick={() => toggleDetails(rowKey)}>{isExpanded ? "Chiudi" : "Dettagli"}</button>
                <button className={alertMap[alertKey] ? "btn alert-on" : "btn ghost"} aria-expanded={alertEditor === rowKey} onClick={() => toggleAlertEditor(rowKey, row, alertKey)}>{alertMap[alertKey] ? "Alert ON" : "Alert"}</button>
              </td>
            </tr>,
            isExpanded ? <tr className="watchlist-detail-row" key={`${rowKey}-details`}><td colSpan={15}>
              <div className="watchlist-row-details">
                <span><b>Data</b>{row.Date ? String(row.Date).slice(0, 10) : "-"}</span>
                <span><b>10D</b><i className={pctClass(row.PCTV_10D)}>{pct(row.PCTV_10D)}</i></span>
                <span><b>Alligator</b>{String(row.Signal6 ?? "-")} {row.Signal6_Trend_Days != null ? `(${row.Signal6_Trend_Days}d)` : ""}</span>
                <span><b>Stocastico</b>K {num(row.Stoch_K)} / D {num(row.Stoch_D)}</span>
                <span><b>Williams %R</b>{num(row.Williams_R)}</span>
                <span><b>Volume</b>{num(row.Volume)}</span>
                <span><b>TECH Struttura</b>{num(row.TECH_STRUCTURE)}</span>
                <span><b>TECH Momentum</b>{num(row.TECH_MOMENTUM)}</span>
                <span><b>TECH Partecipazione</b>{num(row.TECH_PARTICIPATION)}</span>
                <span><b>Penalità estensione</b>-{num(row.TECH_EXTENSION_PENALTY)}</span>
                <span className="detail-reason"><b>Motivazione</b>{String(row.Entry_Reason ?? "-")}</span>
              </div>
            </td></tr> : null,
            alertEditor === rowKey ? <tr className="watchlist-alert-row" key={`${rowKey}-alert`}><td colSpan={15}>
              <div className="watchlist-inline-alert">
                <strong>Alert {ticker}</strong>
                <label>Indicatore<select value={alertField} onChange={(event) => setAlertField(event.target.value as QuickAlertField)}>{ALERT_FIELDS.map((field) => <option key={field.value} value={field.value}>{field.label}</option>)}</select></label>
                <label>Condizione<select value={alertOp} onChange={(event) => setAlertOp(event.target.value as typeof alertOp)}><option value=">">maggiore di</option><option value="<">minore di</option><option value="==">uguale a</option><option value="!=">diverso da</option></select></label>
                <label>Valore<input value={alertValue} onChange={(event) => setAlertValue(event.target.value)} /></label>
                <button className="btn" disabled={alertBusyMap[alertKey] || !alertValue.trim()} onClick={async () => setAlertMessage(await onCreateAlert({ row, source_market: String(row.WL_Source_Market ?? market), field: alertField, op: alertOp, value: alertValue }))}>{alertMap[alertKey] ? "Aggiorna" : "Attiva"}</button>
                {alertMap[alertKey] ? <button className="btn ghost remove-btn" disabled={alertBusyMap[alertKey]} onClick={async () => { setAlertMessage(await onRemoveAlert({ row, source_market: String(row.WL_Source_Market ?? market) })); }}>Rimuovi</button> : null}
                <button className="btn ghost" onClick={() => setAlertEditor("")}>Chiudi</button>
              </div>
              {alertMessage ? <div className="watchlist-alert-message">{alertMessage}</div> : null}
            </td></tr> : null,
          ];
        })}</tbody>
      </table>
    </div>
  );
}
