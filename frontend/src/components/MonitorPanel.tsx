import { useState, useMemo } from "react";
import type { WatchlistRow, MonitorResponse } from "../types";

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
  onAlert: (row: WatchlistRow) => void;
};

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
  onAlert,
}: Props) {
  const [newTicker, setNewTicker] = useState("");
  const [newMarket, setNewMarket] = useState("MIB30");
  const [newNote, setNewNote] = useState("");
  const [adding, setAdding] = useState(false);
  const [filterText, setFilterText] = useState("");
  const [error, setError] = useState("");

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

  const formatPct = (val: unknown) => {
    const num = Number(val);
    if (!Number.isFinite(num)) return "-";
    const sign = num > 0 ? "+" : "";
    const color = num > 0 ? "var(--color-up, #4caf50)" : num < 0 ? "var(--color-down, #f44336)" : "inherit";
    return <span style={{ color, fontWeight: 600 }}>{sign}{num.toFixed(2)}%</span>;
  };

  const getSignalBadge = (sig?: string) => {
    const s = String(sig || "").toUpperCase();
    if (s === "ENTRA") return <span className="badge badge-success" style={{ background: "#2e7d32", color: "#fff", padding: "2px 8px", borderRadius: 4, fontWeight: 700, fontSize: "0.75rem" }}>ENTRA</span>;
    if (s === "OSSERVA") return <span className="badge badge-info" style={{ background: "#0288d1", color: "#fff", padding: "2px 8px", borderRadius: 4, fontWeight: 700, fontSize: "0.75rem" }}>OSSERVA</span>;
    if (s === "ATTENDI") return <span className="badge badge-warning" style={{ background: "#ed6c02", color: "#fff", padding: "2px 8px", borderRadius: 4, fontWeight: 700, fontSize: "0.75rem" }}>ATTENDI</span>;
    if (s === "EVITA") return <span className="badge badge-danger" style={{ background: "#d32f2f", color: "#fff", padding: "2px 8px", borderRadius: 4, fontWeight: 700, fontSize: "0.75rem" }}>EVITA</span>;
    return <span style={{ fontSize: "0.8rem", opacity: 0.7 }}>-</span>;
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

        <div className="monitor-stats-grid" style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
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
      <form className="monitor-add-form" onSubmit={handleQuickAdd} style={{ background: "var(--bg-card, #262626)", padding: 14, borderRadius: 10, border: "1px solid var(--border-color, #333)", display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
        <span className="monitor-add-label" style={{ fontWeight: 600, fontSize: "0.9rem" }}>Aggiungi Ticker:</span>
        <input
          className="monitor-ticker-input"
          type="text"
          placeholder="es. AMP.MI, ERG.MI"
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #444", background: "#1a1a1a", color: "#fff", width: 140, fontSize: "0.88rem" }}
          required
        />
        <select
          className="monitor-market-select"
          value={newMarket}
          onChange={(e) => setNewMarket(e.target.value)}
          style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #444", background: "#1a1a1a", color: "#fff", fontSize: "0.88rem" }}
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
          style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #444", background: "#1a1a1a", color: "#fff", flex: 1, minWidth: 200, fontSize: "0.88rem" }}
        />
        <button type="submit" className="btn primary monitor-add-button" disabled={adding || !newTicker.trim()} style={{ padding: "6px 16px", fontSize: "0.88rem" }}>
          {adding ? "Aggiungo..." : "+ Aggiungi a Monitor"}
        </button>
      </form>

      {error && <div className="error-banner">{error}</div>}

      {/* Filter / Search inside Monitor */}
      {items.length > 0 && (
        <div className="monitor-filter-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <input
            className="monitor-filter-input"
            type="text"
            placeholder="🔍 Filtra nei titoli monitorati..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #444", background: "#1a1a1a", color: "#fff", width: 260, fontSize: "0.85rem" }}
          />
          <div className="monitor-filter-count" style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
            Visualizzati {filteredItems.length} di {totalCount} titoli
          </div>
        </div>
      )}

      {/* Main Table */}
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
        <div className="table-responsive" style={{ overflowX: "auto" }}>
          <table className="watchlist-table" style={{ width: "max-content", minWidth: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "var(--bg-table-header, #1f1f1f)", borderBottom: "2px solid #333", textAlign: "left", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                <th style={{ padding: "10px 12px" }}>TICKER / NOME</th>
                <th style={{ padding: "10px 12px" }}>MERCATO</th>
                <th style={{ padding: "10px 12px" }}>PREZZO</th>
                <th style={{ padding: "10px 12px" }}>1D %</th>
                <th style={{ padding: "10px 12px" }}>5D %</th>
                <th style={{ padding: "10px 12px" }}>30D %</th>
                <th style={{ padding: "10px 12px" }}>SEGNALE</th>
                <th style={{ padding: "10px 12px" }}>SCORE</th>
                <th style={{ padding: "10px 12px" }}>INDICATORI</th>
                <th style={{ padding: "10px 12px", width: 240, minWidth: 240 }}>NOTA OPERATIVA MANUAL</th>
                <th style={{ padding: "10px 12px", textAlign: "right", width: 230, minWidth: 230 }}>AZIONI</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((row) => {
                const tk = String(row.Ticker || "").trim();
                const nm = String(row.Name || tk);
                const src = String(row.WL_Source_Market || "MIB30");
                const close = Number(row.Close);
                const note = String(row.Monitor_Note || "").trim();
                const techScore = Number(row.TECH_SCORE);

                return (
                  <tr key={`${src}-${tk}`} style={{ borderBottom: "1px solid var(--border-color, #2a2a2a)", fontSize: "0.88rem" }}>
                    {/* Ticker & Name */}
                    <td style={{ padding: "10px 12px" }}>
                      <div style={{ fontWeight: 700, fontSize: "0.95rem" }}>{tk}</div>
                      <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: 160 }}>
                        {nm}
                      </div>
                    </td>

                    {/* Mercato */}
                    <td style={{ padding: "10px 12px" }}>
                      <span className="quick-bar" style={{ fontSize: "0.75rem", padding: "2px 6px" }}>{src}</span>
                    </td>

                    {/* Prezzo */}
                    <td style={{ padding: "10px 12px", fontWeight: 600 }}>
                      {Number.isFinite(close) ? close.toFixed(2) : "-"}
                    </td>

                    {/* Variazioni */}
                    <td style={{ padding: "10px 12px" }}>{formatPct(row.PCTV_1D)}</td>
                    <td style={{ padding: "10px 12px" }}>{formatPct(row.PCTV_5D)}</td>
                    <td style={{ padding: "10px 12px" }}>{formatPct(row.PCTV_30D)}</td>

                    {/* Segnale */}
                    <td style={{ padding: "10px 12px" }}>{getSignalBadge(row.Entry_Signal)}</td>

                    {/* Score */}
                    <td style={{ padding: "10px 12px", fontWeight: 600 }}>
                      {Number.isFinite(techScore) ? (
                        <span style={{ color: techScore >= 60 ? "#4caf50" : techScore <= 40 ? "#f44336" : "#ff9800" }}>
                          {techScore.toFixed(0)}
                        </span>
                      ) : "-"}
                    </td>

                    {/* Indicatori */}
                    <td style={{ padding: "10px 12px", fontSize: "0.78rem" }}>
                      <div>RSI: <strong>{Number.isFinite(Number(row.RSI)) ? Number(row.RSI).toFixed(0) : "-"}</strong></div>
                      <div>ADX: <strong>{Number.isFinite(Number(row.ADX)) ? Number(row.ADX).toFixed(0) : "-"}</strong></div>
                    </td>

                    {/* Nota Operativa Manuale */}
                    <td style={{ padding: "10px 12px", width: 240, minWidth: 240 }}>
                      <div
                        onClick={() => onOpenNoteModal(row)}
                        style={{
                          background: note ? "rgba(2, 136, 209, 0.1)" : "rgba(255, 255, 255, 0.03)",
                          border: note ? "1px solid rgba(2, 136, 209, 0.3)" : "1px dashed #444",
                          borderRadius: 6,
                          padding: "6px 10px",
                          fontSize: "0.82rem",
                          color: note ? "#e0e0e0" : "var(--text-muted)",
                          cursor: "pointer",
                          minHeight: 32,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 6,
                        }}
                        title="Clicca per modificare la nota"
                      >
                        <span style={{ fontStyle: note ? "normal" : "italic", flex: 1 }}>
                          {note || "+ Aggiungi nota..."}
                        </span>
                        <span style={{ fontSize: "0.75rem", opacity: 0.6 }}>✏️</span>
                      </div>
                    </td>

                    {/* Azioni */}
                    <td style={{ padding: "10px 12px", textAlign: "right", width: 230, minWidth: 230 }}>
                      <div style={{ display: "flex", gap: 4, justifyContent: "flex-end", flexWrap: "nowrap" }}>
                        <button type="button" className="btn ghost" onClick={() => onChart(row)} title="Grafico" style={{ padding: "4px 8px", fontSize: "0.8rem" }}>
                          📈
                        </button>
                        <button type="button" className="btn ghost" onClick={() => onAi(row)} title="Analisi AI" style={{ padding: "4px 8px", fontSize: "0.8rem" }}>
                          🤖
                        </button>
                        <button type="button" className="btn ghost" onClick={() => onNews(tk)} title="News" style={{ padding: "4px 8px", fontSize: "0.8rem" }}>
                          📰
                        </button>
                        <button type="button" className="btn ghost" onClick={() => onAlert(row)} title="Alert" style={{ padding: "4px 8px", fontSize: "0.8rem" }}>
                          🔔
                        </button>
                        <button type="button" className="btn ghost danger" onClick={() => onRemoveMonitor(tk, src)} title="Rimuovi da Monitor" style={{ padding: "4px 8px", fontSize: "0.8rem" }}>
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}






