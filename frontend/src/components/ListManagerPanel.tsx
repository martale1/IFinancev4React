import { useState, useEffect, useMemo, useRef } from "react";

interface ListManagerPanelProps {
  initialMarket: string;
  markets: string[];
}

interface TickerItem {
  Ticker: string;
  Name: string;
  Source_Market?: string;
}

const ANALYSIS_MARKETS = ["MIB30", "ETC", "ETF", "Preferite", "DAX", "US_Others", "Crypto"];

interface AnalysisJob {
  running: boolean;
  status: "idle" | "running" | "stopping" | "cancelled" | "completed" | "failed";
  markets: string[];
  logs: string[];
  return_code: number | null;
  started_at: string | null;
  finished_at: string | null;
}

export default function ListManagerPanel({ initialMarket, markets }: ListManagerPanelProps) {
  const [selectedMarket, setSelectedMarket] = useState(initialMarket || "Preferite");
  const [items, setItems] = useState<TickerItem[]>([]);
  const [sortOrder, setSortOrder] = useState<"ticker_asc" | "ticker_desc" | "name_asc" | "name_desc">("ticker_asc");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [newTicker, setNewTicker] = useState("");
  const [newName, setNewName] = useState("");
  const [sourceMarket, setSourceMarket] = useState("MIB30");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Actions state
  const [removingTicker, setRemovingTicker] = useState<string | null>(null);
  const [selectedTickers, setSelectedTickers] = useState<string[]>([]);
  const [regenerating, setRegenerating] = useState(false);
  const [analysisMarkets, setAnalysisMarkets] = useState<string[]>(["MIB30"]);
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null);
  const logEndRef = useRef<HTMLDivElement | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const orderedItems = useMemo(() => {
    const byTicker = (a: TickerItem, b: TickerItem) => String(a.Ticker || "").localeCompare(
      String(b.Ticker || ""), "it", { sensitivity: "base", numeric: true }
    );
    const byName = (a: TickerItem, b: TickerItem) => String(a.Name || "").localeCompare(
      String(b.Name || ""), "it", { sensitivity: "base", numeric: true }
    );

    return [...items].sort((a, b) => {
      if (sortOrder === "ticker_asc") return byTicker(a, b) || byName(a, b);
      if (sortOrder === "ticker_desc") return -(byTicker(a, b) || byName(a, b));
      if (sortOrder === "name_asc") return byName(a, b) || byTicker(a, b);
      return -(byName(a, b) || byTicker(a, b));
    });
  }, [items, sortOrder]);

  // Automatically hide toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  async function fetchAnalysisStatus() {
    try {
      const res = await fetch(`/api/watchlist/regenerate/status?t=${Date.now()}`, {
        cache: "no-store",
        headers: { "Cache-Control": "no-cache" },
      });
      if (!res.ok) return;
      const data = await res.json() as AnalysisJob;
      setAnalysisJob(data);
      setRegenerating(data.running);
    } catch {
      // Il polling riproverà automaticamente al ciclo successivo.
    }
  }

  useEffect(() => {
    fetchAnalysisStatus();
    const timer = window.setInterval(fetchAnalysisStatus, 1500);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [analysisJob?.logs.length]);

  // Fetch list items
  async function fetchList(marketName: string) {
    setIsLoading(true);
    setError(null);
    setSelectedTickers([]);
    try {
      const res = await fetch(`/api/ticker-lists/${encodeURIComponent(marketName)}`);
      if (!res.ok) {
        throw new Error(`Impossibile caricare i dati: ${res.statusText}`);
      }
      const data = await res.json();
      setItems(data.items || []);
    } catch (err: any) {
      setError(err.message || "Errore sconosciuto nel caricamento della lista.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchList(selectedMarket);
  }, [selectedMarket]);

  // Handle Add Ticker
  async function handleAddTicker(e: React.FormEvent) {
    e.preventDefault();
    if (!newTicker.trim() || !newName.trim()) {
      setToast({ message: "Sia il Ticker che il Nome sono obbligatori.", type: "error" });
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`/api/ticker-lists/${encodeURIComponent(selectedMarket)}/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: newTicker,
          name: newName,
          source_market: selectedMarket.startsWith("WL:") ? sourceMarket : null
        })
      });

      if (!res.ok) {
        throw new Error(`Errore durante l'aggiunta: ${res.statusText}`);
      }

      const data = await res.json();
      if (data.status === "exists") {
        setToast({ message: `Il ticker ${newTicker.toUpperCase()} è già presente nella lista.`, type: "error" });
      } else {
        setToast({ message: `Ticker ${newTicker.toUpperCase()} aggiunto con successo!`, type: "success" });
        setNewTicker("");
        setNewName("");
        fetchList(selectedMarket);
      }
    } catch (err: any) {
      setToast({ message: err.message || "Errore sconosciuto durante l'aggiunta.", type: "error" });
    } finally {
      setIsSubmitting(false);
    }
  }

  // Handle Remove Ticker
  async function handleRemoveTicker(ticker: string, srcMkt?: string) {
    if (!confirm(`Sei sicuro di voler rimuovere il ticker ${ticker} da questa lista?`)) {
      return;
    }

    setRemovingTicker(ticker);
    try {
      const res = await fetch(`/api/ticker-lists/${encodeURIComponent(selectedMarket)}/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: ticker,
          source_market: srcMkt
        })
      });

      if (!res.ok) {
        throw new Error(`Errore durante la rimozione: ${res.statusText}`);
      }

      setToast({ message: `Ticker ${ticker} rimosso con successo.`, type: "success" });
      fetchList(selectedMarket);
    } catch (err: any) {
      setToast({ message: err.message || "Errore sconosciuto durante la rimozione.", type: "error" });
    } finally {
      setRemovingTicker(null);
    }
  }

  // Handle Bulk Remove Tickers
  async function handleBulkRemove() {
    if (selectedTickers.length === 0) return;
    if (!confirm(`Sei sicuro di voler eliminare i ${selectedTickers.length} ticker selezionati in un colpo solo?`)) {
      return;
    }

    setRemovingTicker("BULK");
    try {
      const res = await fetch(`/api/ticker-lists/${encodeURIComponent(selectedMarket)}/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tickers: selectedTickers
        })
      });

      if (!res.ok) {
        throw new Error(`Errore durante la rimozione multipla: ${res.statusText}`);
      }

      setToast({ message: `${selectedTickers.length} ticker rimossi con successo.`, type: "success" });
      setSelectedTickers([]);
      fetchList(selectedMarket);
    } catch (err: any) {
      setToast({ message: err.message || "Errore sconosciuto durante la rimozione multipla.", type: "error" });
    } finally {
      setRemovingTicker(null);
    }
  }

  // Handle Regenerate Data
  async function handleRegenerate() {
    if (analysisMarkets.length === 0) {
      setToast({ message: "Seleziona almeno un mercato da analizzare.", type: "error" });
      return;
    }
    setRegenerating(true);
    try {
      const res = await fetch("/api/watchlist/regenerate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ markets: analysisMarkets }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail || `Errore nell'avvio: ${res.statusText}`);
      }
      setToast({ 
        message: `⚡ Analisi avviata per: ${analysisMarkets.join(", ")}.`,
        type: "success" 
      });
      await fetchAnalysisStatus();
    } catch (err: any) {
      setToast({ message: err.message || "Errore sconosciuto nell'avvio dei calcoli.", type: "error" });
      setRegenerating(false);
    }
  }

  async function handleStopAnalysis() {
    try {
      const res = await fetch("/api/watchlist/regenerate/stop", { method: "POST" });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail || `Errore durante l'arresto: ${res.statusText}`);
      }
      setToast({ message: "⏹ Arresto dell'analisi richiesto.", type: "success" });
      await fetchAnalysisStatus();
    } catch (err: any) {
      setToast({ message: err.message || "Impossibile interrompere l'analisi.", type: "error" });
    }
  }

  function toggleAnalysisMarket(marketName: string) {
    if (regenerating) return;
    setAnalysisMarkets((current) =>
      current.includes(marketName)
        ? current.filter((name) => name !== marketName)
        : [...current, marketName]
    );
  }

  return (
    <div className="list-manager-panel" style={{ marginTop: "1rem", display: "grid", gap: "1.5rem" }}>
      {/* Toast Notification */}
      {toast && (
        <div className="analysis-layout" style={{
          position: "fixed",
          top: "20px",
          right: "20px",
          padding: "1rem 1.5rem",
          borderRadius: "12px",
          zIndex: 9999,
          background: toast.type === "success" ? "rgba(34,197,94,0.9)" : "rgba(239,68,68,0.9)",
          border: `1px solid ${toast.type === "success" ? "rgba(74,222,128,0.5)" : "rgba(248,113,113,0.5)"}`,
          color: "#ffffff",
          boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
          fontWeight: 600,
          backdropFilter: "blur(8px)"
        }}>
          {toast.message}
        </div>
      )}

      {/* 1. Header & Select Market */}
      <section className="hero" style={{ flexDirection: "column", gap: "1rem", alignItems: "stretch", position: "relative" }}>
        <div className="analysis-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div className="analysis-title">
            <h2 style={{ fontSize: "1.25rem", margin: 0, color: "#ffffff" }}>📂 Gestore Database e Liste Titoli (Excel & JSON)</h2>
            <p style={{ fontSize: "0.85rem", color: "#8cb4d9", margin: "0.2rem 0 0 0" }}>
              Visualizza, aggiungi o rimuovi titoli dai file Excel sorgenti (`preferite.xlsx`, `validtickers_DE_DAX.xlsx`, ecc.) e dalle watchlists della GUI.
            </p>
          </div>
          <button
            type="button"
            className="btn analysis-run-button"
            disabled={analysisJob?.status === "stopping"}
            onClick={regenerating ? handleStopAnalysis : handleRegenerate}
            style={{ 
              height: "40px", 
              background: regenerating
                ? "linear-gradient(135deg, #ef4444 0%, #b91c1c 100%)"
                : "linear-gradient(135deg, #fbbf24 0%, #d97706 100%)",
              border: regenerating ? "1px solid rgba(248,113,113,0.5)" : "1px solid rgba(251,191,36,0.3)",
              fontWeight: "bold",
              color: "#050b14",
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
              cursor: "pointer"
            }}
          >
            {analysisJob?.status === "stopping"
              ? "⏳ ARRESTO IN CORSO..."
              : regenerating
                ? "⏹ INTERROMPI ANALISI"
                : "⚡ RIGENERA ANALISI DATABASE (main.py)"}
          </button>
        </div>

        <div style={{
          display: "grid", gridTemplateColumns: "minmax(260px, 0.8fr) minmax(420px, 1.7fr)",
          gap: "1rem", alignItems: "stretch"
        }}>
          <div style={{ background: "rgba(8,18,34,0.55)", padding: "0.9rem", borderRadius: "12px", border: "1px solid rgba(184,216,246,0.15)" }}>
            <div style={{ fontWeight: 700, color: "#cfe5fa", marginBottom: "0.65rem" }}>Mercati da analizzare</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "0.5rem" }}>
              {ANALYSIS_MARKETS.map((marketName) => (
                <label key={marketName} style={{
                  display: "flex", alignItems: "center", gap: "0.45rem", cursor: regenerating ? "not-allowed" : "pointer",
                  padding: "0.4rem 0.55rem", borderRadius: "8px",
                  background: analysisMarkets.includes(marketName) ? "rgba(56,189,248,0.14)" : "rgba(255,255,255,0.025)",
                  border: analysisMarkets.includes(marketName) ? "1px solid rgba(56,189,248,0.45)" : "1px solid rgba(184,216,246,0.12)"
                }}>
                  <input
                    type="checkbox"
                    checked={analysisMarkets.includes(marketName)}
                    disabled={regenerating}
                    onChange={() => toggleAnalysisMarket(marketName)}
                  />
                  <span>{marketName}</span>
                </label>
              ))}
            </div>
            <div style={{ fontSize: "0.75rem", color: "#8cb4d9", marginTop: "0.65rem" }}>
              Puoi selezionare uno o più mercati prima di avviare il calcolo.
            </div>
          </div>

          <div className="analysis-log" style={{ background: "#050b14", borderRadius: "12px", border: "1px solid rgba(74,222,128,0.25)", overflow: "hidden" }}>
            <div style={{
              display: "flex", justifyContent: "space-between", gap: "1rem", padding: "0.55rem 0.75rem",
              background: "rgba(15,34,55,0.95)", borderBottom: "1px solid rgba(184,216,246,0.12)", fontSize: "0.8rem"
            }}>
              <strong style={{ color: "#cfe5fa" }}>Log analisi</strong>
              <span style={{ color: analysisJob?.status === "failed" ? "#f87171" : analysisJob?.running ? "#fbbf24" : "#4ade80" }}>
                {analysisJob?.status === "stopping" ? "◌ ARRESTO IN CORSO"
                  : analysisJob?.running ? "● IN ESECUZIONE"
                  : analysisJob?.status === "completed" ? "✓ COMPLETATA"
                  : analysisJob?.status === "cancelled" ? "■ INTERROTTA"
                  : analysisJob?.status === "failed" ? "✕ ERRORE"
                  : "IN ATTESA"}
              </span>
            </div>
            <div style={{
              height: "190px", overflowY: "auto", padding: "0.75rem", whiteSpace: "pre-wrap",
              fontFamily: "Consolas, 'Courier New', monospace", fontSize: "0.75rem", lineHeight: 1.45, color: "#b8d8f6"
            }}>
              {analysisJob?.logs.length
                ? analysisJob.logs.map((line, index) => <div key={`${index}-${line}`}>{line || " "}</div>)
                : <span style={{ color: "#64748b" }}>Seleziona i mercati e premi “Rigenera analisi”.</span>}
              <div ref={logEndRef} />
            </div>
          </div>
        </div>

        <div className="list-controls-layout" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginTop: "0.5rem" }}>
          {/* Market Selection Dropdown */}
          <div style={{ background: "rgba(8,18,34,0.4)", padding: "0.8rem", borderRadius: "12px", border: "1px solid rgba(184,216,246,0.15)" }}>
            <span style={{ fontSize: "0.82rem", fontWeight: "bold", display: "block", marginBottom: "0.4rem", color: "#cfe5fa" }}>
              Seleziona la Lista da Gestire:
            </span>
            <select
              value={selectedMarket}
              onChange={(e) => setSelectedMarket(e.target.value)}
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                borderRadius: "8px",
                backgroundColor: "rgba(12, 28, 48, 0.7)",
                border: "1px solid rgba(184, 216, 246, 0.25)",
                color: "#ffffff",
                fontSize: "0.88rem",
                cursor: "pointer",
                outline: "none"
              }}
            >
              {markets.map((m) => (
                <option key={m} value={m}>
                  {m.startsWith("WL:") ? `⭐ Watchlist Custom: ${m.slice(3)}` : `📊 Excel sorgente: ${m}`}
                </option>
              ))}
            </select>
          </div>

          {/* Add Ticker Form */}
          <form onSubmit={handleAddTicker} style={{ background: "rgba(8,18,34,0.4)", padding: "0.8rem", borderRadius: "12px", border: "1px solid rgba(184,216,246,0.15)", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            <span style={{ fontSize: "0.82rem", fontWeight: "bold", display: "block", color: "#cfe5fa" }}>
              ➕ Aggiungi un Nuovo Titolo alla Lista:
            </span>
            <div className="add-ticker-fields" style={{ display: "grid", gridTemplateColumns: selectedMarket.startsWith("WL:") ? "1fr 1.2fr 1fr" : "1fr 1.5fr", gap: "0.5rem" }}>
              <input
                type="text"
                placeholder="Ticker (es. RWE.DE)"
                value={newTicker}
                onChange={(e) => setNewTicker(e.target.value)}
                style={{
                  padding: "0.4rem 0.6rem",
                  borderRadius: "8px",
                  backgroundColor: "rgba(12, 28, 48, 0.8)",
                  border: "1px solid rgba(184, 216, 246, 0.2)",
                  color: "#ffffff",
                  fontSize: "0.84rem",
                  outline: "none"
                }}
              />
              <input
                type="text"
                placeholder="Nome Azienda (es. RWE AG)"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                style={{
                  padding: "0.4rem 0.6rem",
                  borderRadius: "8px",
                  backgroundColor: "rgba(12, 28, 48, 0.8)",
                  border: "1px solid rgba(184, 216, 246, 0.2)",
                  color: "#ffffff",
                  fontSize: "0.84rem",
                  outline: "none"
                }}
              />
              {selectedMarket.startsWith("WL:") && (
                <select
                  value={sourceMarket}
                  onChange={(e) => setSourceMarket(e.target.value)}
                  style={{
                    padding: "0.4rem 0.6rem",
                    borderRadius: "8px",
                    backgroundColor: "rgba(12, 28, 48, 0.8)",
                    border: "1px solid rgba(184, 216, 246, 0.2)",
                    color: "#ffffff",
                    fontSize: "0.84rem",
                    outline: "none",
                    cursor: "pointer"
                  }}
                >
                  <option value="MIB30">MIB30</option>
                  <option value="DAX">DAX</option>
                  <option value="ETF">ETF</option>
                  <option value="ETC">ETC</option>
                  <option value="Preferite">Preferite</option>
                  <option value="US_Others">DOW/NASDAQ</option>
                  <option value="Crypto">Crypto</option>
                </select>
              )}
            </div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn"
              style={{ padding: "0.35rem", fontSize: "0.82rem", height: "32px", fontWeight: "bold", cursor: "pointer" }}
            >
              {isSubmitting ? "⏳ AGGIUNTA IN CORSO..." : "➕ AGGIUNGI TITOLO ALLA LISTA"}
            </button>
          </form>
        </div>
      </section>

      {/* 2. List Content Card */}
      <section className="card" style={{ padding: "1rem" }}>
        <h3 className="list-content-heading" style={{ margin: "0 0 0.6rem 0", fontSize: "1rem", color: "#cfe5fa", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div className="list-heading-primary" style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <span>📋 Titoli Correnti ({items.length})</span>
            {selectedTickers.length > 0 && (
              <button
                onClick={handleBulkRemove}
                disabled={removingTicker !== null}
                className="btn text-danger"
                style={{
                  padding: "0.2rem 0.6rem",
                  fontSize: "0.78rem",
                  height: "28px",
                  background: "rgba(239, 68, 68, 0.2)",
                  border: "1px solid rgba(239, 68, 68, 0.4)",
                  color: "#fca5a5",
                  fontWeight: "bold",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.3rem"
                }}
              >
                🗑️ Elimina selezionati ({selectedTickers.length})
              </button>
            )}
          </div>
          <div className="list-heading-meta" style={{ display: "flex", alignItems: "center", gap: "0.65rem", fontSize: "0.78rem", color: "#8cb4d9", fontWeight: "normal" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              Ordina:
              <select
                value={sortOrder}
                onChange={(event) => setSortOrder(event.target.value as typeof sortOrder)}
                style={{
                  padding: "0.28rem 0.45rem", borderRadius: "7px", color: "#dbeafe",
                  background: "#0c1c30", border: "1px solid rgba(184,216,246,0.25)"
                }}
              >
                <option value="ticker_asc">Ticker A → Z</option>
                <option value="ticker_desc">Ticker Z → A</option>
                <option value="name_asc">Nome A → Z</option>
                <option value="name_desc">Nome Z → A</option>
              </select>
            </label>
            <span>Lista: <code>{selectedMarket}</code></span>
          </div>
        </h3>

        {isLoading ? (
          <div style={{ textAlign: "center", padding: "2rem" }}>
            <span style={{ fontSize: "1.05rem" }}>⏳ Caricamento dei titoli della lista...</span>
          </div>
        ) : error ? (
          <div style={{ padding: "1rem", borderRadius: "12px", border: "1px solid rgba(239,68,68,0.2)", backgroundColor: "rgba(239,68,68,0.06)", color: "#fca5a5", fontSize: "0.88rem" }}>
            {error}
          </div>
        ) : items.length === 0 ? (
          <div style={{ padding: "2rem", textAlign: "center", background: "rgba(18, 32, 57, 0.2)", borderRadius: "12px", border: "1px dashed rgba(184, 216, 246, 0.15)", color: "#8cb4d9" }}>
            Nessun titolo presente in questa lista. Usa il modulo sopra per aggiungere il tuo primo titolo!
          </div>
        ) : (
          <div className="table-wrap managed-tickers-wrap" style={{ maxHeight: "400px" }}>
            <table className="managed-tickers-table">
              <thead>
                <tr>
                  <th style={{ width: "5%", textAlign: "center" }}>
                    <input
                      type="checkbox"
                      checked={items.length > 0 && selectedTickers.length === items.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedTickers(items.map((x) => x.Ticker));
                        } else {
                          setSelectedTickers([]);
                        }
                      }}
                      style={{ cursor: "pointer", width: "16px", height: "16px" }}
                    />
                  </th>
                  <th style={{ width: "22%" }}>Ticker</th>
                  <th style={{ width: "43%" }}>Nome Titolo</th>
                  {selectedMarket.startsWith("WL:") && <th style={{ width: "20%" }}>Mercato Origine</th>}
                  <th style={{ width: "10%", textAlign: "center" }}>Azione</th>
                </tr>
              </thead>
              <tbody>
                {orderedItems.map((row) => (
                  <tr key={row.Ticker} style={{ transition: "background-color 0.2s" }}>
                    <td className="managed-select" style={{ textAlign: "center" }}>
                      <input
                        type="checkbox"
                        checked={selectedTickers.includes(row.Ticker)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedTickers((prev) => [...prev, row.Ticker]);
                          } else {
                            setSelectedTickers((prev) => prev.filter((x) => x !== row.Ticker));
                          }
                        }}
                        style={{ cursor: "pointer", width: "16px", height: "16px" }}
                      />
                    </td>
                    <td className="managed-ticker" style={{ fontWeight: "bold", color: "#ffffff", fontSize: "0.9rem" }}>{row.Ticker}</td>
                    <td className="managed-name" style={{ color: "#b8d4ee", fontSize: "0.88rem" }}>{row.Name}</td>
                    {selectedMarket.startsWith("WL:") && (
                      <td className="managed-market">
                        <span style={{
                          padding: "0.15rem 0.45rem",
                          borderRadius: "6px",
                          fontSize: "0.75rem",
                          fontWeight: "bold",
                          background: "rgba(96, 165, 250, 0.15)",
                          border: "1px solid rgba(96, 165, 250, 0.3)",
                          color: "#60a5fa"
                        }}>
                          {row.Source_Market}
                        </span>
                      </td>
                    )}
                    <td className="managed-action" style={{ textAlign: "center" }}>
                      <button
                        className="btn ghost text-danger"
                        disabled={removingTicker === row.Ticker || removingTicker === "BULK"}
                        onClick={() => handleRemoveTicker(row.Ticker, row.Source_Market)}
                        style={{
                          padding: "0.2rem 0.5rem",
                          fontSize: "0.76rem",
                          height: "26px",
                          background: "rgba(239, 68, 68, 0.08)",
                          border: "1px solid rgba(239, 68, 68, 0.2)",
                          color: "#fca5a5",
                          cursor: "pointer"
                        }}
                        title="Rimuovi questo ticker dalla lista"
                      >
                        {removingTicker === row.Ticker ? "⏳..." : "✕ Rimuovi"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
