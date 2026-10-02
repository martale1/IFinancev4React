import { useEffect, useState } from "react";
import type { WatchlistRow } from "../types";

type Props = {
  open: boolean;
  row: WatchlistRow | null;
  existingNote?: string;
  isMonitored?: boolean;
  onSave: (ticker: string, sourceMarket: string, note: string, name?: string) => Promise<void>;
  onRemove?: (ticker: string, sourceMarket: string) => Promise<void>;
  onClose: () => void;
};

const SUGGESTIONS = [
  "Monitorare breakout sopra resistenza",
  "Possibile ripartenza dopo pullback",
  "Attendere conferma incrocio MACD",
  "Verificare tenuta supporto principale",
  "RSI in ipervenduto - in osservazione",
  "In attesa dei risultati societari/news",
];

export default function MonitorNoteModal({
  open,
  row,
  existingNote = "",
  isMonitored = false,
  onSave,
  onRemove,
  onClose,
}: Props) {
  const [note, setNote] = useState(existingNote);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setNote(existingNote);
    setError("");
  }, [open, existingNote, row]);

  if (!open || !row) return null;

  const ticker = String(row.Ticker || "").trim();
  const name = String(row.Name || ticker);
  const sourceMarket = String(row.WL_Source_Market || row.Market || "MIB30");

  const handleSave = async () => {
    try {
      setSaving(true);
      setError("");
      await onSave(ticker, sourceMarket, note.trim(), name);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore durante il salvataggio");
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async () => {
    if (!onRemove) return;
    try {
      setSaving(true);
      setError("");
      await onRemove(ticker, sourceMarket);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore durante la rimozione");
    } finally {
      setSaving(false);
    }
  };

  const handleAddSuggestion = (text: string) => {
    setNote((prev) => (prev ? `${prev}; ${text}` : text));
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 520 }}>
        <div className="modal-header">
          <div>
            <h3 style={{ margin: 0 }}>
              🎯 {isMonitored ? "Modifica Monitor" : "Aggiungi a Monitor"}
            </h3>
            <div style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginTop: 4 }}>
              <strong>{ticker}</strong> - {name} ({sourceMarket})
            </div>
          </div>
          <button className="btn-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {error && <div className="error-banner">{error}</div>}

          <div>
            <label style={{ display: "block", marginBottom: 6, fontWeight: 600, fontSize: "0.85rem" }}>
              Nota manuale operativa (opzionale):
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Es: Monitorare breakout sopra 12.20; supporto 11.50..."
              rows={4}
              style={{
                width: "100%",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid var(--border-color, #333)",
                background: "var(--bg-input, #1e1e1e)",
                color: "var(--text-main, #fff)",
                resize: "vertical",
                fontSize: "0.9rem",
              }}
            />
          </div>

          <div>
            <label style={{ display: "block", marginBottom: 6, fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Suggerimenti rapidi:
            </label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {SUGGESTIONS.map((text) => (
                <button
                  key={text}
                  type="button"
                  className="quick-bar"
                  onClick={() => handleAddSuggestion(text)}
                  style={{ fontSize: "0.78rem", padding: "3px 8px" }}
                >
                  + {text}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="modal-footer" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
          {isMonitored && onRemove ? (
            <button
              type="button"
              className="btn danger"
              onClick={handleRemove}
              disabled={saving}
              style={{ padding: "6px 14px", fontSize: "0.85rem" }}
            >
              🗑️ Rimuovi da Monitor
            </button>
          ) : <div />}

          <div style={{ display: "flex", gap: 8 }}>
            <button type="button" className="btn ghost" onClick={onClose} disabled={saving}>
              Annulla
            </button>
            <button type="button" className="btn primary" onClick={handleSave} disabled={saving}>
              {saving ? "Salvataggio..." : "Salva"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
