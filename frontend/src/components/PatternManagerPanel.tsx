import { useState, useEffect } from "react";

interface CustomPattern {
  id: string;
  label: string;
  desc: string;
  query: string;
  color: string;
}

const PRESET_COLORS = [
  { hex: "#10b981", name: "Verde Smeraldo" },
  { hex: "#38bdf8", name: "Azzurro Sky" },
  { hex: "#f43f5e", name: "Rosa/Rosso Rose" },
  { hex: "#eab308", name: "Giallo Oro" },
  { hex: "#a78bfa", name: "Viola Lavanda" },
  { hex: "#f97316", name: "Arancione Rust" },
  { hex: "#ec4899", name: "Fucsia Shock" },
  { hex: "#6b7280", name: "Grigio Ardesia" },
];

export default function PatternManagerPanel() {
  const [patterns, setPatterns] = useState<CustomPattern[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [isEditing, setIsEditing] = useState(false);
  const [formId, setFormId] = useState("");
  const [formLabel, setFormLabel] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formQuery, setFormQuery] = useState("");
  const [formColor, setFormColor] = useState("#10b981");

  const [isSaving, setIsSaving] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Automatically hide toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Fetch list items
  async function fetchPatterns() {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/scanner/custom-patterns");
      if (!res.ok) throw new Error("Impossibile caricare i pattern.");
      const data = await res.json();
      setPatterns(data.patterns || []);
    } catch (err: any) {
      setError(err.message || "Errore nel caricamento dei pattern.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchPatterns();
  }, []);

  // Handle Edit click
  function startEdit(pat: CustomPattern) {
    setIsEditing(true);
    setFormId(pat.id);
    setFormLabel(pat.label);
    setFormDesc(pat.desc);
    setFormQuery(pat.query);
    setFormColor(pat.color);
  }

  // Handle Clear / New Pattern
  function startNew() {
    setIsEditing(false);
    setFormId("");
    setFormLabel("");
    setFormDesc("");
    setFormQuery("");
    setFormColor("#10b981");
  }

  // Handle Save
  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!formId.trim() || !formLabel.trim() || !formQuery.trim()) {
      setToast({ message: "ID, Nome e Formula Query sono campi obbligatori.", type: "error" });
      return;
    }

    // Auto-sanitizzazione ID
    const sanitizedId = formId
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "_")
      .replace(/[^a-z0-9_-]/g, "");

    if (!sanitizedId) {
      setToast({ message: "ID pattern non valido (usa solo lettere, numeri, trattini e underscore).", type: "error" });
      return;
    }

    setIsSaving(true);
    try {
      const res = await fetch("/api/scanner/custom-patterns/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: sanitizedId,
          label: formLabel.trim(),
          desc: formDesc.trim(),
          query: formQuery.trim(),
          color: formColor,
        }),
      });

      if (!res.ok) throw new Error("Salvataggio fallito.");

      setToast({ message: `Pattern "${formLabel}" salvato correttamente!`, type: "success" });
      startNew();
      fetchPatterns();
    } catch (err: any) {
      setToast({ message: err.message || "Errore durante il salvataggio.", type: "error" });
    } finally {
      setIsSaving(false);
    }
  }

  // Handle Delete
  async function handleDelete(patId: string, patLabel: string) {
    if (!confirm(`Sei sicuro di voler eliminare definitivamente il pattern "${patLabel}"?`)) {
      return;
    }

    try {
      const res = await fetch(`/api/scanner/custom-patterns/${encodeURIComponent(patId)}`, {
        method: "DELETE",
      });

      if (!res.ok) throw new Error("Eliminazione fallita.");

      setToast({ message: `Pattern "${patLabel}" eliminato con successo.`, type: "success" });
      if (formId === patId) {
        startNew();
      }
      fetchPatterns();
    } catch (err: any) {
      setToast({ message: err.message || "Errore durante l'eliminazione.", type: "error" });
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.2rem", marginTop: "1rem" }}>
      {/* Toast Alert */}
      {toast && (
        <div
          style={{
            position: "fixed",
            bottom: "20px",
            right: "20px",
            zIndex: 1000,
            padding: "0.8rem 1.2rem",
            borderRadius: "10px",
            backgroundColor: toast.type === "success" ? "#065f46" : "#7f1d1d",
            border: `1px solid ${toast.type === "success" ? "#059669" : "#dc2626"}`,
            color: "#ffffff",
            boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.4)",
            animation: "fadeIn 0.2s ease-out",
          }}
        >
          {toast.type === "success" ? "✅ " : "❌ "}
          {toast.message}
        </div>
      )}

      {/* ══════════════ LEFT PANE: PATTERNS LIST ══════════════ */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div className="watchlist-card" style={{ padding: "1.2rem", display: "flex", flexDirection: "column", gap: "0.8rem", height: "100%" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ margin: 0, color: "#ffffff", fontSize: "1.1rem" }}>📋 Pattern Personalizzati Attuali</h3>
            <button
              onClick={startNew}
              style={{
                padding: "0.35rem 0.6rem",
                borderRadius: "8px",
                border: "none",
                background: "rgba(96, 165, 250, 0.15)",
                color: "#60a5fa",
                fontSize: "0.78rem",
                fontWeight: 700,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              ➕ Nuovo
            </button>
          </div>

          {isLoading && <p style={{ fontSize: "0.85rem", color: "#8cb4d9" }}>Caricamento in corso...</p>}
          {error && <p style={{ fontSize: "0.85rem", color: "#fca5a5" }}>{error}</p>}

          {!isLoading && !error && patterns.length === 0 && (
            <div style={{ padding: "2rem 1rem", textAlign: "center", border: "1px dashed rgba(184, 216, 246, 0.15)", borderRadius: "10px" }}>
              <p style={{ color: "#8cb4d9", fontSize: "0.82rem", margin: 0 }}>Nessun pattern personalizzato trovato.</p>
              <p style={{ color: "#b8d4ee", fontSize: "0.78rem", marginTop: "0.4rem" }}>Creane uno usando il modulo a destra!</p>
            </div>
          )}

          {!isLoading && !error && patterns.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem", overflowY: "auto", maxHeight: "550px" }}>
              {patterns.map((pat) => (
                <div
                  key={pat.id}
                  style={{
                    padding: "0.9rem",
                    borderRadius: "12px",
                    background: "rgba(10, 25, 47, 0.45)",
                    border: `1px solid ${pat.color}35`,
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.4rem",
                    transition: "transform 0.2s, border-color 0.2s",
                    position: "relative",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span
                        style={{
                          display: "inline-block",
                          width: "8px",
                          height: "8px",
                          borderRadius: "50%",
                          backgroundColor: pat.color,
                        }}
                      />
                      <strong style={{ color: "#ffffff", fontSize: "0.9rem" }}>{pat.label}</strong>
                      <span style={{ fontSize: "0.7rem", color: "#8cb4d9", background: "rgba(184,216,246,0.08)", padding: "0.1rem 0.3rem", borderRadius: "4px" }}>
                        {pat.id}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: "0.3rem" }}>
                      <button
                        onClick={() => startEdit(pat)}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "#60a5fa",
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          cursor: "pointer",
                          padding: "0.2rem 0.4rem",
                        }}
                      >
                        Modifica
                      </button>
                      <button
                        onClick={() => handleDelete(pat.id, pat.label)}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "#ef4444",
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          cursor: "pointer",
                          padding: "0.2rem 0.4rem",
                        }}
                      >
                        Elimina
                      </button>
                    </div>
                  </div>

                  {pat.desc && <p style={{ fontSize: "0.8rem", color: "#b8d4ee", margin: "0.1rem 0" }}>{pat.desc}</p>}

                  <div style={{ marginTop: "0.3rem" }}>
                    <span style={{ fontSize: "0.7rem", color: "#8cb4d9", textTransform: "uppercase", fontWeight: 700, display: "block" }}>Formula Pandas Query:</span>
                    <code
                      style={{
                        display: "block",
                        fontFamily: "monospace",
                        fontSize: "0.78rem",
                        color: "#fbbf24",
                        padding: "0.35rem 0.5rem",
                        background: "rgba(0, 0, 0, 0.25)",
                        borderRadius: "6px",
                        marginTop: "0.15rem",
                        wordBreak: "break-all",
                      }}
                    >
                      {pat.query}
                    </code>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ══════════════ RIGHT PANE: FORM & CHEAT SHEET ══════════════ */}
      <div style={{ display: "flex", flexDirection: "column", gap: "1.2rem" }}>
        {/* Form Card */}
        <div className="watchlist-card" style={{ padding: "1.2rem" }}>
          <h3 style={{ margin: "0 0 1rem 0", color: "#ffffff", fontSize: "1.1rem" }}>
            {isEditing ? `📝 Modifica Pattern: ${formLabel}` : "➕ Crea Nuovo Pattern"}
          </h3>

          <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
            {/* ID */}
            <div>
              <label style={{ fontSize: "0.78rem", color: "#cfe5fa", fontWeight: 700, display: "block", marginBottom: "0.25rem" }}>
                ID Pattern (univoco, minuscolo senza spazi) <span style={{ color: "#ef4444" }}>*</span>
              </label>
              <input
                type="text"
                placeholder="es: custom_rsi_cross"
                value={formId}
                onChange={(e) => setFormId(e.target.value)}
                disabled={isEditing}
                style={{
                  width: "100%",
                  padding: "0.45rem 0.6rem",
                  borderRadius: "8px",
                  backgroundColor: isEditing ? "rgba(12,28,48,0.3)" : "rgba(12,28,48,0.7)",
                  border: "1px solid rgba(184,216,246,0.2)",
                  color: isEditing ? "#8cb4d9" : "#ffffff",
                  fontSize: "0.85rem",
                  outline: "none",
                }}
                required
              />
            </div>

            {/* Label */}
            <div>
              <label style={{ fontSize: "0.78rem", color: "#cfe5fa", fontWeight: 700, display: "block", marginBottom: "0.25rem" }}>
                Nome Visualizzato <span style={{ color: "#ef4444" }}>*</span>
              </label>
              <input
                type="text"
                placeholder="es: RSI Oversold Crossover"
                value={formLabel}
                onChange={(e) => setFormLabel(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.45rem 0.6rem",
                  borderRadius: "8px",
                  backgroundColor: "rgba(12,28,48,0.7)",
                  border: "1px solid rgba(184,216,246,0.2)",
                  color: "#ffffff",
                  fontSize: "0.85rem",
                  outline: "none",
                }}
                required
              />
            </div>

            {/* Desc */}
            <div>
              <label style={{ fontSize: "0.78rem", color: "#cfe5fa", fontWeight: 700, display: "block", marginBottom: "0.25rem" }}>
                Descrizione Strategia
              </label>
              <input
                type="text"
                placeholder="es: RSI < 30 e incrocio stocastico nei minimi"
                value={formDesc}
                onChange={(e) => setFormDesc(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.45rem 0.6rem",
                  borderRadius: "8px",
                  backgroundColor: "rgba(12,28,48,0.7)",
                  border: "1px solid rgba(184,216,246,0.2)",
                  color: "#ffffff",
                  fontSize: "0.85rem",
                  outline: "none",
                }}
              />
            </div>

            {/* Query */}
            <div>
              <label style={{ fontSize: "0.78rem", color: "#cfe5fa", fontWeight: 700, display: "block", marginBottom: "0.25rem" }}>
                Formula Query (Sintassi Pandas) <span style={{ color: "#ef4444" }}>*</span>
              </label>
              <input
                type="text"
                placeholder="es: RSI < 30 and Stoch_K > Stoch_D"
                value={formQuery}
                onChange={(e) => setFormQuery(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.55rem 0.6rem",
                  borderRadius: "8px",
                  backgroundColor: "rgba(12,28,48,0.7)",
                  border: "1px solid rgba(184,216,246,0.25)",
                  color: "#ffffff",
                  fontFamily: "monospace",
                  fontSize: "0.88rem",
                  outline: "none",
                }}
                required
              />
            </div>

            {/* Color */}
            <div>
              <label style={{ fontSize: "0.78rem", color: "#cfe5fa", fontWeight: 700, display: "block", marginBottom: "0.4rem" }}>
                Colore Badge / Tab
              </label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
                {PRESET_COLORS.map((c) => {
                  const active = formColor === c.hex;
                  return (
                    <button
                      key={c.hex}
                      type="button"
                      title={c.name}
                      onClick={() => setFormColor(c.hex)}
                      style={{
                        width: "24px",
                        height: "24px",
                        borderRadius: "50%",
                        backgroundColor: c.hex,
                        border: active ? "2.5px solid #ffffff" : "1px solid rgba(255,255,255,0.2)",
                        cursor: "pointer",
                        boxShadow: active ? "0 0 8px rgba(255,255,255,0.4)" : "none",
                        transition: "all 0.15s ease",
                      }}
                    />
                  );
                })}
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
              <button
                type="submit"
                disabled={isSaving}
                className="btn-accent"
                style={{ flex: 1, padding: "0.55rem", border: "none", borderRadius: "8px", fontWeight: 700, cursor: "pointer" }}
              >
                {isSaving ? "Salvataggio..." : "Salva Pattern"}
              </button>
              {isEditing && (
                <button
                  type="button"
                  onClick={startNew}
                  style={{
                    padding: "0.55rem 1rem",
                    border: "1px solid rgba(184,216,246,0.2)",
                    borderRadius: "8px",
                    background: "transparent",
                    color: "#b8d4ee",
                    fontSize: "0.82rem",
                    cursor: "pointer",
                  }}
                >
                  Annulla
                </button>
              )}
            </div>
          </form>
        </div>

        {/* Cheat Sheet Guide Accordion */}
        <div className="guide-card" style={{ padding: "0.8rem 1rem" }}>
          <details>
            <summary style={{ fontSize: "0.82rem", fontWeight: 700, color: "#ffffff", cursor: "pointer" }}>
              💡 Cheat-Sheet: Colonne e Operatori Disponibili
            </summary>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", marginTop: "0.6rem", fontSize: "0.78rem", color: "#b8d4ee" }}>
              <div>
                <strong style={{ color: "#ffffff" }}>Prezzo e Volumi:</strong>
                <p style={{ margin: "0.1rem 0 0 0" }}>
                  <code>Close</code>, <code>Open</code>, <code>High</code>, <code>Low</code>, <code>Volume</code>
                </p>
              </div>
              <div>
                <strong style={{ color: "#ffffff" }}>Medie Mobili:</strong>
                <p style={{ margin: "0.1rem 0 0 0" }}>
                  <code>EMA_30</code>, <code>EMA_50</code>, <code>SMA200</code>, <code>EMA_9</code>, <code>EMA_21</code>, <code>Volume_MA20</code>
                </p>
              </div>
              <div>
                <strong style={{ color: "#ffffff" }}>Oscillatori e MACD:</strong>
                <p style={{ margin: "0.1rem 0 0 0" }}>
                  <code>RSI</code>, <code>Stoch_K</code>, <code>Stoch_D</code>, <code>Williams_R</code>, <code>ADX</code>, <code>MACD</code>, <code>MACD_Signal</code>, <code>MACD_Hist</code>
                </p>
              </div>
              <div>
                <strong style={{ color: "#ffffff" }}>Variabili Shiftate (1 giorno fa):</strong>
                <p style={{ margin: "0.1rem 0 0 0" }}>
                  <code>RSI_shift1</code>, <code>Stoch_K_shift1</code>, <code>Stoch_D_shift1</code>, <code>Williams_R_shift1</code>, <code>MACD_shift1</code>
                </p>
              </div>
              <div>
                <strong style={{ color: "#ffffff" }}>Differenze Calcolate:</strong>
                <p style={{ margin: "0.1rem 0 0 0" }}>
                  <code>Stoch_KvsD</code> (K - D), <code>DI_diff</code> (PLUS_DI - MINUS_DI)
                </p>
              </div>
              <div>
                <strong style={{ color: "#ffffff" }}>Alligator Trend State (Signal6):</strong>
                <p style={{ margin: "0.1rem 0 0 0" }}>
                  <code>Signal6</code> (valori: <code>'Uptrend'</code>, <code>'Uptrend-'</code>, <code>'Downtrend'</code>, <code>'sleep1'</code> etc.)
                </p>
              </div>
              <hr style={{ border: "none", borderTop: "1px solid rgba(184,216,246,0.1)", margin: "0.3rem 0" }} />
              <div>
                <strong style={{ color: "#ffffff" }}>Esempi Pratici di Formule:</strong>
                <ul style={{ margin: "0.2rem 0 0 0", paddingLeft: "1.2rem" }}>
                  <li style={{ marginBottom: "0.25rem" }}>
                    <code>{"RSI < 30 and Stoch_K > Stoch_D"}</code>
                  </li>
                  <li style={{ marginBottom: "0.25rem" }}>
                    <code>{"EMA_30 > EMA_50 and ADX > 25"}</code>
                  </li>
                  <li style={{ marginBottom: "0.25rem" }}>
                    <code>{"Close > SAR and (Signal6 == 'Uptrend' or Signal6 == 'Uptrend*')"}</code>
                  </li>
                  <li style={{ marginBottom: "0.25rem" }}>
                    <code>{"Close > Open and Volume > Volume_MA20 * 1.5"}</code>
                  </li>
                </ul>
              </div>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
}
