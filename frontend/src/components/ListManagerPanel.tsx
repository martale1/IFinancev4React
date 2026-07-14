import { useState, useEffect } from "react";

interface ListManagerPanelProps {
  initialMarket: string;
  markets: string[];
}

interface TickerItem {
  Ticker: string;
  Name: string;
  Source_Market?: string;
}

export default function ListManagerPanel({ initialMarket, markets }: ListManagerPanelProps) {
  const [selectedMarket, setSelectedMarket] = useState(initialMarket || "Preferite");
  const [items, setItems] = useState<TickerItem[]>([]);
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
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Automatically hide toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

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
    setRegenerating(true);
    try {
      const res = await fetch("/api/watchlist/regenerate", { method: "POST" });
      if (!res.ok) {
        throw new Error(`Errore nell'avvio: ${res.statusText}`);
      }
      setToast({ 
        message: "⚡ Calcolo e rigenerazione avviati in background! Le analisi si aggiorneranno automaticamente nei prossimi minuti.", 
        type: "success" 
      });
    } catch (err: any) {
      setToast({ message: err.message || "Errore sconosciuto nell'avvio dei calcoli.", type: "error" });
    } finally {
      setRegenerating(false);
    }
  }

  return (
    <div style={{ marginTop: "1rem", display: "grid", gap: "1.5rem" }}>
      {/* Toast Notification */}
      {toast && (
        <div style={{
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h2 style={{ fontSize: "1.25rem", margin: 0, color: "#ffffff" }}>📂 Gestore Database e Liste Titoli (Excel & JSON)</h2>
            <p style={{ fontSize: "0.85rem", color: "#8cb4d9", margin: "0.2rem 0 0 0" }}>
              Visualizza, aggiungi o rimuovi titoli dai file Excel sorgenti (`preferite.xlsx`, `validtickers_DE_DAX.xlsx`, ecc.) e dalle watchlists della GUI.
            </p>
          </div>
          <button
            className="btn"
            disabled={regenerating}
            onClick={handleRegenerate}
            style={{ 
              height: "40px", 
              background: "linear-gradient(135deg, #fbbf24 0%, #d97706 100%)", 
              border: "1px solid rgba(251,191,36,0.3)",
              fontWeight: "bold",
              color: "#050b14",
              display: "flex",
              alignItems: "center",
              gap: "0.4rem",
              cursor: "pointer"
            }}
          >
            {regenerating ? "⏳ AVVIO..." : "⚡ RIGENERA ANALISI DATABASE (main.py)"}
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem", marginTop: "0.5rem" }}>
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
            <div style={{ display: "grid", gridTemplateColumns: selectedMarket.startsWith("WL:") ? "1fr 1.2fr 1fr" : "1fr 1.5fr", gap: "0.5rem" }}>
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
        <h3 style={{ margin: "0 0 0.6rem 0", fontSize: "1rem", color: "#cfe5fa", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
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
          <span style={{ fontSize: "0.78rem", color: "#8cb4d9", fontWeight: "normal" }}>
            Lista: <code>{selectedMarket}</code>
          </span>
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
          <div className="table-wrap" style={{ maxHeight: "400px" }}>
            <table>
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
                {items.map((row) => (
                  <tr key={row.Ticker} style={{ transition: "background-color 0.2s" }}>
                    <td style={{ textAlign: "center" }}>
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
                    <td style={{ fontWeight: "bold", color: "#ffffff", fontSize: "0.9rem" }}>{row.Ticker}</td>
                    <td style={{ color: "#b8d4ee", fontSize: "0.88rem" }}>{row.Name}</td>
                    {selectedMarket.startsWith("WL:") && (
                      <td>
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
                    <td style={{ textAlign: "center" }}>
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
