import type { WatchlistRow } from "../types";

export type AxisTileKind = "fase" | "indicazione" | "rischio";

export type AxisTileSelection = { kind: AxisTileKind; value: string };

/**
 * Tessere riassuntive dei quattro assi: quante fasi, quante indicazioni, quanti
 * livelli di rischio. Usate dal Monitor e dalla tab All, così i due posti non
 * possono divergere (prima il Monitor aveva tessere proprie e All nessuna).
 *
 * I conteggi riguardano SEMPRE tutti i titoli passati: cliccare una tessera
 * filtra l'elenco ma non cambia i numeri, altrimenti sembrerebbe che il mercato
 * sia cambiato.
 */
const FASI = ["TENDENZA", "RIPRESA", "LATERALE", "RIBASSO"] as const;
const INDICAZIONI = ["ENTRA", "OSSERVA", "ATTENDI", "EVITA"] as const;
const RISCHI = ["NORMALE", "TESO", "ESTREMO"] as const;

/**
 * Classe di colore di una tessera, per tipo e valore.
 *
 * Gli stessi colori della tabella: cosi' "ENTRA" e' verde sia nella tessera sia
 * nella riga, e il colore significa la stessa cosa nei due posti.
 */
function classeColore(kind: AxisTileKind, valore: string): string {
  const v = valore.toUpperCase();
  // Indicazioni: sono le stesse classi usate dalla tabella.
  if (kind === "indicazione") {
    if (v === "ENTRA") return "tile-enter";
    if (v === "OSSERVA") return "tile-watch";
    if (v === "EVITA") return "tile-avoid";
    return "tile-wait";
  }
  if (kind === "fase") {
    if (v === "TENDENZA") return "tile-enter";
    if (v === "RIPRESA") return "tile-watch";
    if (v === "RIBASSO") return "tile-avoid";
    return "tile-wait";
  }
  // Rischio: TESO e' un avvertimento, non un pericolo pieno.
  if (v === "NORMALE") return "tile-enter";
  if (v === "TESO") return "tile-warn";
  return "tile-avoid";
}

function conta(items: WatchlistRow[], campo: string, valore: string): number {
  return items.filter((row) => String(row[campo] ?? "").toUpperCase() === valore).length;
}

export function AxisTiles({
  items,
  onSelect,
  active = null,
  disabled = false,
  nota,
}: {
  items: WatchlistRow[];
  onSelect?: (selection: AxisTileSelection) => void;
  active?: AxisTileSelection | null;
  /** Con elenco paginato i conteggi sarebbero parziali: meglio dirlo. */
  disabled?: boolean;
  nota?: string;
}) {
  if (!items.length) return null;

  const attivo = (kind: AxisTileKind, value: string) => active?.kind === kind && active.value === value;
  const clic = (kind: AxisTileKind, value: string, n: number) => {
    if (!onSelect || disabled || !n) return;
    onSelect({ kind, value });
  };

  const gruppo = (etichetta: string, kind: AxisTileKind, campo: string, valori: readonly string[]) => (
    <div className="monitor-tile-group">
      <span className="monitor-tile-label">{etichetta}</span>
      {valori.map((valore) => {
        const n = conta(items, campo, valore);
        const isActive = attivo(kind, valore);
        return (
          <button
            type="button"
            key={valore}
            className={`monitor-tile ${classeColore(kind, valore)} ${isActive ? "active" : ""}`}
            disabled={disabled || !n}
            onClick={() => clic(kind, valore, n)}
            title={
              disabled
                ? `${n} titoli con ${etichetta.toLowerCase()} ${valore}`
                : n
                  ? `Mostra i ${n} titoli con ${etichetta.toLowerCase()} ${valore}`
                  : `Nessun titolo con ${etichetta.toLowerCase()} ${valore}`
            }
          >
            <b>{n}</b> {valore}
          </button>
        );
      })}
    </div>
  );

  return (
    <div className="monitor-tile-groups">
      {gruppo("Fase", "fase", "Market_Phase", FASI)}
      {gruppo("Indicazione", "indicazione", "Entry_Signal", INDICAZIONI)}
      {gruppo("Rischio", "rischio", "Rischio_Trend", RISCHI)}
      {nota ? <span className="monitor-tile-nota">{nota}</span> : null}
      {active && onSelect ? (
        <button type="button" className="btn ghost monitor-tile-clear" onClick={() => onSelect({ kind: active.kind, value: "" })}>
          ✕ Togli il filtro
        </button>
      ) : null}
    </div>
  );
}
