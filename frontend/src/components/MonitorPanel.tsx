import { useState, useMemo } from "react";
import type { WatchlistRow, MonitorResponse, QuickAlertField } from "../types";

type QuickAlertConfig = {
  field: QuickAlertField;
  op: ">" | "<" | "==" | "!=";
  value: number | string | null;
};

type Props = {
  monitorData: MonitorResponse | undefined;
  isLoading: boolean;
  markets: string[];
  onAddMonitor: (ticker: string, sourceMarket?: string, note?: string) => Promise<void>;
  onRemoveMonitor: (ticker: string, sourceMarket?: string) => Promise<void>;
  onOpenNoteModal: (row: WatchlistRow) => void;
  onChart: (row: WatchlistRow) => void;
  onAi: (row: WatchlistRow) => void;
  onNews: (ticker: string) => void;
  alertMap: Record<string, boolean>;
  alertConfigMap: Record<string, QuickAlertConfig>;
  alertBusyMap: Record<string, boolean>;
  onCreateAlert: (input: { row: WatchlistRow; source_market: string; field: QuickAlertField; op: ">" | "<" | "==" | "!="; value: number | string }) => Promise<string>;
  onRemoveAlert: (input: { row: WatchlistRow; source_market: string }) => Promise<string>;
};

function toNum(v: unknown): number | null {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function num(v: unknown, digits = 1): string {
  const n = toNum(v);
  if (n === null) return "-";
  return n.toLocaleString("it-IT", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function pct(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "-";
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function pctColor(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "#9fb7cf";
  if (n > 0) return "#22c55e";
  if (n < 0) return "#ff4d5a";
  return "#cfe5fa";
}

function techColor(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "#9fb7cf";
  if (n >= 60) return "#22c55e";
  if (n <= 40) return "#ff4d5a";
  return "#f59e0b";
}

function s3Color(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "#9fb7cf";
  if (n > 0) return "#22c55e";
  if (n < 0) return "#ff4d5a";
  return "#9fb7cf";
}

function alligatorColor(v: unknown): string {
  const s = String(v ?? "").toLowerCase();
  if (s.includes("uptrend") || s.includes("wakeup")) return "#22c55e";
  if (s.includes("downtrend")) return "#ff4d5a";
  if (s.includes("sleep")) return "#9fb7cf";
  return "#f59e0b";
}

function fmtVol(v: unknown): string {
  const n = toNum(v);
  if (n === null) return "-";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2).replace(".", ",")}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(".", ",")}K`;
  return String(Math.round(n));
}

function entrySignalClass(sig: unknown): string {
  const s = String(sig ?? "").trim().toUpperCase();
  if (s === "ENTRA") return "action-buy";
  if (s === "OSSERVA") return "action-add";
  if (s === "EVITA") return "action-sell";
  return "action-wait";
}

export default function MonitorPanel({
  monitorData,
  isLoading,
  markets,
  onAddMonitor,
  onRemoveMonitor,
  onOpenNoteModal,
  onChart,
  onAi,
  onNews,
  alertMap,
  alertConfigMap,
  alertBusyMap,
  onCreateAlert,
  onRemoveAlert,
}: Props) {
  const [newTicker, setNewTicker] = useState("");
  const [newMarket, setNewMarket] = useState("MIB30");
  const [newNote, setNewNote] = useState("");
  const [adding, setAdding] = useState(false);
  const [filterText, setFilterText] = useState("");
  const [error, setError] = useState("");
  const [alertRow, setAlertRow] = useState<WatchlistRow | null>(null);
  const [alertField, setAlertField] = useState<QuickAlertField>("Close");
  const [alertOp, setAlertOp] = useState<">" | "<" | "==" | "!=">(">");
  const [alertValue, setAlertValue] = useState("");
  const [alertMsg, setAlertMsg] = useState("");

  const items = useMemo(() => monitorData?.items || [], [monitorData]);

  const filteredItems = useMemo(() => {
    if (!filterText.trim()) return items;
    const term = filterText.trim().toLowerCase();
    return items.filter((row) => {
      const tk = String(row.Ticker || "").toLowerCase();
      const nm = String(row.Name || "").toLowerCase();
      const note = String(row.Monitor_Note || "").toLowerCase();
      const mkt = String(row.WL_Source_Market || "").toLowerCase();
      return tk.includes(term) || nm.includes(term) || note.includes(term) || mkt.includes(term);
    });
  }, [items, filterText]);

  // Statistics
  const totalCount = items.length;
  const entraCount = items.filter((r) => r.Entry_Signal === "ENTRA").length;
  const osservaCount = items.filter((r) => r.Entry_Signal === "OSSERVA").length;
  const withNotesCount = items.filter((r) => String(r.Monitor_Note || "").trim().length > 0).length;

  const handleQuickAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const tk = newTicker.trim().toUpperCase();
    if (!tk) return;
    try {
      setAdding(true);
      setError("");
      await onAddMonitor(tk, newMarket, newNote.trim());
      setNewTicker("");
      setNewNote("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore durante l'aggiunta");
    } finally {
      setAdding(false);
    }
  };

  const openAlertBox = (row: WatchlistRow) => {
    const close = toNum(row.Close);
    const cfg = alertConfigMap[`${String(row.WL_Source_Market || "MIB30")}::${String(row.Ticker || "").toUpperCase()}`];
    setAlertRow(row);
    setAlertMsg("");
    setAlertField(cfg?.field ?? "Close");
    setAlertOp(cfg?.op ?? ">");
    setAlertValue(cfg?.value != null ? String(cfg.value) : close != null ? String(close) : "");
  };

  const saveAlert = async () => {
    if (!alertRow) return;
    const sourceMarket = String(alertRow.WL_Source_Market || "MIB30");
    const n = Number(alertValue.replace(",", "."));
    const value: number | string = alertField === "Signal6" ? alertValue : n;
    if (alertField !== "Signal6" && !Number.isFinite(n)) {
      setAlertMsg("Valore alert non valido.");
      return;
    }
    try {
      const result = await onCreateAlert({ row: alertRow, source_market: sourceMarket, field: alertField, op: alertOp, value });
      setAlertMsg(result);
    } catch (err: unknown) {
      setAlertMsg(err instanceof Error ? err.message : String(err));
    }
  };

  const deleteAlert = async () => {
    if (!alertRow) return;
    const sourceMarket = String(alertRow.WL_Source_Market || "MIB30");
    try {
      const result = await onRemoveAlert({ row: alertRow, source_market: sourceMarket });
      setAlertMsg(result);
      setAlertRow(null);
    } catch (err: unknown) {
      setAlertMsg(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="monitor-panel" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header & KPI Cards */}
      <div className="panel-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
            🎯 Titoli in Monitoraggio Attivo
          </h2>
          <div style={{ fontSize: "0.88rem", color: "var(--text-muted)", marginTop: 4 }}>
            Monitora da vicino i titoli con nota operativa e segnali aggiornati in tempo reale.
          </div>
        </div>

        <div className="monitor-stats-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(132px, 1fr))", gap: 12, width: "100%" }}>
          <div className="stat-card" style={{ background: "var(--bg-card, #262626)", padding: "8px 16px", borderRadius: 8, textAlign: "center", border: "1px solid var(--border-color, #333)" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Totale Monitor</div>
            <div style={{ fontSize: "1.3rem", fontWeight: 700 }}>{totalCount}</div>
          </div>
          <div className="stat-card" style={{ background: "var(--bg-card, #262626)", padding: "8px 16px", borderRadius: 8, textAlign: "center", border: "1px solid var(--border-color, #333)" }}>
            <div style={{ fontSize: "0.75rem", color: "#4caf50", textTransform: "uppercase" }}>Entra</div>
            <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "#4caf50" }}>{entraCount}</div>
          </div>
          <div className="stat-card" style={{ background: "var(--bg-card, #262626)", padding: "8px 16px", borderRadius: 8, textAlign: "center", border: "1px solid var(--border-color, #333)" }}>
            <div style={{ fontSize: "0.75rem", color: "#0288d1", textTransform: "uppercase" }}>Osserva</div>
            <div style={{ fontSize: "1.3rem", fontWeight: 700, color: "#0288d1" }}>{osservaCount}</div>
          </div>
          <div className="stat-card" style={{ background: "var(--bg-card, #262626)", padding: "8px 16px", borderRadius: 8, textAlign: "center", border: "1px solid var(--border-color, #333)" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>Con Note</div>
            <div style={{ fontSize: "1.3rem", fontWeight: 700 }}>{withNotesCount}</div>
          </div>
        </div>
      </div>

      {/* Quick Add Bar */}
      <form className="monitor-add-form" onSubmit={handleQuickAdd} style={{ background: "var(--bg-card, #262626)", padding: 14, borderRadius: 10, border: "1px solid var(--border-color, #333)", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 10, alignItems: "center" }}>
        <span className="monitor-add-label" style={{ fontWeight: 600, fontSize: "0.9rem" }}>Aggiungi Ticker</span>
        <input
          className="monitor-ticker-input"
          type="text"
          placeholder="es. AMP.MI, ERG.MI"
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #444", background: "#1a1a1a", color: "#fff", width: "100%", minWidth: 0, fontSize: "0.88rem", boxSizing: "border-box" }}
          required
        />
        <select
          className="monitor-market-select"
          value={newMarket}
          onChange={(e) => setNewMarket(e.target.value)}
          style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #444", background: "#1a1a1a", color: "#fff", width: "100%", minWidth: 0, fontSize: "0.88rem", boxSizing: "border-box" }}
        >
          {markets.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <input
          className="monitor-note-input"
          type="text"
          placeholder="Nota opzionale (es. breakout sopra 12.20)"
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #444", background: "#1a1a1a", color: "#fff", width: "100%", minWidth: 0, fontSize: "0.88rem", boxSizing: "border-box" }}
        />
        <button type="submit" className="btn primary monitor-add-button" disabled={adding || !newTicker.trim()} style={{ padding: "6px 16px", fontSize: "0.88rem", width: "100%" }}>
          {adding ? "Aggiungo..." : "+ Aggiungi a Monitor"}
        </button>
      </form>

      {error && <div className="error-banner">{error}</div>}

      {/* Filter / Search inside Monitor */}
      {items.length > 0 && (
        <div className="monitor-filter-row" style={{ display: "grid", gridTemplateColumns: "minmax(220px, 1fr) auto", gap: 10, alignItems: "center" }}>
          <input
            className="monitor-filter-input"
            type="text"
            placeholder="🔍 Filtra nei titoli monitorati..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #444", background: "#1a1a1a", color: "#fff", width: "100%", minWidth: 0, fontSize: "0.85rem", boxSizing: "border-box" }}
          />
          <div className="monitor-filter-count" style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
            Visualizzati {filteredItems.length} di {totalCount} titoli
          </div>
        </div>
      )}

      {alertRow ? (() => {
        const src = String(alertRow.WL_Source_Market || "MIB30");
        const tk = String(alertRow.Ticker || "").toUpperCase();
        const key = `${src}::${tk}`;
        const busy = Boolean(alertBusyMap[key]);
        const active = Boolean(alertMap[key]);
        return (
          <div className="modal-backdrop" onClick={() => setAlertRow(null)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
              <div className="modal-header">
                <div><h3 style={{ margin: 0 }}>🔔 Alert rapido</h3><div style={{ color: "var(--text-muted)", marginTop: 4 }}>{tk} · {src}</div></div>
                <button className="btn-close" onClick={() => setAlertRow(null)}>✕</button>
              </div>
              <div className="modal-body" style={{ display: "grid", gap: 10 }}>
                <select value={alertField} onChange={(e) => setAlertField(e.target.value as QuickAlertField)}>
                  <option value="Close">Close</option>
                  <option value="RSI">RSI</option>
                  <option value="Williams_R">Williams %R</option>
                  <option value="MACD_vs_Signal">S3</option>
                  <option value="SIG_MA_SAR">SARMA</option>
                  <option value="Stoch_KvsD">Stoch K-D</option>
                  <option value="DI_diff">DI+ - DI-</option>
                </select>
                <div className="watchlist-mode">
                  <button className={alertOp === ">" ? "quick-bar active" : "quick-bar"} onClick={() => setAlertOp(">")}>&gt;</button>
                  <button className={alertOp === "<" ? "quick-bar active" : "quick-bar"} onClick={() => setAlertOp("<")}>&lt;</button>
                </div>
                <input value={alertValue} onChange={(e) => setAlertValue(e.target.value)} placeholder="Valore soglia" />
                {alertMsg ? <div className="muted">{alertMsg}</div> : null}
              </div>
              <div className="modal-footer" style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                {active ? <button className="btn ghost remove-btn" disabled={busy} onClick={deleteAlert}>Rimuovi alert</button> : <div />}
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn ghost" onClick={() => setAlertRow(null)}>Chiudi</button>
                  <button className="btn primary" disabled={busy} onClick={saveAlert}>{active ? "Aggiorna alert" : "Crea alert"}</button>
                </div>
              </div>
            </div>
          </div>
        );
      })() : null}

      {/* Monitor cards */}
      {isLoading ? (
        <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>
          Caricamento dati monitor in corso...
        </div>
      ) : filteredItems.length === 0 ? (
        <div style={{ textAlign: "center", padding: "50px 20px", background: "var(--bg-card, #262626)", borderRadius: 10, border: "1px solid var(--border-color, #333)" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: 10 }}>🎯</div>
          <h3 style={{ margin: "0 0 8px 0" }}>Nessun titolo in monitoraggio</h3>
          <p style={{ color: "var(--text-muted)", margin: "0 0 16px 0", maxWidth: 460, marginLeft: "auto", marginRight: "auto" }}>
            Aggiungi i tuoi titoli chiave premendo il pulsante <strong>+ Monitor</strong> sulle card delle watchlist o inserendo il ticker qui sopra.
          </p>
        </div>
      ) : (
        <div className="monitor-card-grid">
          {filteredItems.map((row) => {
            const tk = String(row.Ticker || "").trim();
            const nm = String(row.Name || tk);
            const src = String(row.WL_Source_Market || "MIB30");
            const note = String(row.Monitor_Note || "").trim();
            const phase = String(row.Market_Phase || "-");
            const detail = String(row.Trend_Phase_Detail || "").replace(/_/g, " ");
            const entry = String(row.Entry_Signal || "ATTENDI").toUpperCase();
            const date = row.Date ? (row.Date instanceof Date ? row.Date.toISOString().slice(0, 10) : String(row.Date).slice(0, 10)) : "non disponibile";

            return (
              <article className="monitor-card" key={`${src}-${tk}`}>
                <header className="monitor-card-head">
                  <div>
                    <strong>{tk}</strong>
                    <span>{nm}</span>
                    <small>Dato al {date} · {src}</small>
                  </div>
                  <div className="monitor-card-price">
                    <b>{num(row.Close, 3)}</b>
                    <em style={{ color: pctColor(row.PCTV_1D) }}>{pct(row.PCTV_1D)}</em>
                  </div>
                </header>

                <div className="monitor-card-metrics">
                  <span>1D: <b style={{ color: pctColor(row.PCTV_1D) }}>{pct(row.PCTV_1D)}</b></span>
                  <span>5D: <b style={{ color: pctColor(row.PCTV_5D) }}>{pct(row.PCTV_5D)}</b></span>
                  <span>10D: <b style={{ color: pctColor(row.PCTV_10D) }}>{pct(row.PCTV_10D)}</b></span>
                  <span>30D: <b style={{ color: pctColor(row.PCTV_30D) }}>{pct(row.PCTV_30D)}</b></span>
                  <span>180D: <b style={{ color: pctColor(row.PCTV_180D) }}>{pct(row.PCTV_180D)}</b></span>
                  <span>TECH: <b style={{ color: techColor(row.TECH_SCORE) }}>{num(row.TECH_SCORE, 0)}</b></span>
                  <span>S2: <b>{num(row.Pattern_S2_Days_Ago, 0)}d</b></span>
                  <span>S3: <b style={{ color: s3Color(row.MACD_vs_Signal) }}>{num(row.MACD_vs_Signal, 0)}</b></span>
                  <span>S3_Pat: <b>{num(row.Pattern_S3_Days_Ago, 0)}d</b></span>
                  <span>SARMA: <b style={{ color: (toNum(row.SIG_MA_SAR) ?? 0) >= 0 ? "#22c55e" : "#ff4d5a" }}>{num(row.SIG_MA_SAR, 0)}</b></span>
                  <span>RSI: <b style={{ color: techColor(row.RSI) }}>{num(row.RSI, 0)}</b></span>
                  <span>ADX: <b style={{ color: techColor(row.ADX) }}>{num(row.ADX, 1)}</b></span>
                  <span>DI+: <b style={{ color: "#22c55e" }}>{num(row.PLUS_DI, 1)}</b></span>
                  <span>DI-: <b style={{ color: "#ff4d5a" }}>{num(row.MINUS_DI, 1)}</b></span>
                  <span>willR: <b style={{ color: s3Color(row.Williams_R) }}>{num(row.Williams_R, 0)}</b></span>
                  <span>Sk: <b>{num(row.Stoch_K, 0)}</b></span>
                  <span>Sd: <b>{num(row.Stoch_D, 0)}</b></span>
                  <span>Alligator: <b style={{ color: alligatorColor(row.Signal6) }}>{String(row.Signal6 ?? "-")} {row.Signal6_Trend_Days !== undefined ? `(${row.Signal6_Trend_Days}d)` : ""}</b></span>
                  <span>LIQ: <b style={{ color: String(row.Liquidity ?? "").toUpperCase() === "OK" ? "#22c55e" : "#ff4d5a" }}>{String(row.Liquidity ?? "-")}</b></span>
                </div>

                <div className="monitor-card-context">
                  <span className={`pill ${entrySignalClass(entry)}`}>{entry === "ENTRA" ? "✓ ENTRA" : entry === "OSSERVA" ? "◉ OSSERVA" : entry === "EVITA" ? "✕ EVITA" : "○ ATTENDI"}</span>
                  <p>Contesto tecnico: <b>{phase}</b>{detail && detail !== phase ? ` · ${detail}` : ""}</p>
                  {row.Entry_Reason ? <p>{String(row.Entry_Reason)}</p> : null}
                  <p>VOL: {fmtVol(row.Volume)}</p>
                  {note ? <p className="monitor-note">Nota: {note}</p> : null}
                </div>

                <div className="monitor-card-actions">
                  <button type="button" className="btn primary" onClick={(e) => { e.stopPropagation(); onChart(row); }}>Grafico</button>
                  <button type="button" className="btn ghost" onClick={(e) => { e.stopPropagation(); onAi(row); }}>AI</button>
                  <button type="button" className="btn ghost" onClick={(e) => { e.stopPropagation(); onNews(tk); }}>News</button>
                  <button type="button" className="btn ghost" onClick={(e) => { e.stopPropagation(); onOpenNoteModal(row); }}>Dettagli</button>
                  <button type="button" className="btn ghost" onClick={(e) => { e.stopPropagation(); openAlertBox(row); }}>Alert</button>
                  <button type="button" className="btn ghost danger" onClick={(e) => { e.stopPropagation(); onRemoveMonitor(tk, src); }}>Rimuovi</button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}






