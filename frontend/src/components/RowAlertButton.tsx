/**
 * Pulsante Alert per le righe della vista Lista.
 *
 * Nelle Schede l'alert si crea da un pannello dentro `WatchlistCard`, che pero'
 * porta con se' molto stato (campo, operatore, valore, presets, alert AI). Qui
 * serve la stessa cosa in forma compatta: pulsante + modulo essenziale, cosi' la
 * Lista non resta l'unica vista senza alert.
 *
 * Riusa gli stessi gestori di App (`onCreateAlert`, `onRemoveAlert`) e la stessa
 * convenzione di `Alert` di `WatchlistCard`: campo, operatore, valore.
 */
import { useState } from "react";

import type { QuickAlertField, WatchlistRow } from "../types";

/** Campi su cui si puo' mettere una condizione: sono quelli del tipo
 *  `QuickAlertField`, cioe' le colonne che il backend sa valutare. */
const CAMPI: Array<{ id: QuickAlertField; label: string }> = [
  { id: "Close", label: "Prezzo" },
  { id: "MACD_vs_Signal", label: "MACD − Signal" },
  { id: "MACD_Hist", label: "MACD istogramma" },
  { id: "RSI", label: "RSI" },
  { id: "Williams_R", label: "Williams %R" },
  { id: "Stoch_K", label: "Stocastico K" },
  { id: "Stoch_D", label: "Stocastico D" },
  { id: "Stoch_KvsD", label: "Stocastico K−D" },
  { id: "ADX", label: "ADX" },
  { id: "PLUS_DI", label: "DI+" },
  { id: "MINUS_DI", label: "DI−" },
  { id: "DI_diff", label: "DI+ − DI−" },
  { id: "SIG_MA_SAR", label: "Segnale SAR" },
  { id: "SAR_Above_Price", label: "SAR sopra il prezzo" },
  { id: "Signal6", label: "Signal6" },
];

const OPERATORI: Array<{ id: ">" | "<" | "==" | "!="; label: string }> = [
  { id: ">", label: "sopra >" },
  { id: "<", label: "sotto <" },
  { id: "==", label: "uguale =" },
  { id: "!=", label: "diverso ≠" },
];

export default function RowAlertButton({
  row,
  sourceMarket,
  alertSet,
  busy,
  onCreate,
  onRemove,
}: {
  row: WatchlistRow;
  sourceMarket: string;
  /** Esiste gia' un alert per questo titolo. */
  alertSet: boolean;
  /** Operazione in corso: il pulsante si blocca. */
  busy: boolean;
  onCreate: (input: {
    row: WatchlistRow;
    source_market: string;
    field: QuickAlertField;
    op: ">" | "<" | "==" | "!=";
    value: number | string;
  }) => Promise<string>;
  onRemove: (input: { row: WatchlistRow; source_market: string }) => Promise<string>;
}) {
  const [aperto, setAperto] = useState(false);
  const [campo, setCampo] = useState<QuickAlertField>("Close");
  const [op, setOp] = useState<">" | "<" | "==" | "!=">(">");
  const [valore, setValore] = useState("");
  const [msg, setMsg] = useState("");
  const [inCorso, setInCorso] = useState(false);

  // Il valore di partenza e' quello attuale del campo scelto: cosi' la soglia si
  // scrive guardando il numero, invece di inventarlo.
  function valoreAttuale(): string {
    const v = (row as Record<string, unknown>)[campo as string];
    return v === null || v === undefined ? "" : String(v);
  }

  async function conferma() {
    if (!valore.trim()) {
      setMsg("Scrivi un valore.");
      return;
    }
    setInCorso(true);
    setMsg("");
    try {
      const esito = await onCreate({ row, source_market: sourceMarket, field: campo, op, value: valore.trim() });
      setMsg(esito || "Alert salvato.");
      setAperto(false);
    } finally {
      setInCorso(false);
    }
  }

  async function rimuovi() {
    setInCorso(true);
    setMsg("");
    try {
      const esito = await onRemove({ row, source_market: sourceMarket });
      setMsg(esito || "Alert rimosso.");
      setAperto(false);
    } finally {
      setInCorso(false);
    }
  }

  return (
    <span className="row-alert">
      <button
        type="button"
        className={alertSet ? "btn alert-on" : "btn ghost"}
        disabled={busy}
        onClick={() => {
          setMsg("");
          setValore(valoreAttuale());
          setAperto((v) => !v);
        }}
        title={alertSet ? "Alert presente: apri per modificare o rimuovere" : "Crea un alert su una condizione"}
      >
        {busy ? "..." : alertSet ? "Alert ON" : "Alert"}
      </button>

      {aperto ? (
        <span className="row-alert-form">
          <select value={campo} onChange={(e) => { setCampo(e.target.value as QuickAlertField); setValore(""); }}>
            {CAMPI.map((c) => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>
          <select value={op} onChange={(e) => setOp(e.target.value as ">" | "<" | "==" | "!=")}>
            {OPERATORI.map((o) => (
              <option key={o.id} value={o.id}>{o.label}</option>
            ))}
          </select>
          <input
            value={valore}
            onChange={(e) => setValore(e.target.value)}
            placeholder={valoreAttuale() || "valore"}
            inputMode="decimal"
          />
          <button type="button" className="btn" disabled={inCorso} onClick={conferma}>
            {inCorso ? "..." : alertSet ? "Aggiorna" : "Crea"}
          </button>
          {alertSet ? (
            <button type="button" className="btn ghost remove-btn" disabled={inCorso} onClick={rimuovi}>
              Rimuovi
            </button>
          ) : null}
        </span>
      ) : null}

      {msg ? <span className="row-alert-msg">{msg}</span> : null}
    </span>
  );
}
