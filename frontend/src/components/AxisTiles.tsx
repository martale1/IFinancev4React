import type { WatchlistRow } from "../types";
import { ANELLO_INDICAZIONE, ANELLO_FASE, ANELLO_RISCHIO, ruota } from "../ranking";

export type AxisTileKind = "fase" | "indicazione" | "rischio";

/** Valore messo in testa all'ordinamento. */
export type AxisTileSelection = { kind: AxisTileKind; value: string };


/**
 * Tessere riassuntive dei quattro assi: quante fasi, quante indicazioni, quanti
 * livelli di rischio. Usate dal Monitor e dalla tab All, cosi' i due posti non
 * possono divergere.
 *
 * Il clic NON filtra: porta quel valore in testa all'ordinamento e gli altri lo
 * seguono. I conteggi riguardano sempre tutti i titoli passati.
 */
function conta(items: WatchlistRow[], campo: string, valore: string): number {
  return items.filter((row) => String(row[campo] ?? "").toUpperCase() === valore).length;
}

/** Classe di colore di una tessera, con gli stessi colori della tabella. */
function classeColore(kind: AxisTileKind, valore: string): string {
  const v = valore.toUpperCase();
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

export function AxisTiles({
  items,
  onSelect,
  active = null,
  disabled = false,
  nota,
}: {
  items: WatchlistRow[];
  onSelect?: (selection: AxisTileSelection) => void;
  /** Valore attualmente in testa all'ordinamento, se scelto. */
  active?: AxisTileSelection | null;
  /** Con elenco paginato i conteggi sarebbero parziali: meglio dirlo. */
  disabled?: boolean;
  nota?: string;
}) {
  if (!items.length) return null;

  const inTesta = (kind: AxisTileKind, value: string) => active?.kind === kind && active.value === value;

  const gruppo = (etichetta: string, kind: AxisTileKind, campo: string) => {
    // Tutte le dimensioni si mostrano nell'ordine che avranno i titoli: cosi'
    // cliccandone una si vede subito dove finisce, perche' si sposta in testa.
    // Vale per Indicazione, Fase e Rischio, non solo per l'indicazione.
    const anello = kind === "fase" ? ANELLO_FASE : kind === "rischio" ? ANELLO_RISCHIO : ANELLO_INDICAZIONE;
    const inTestaOra = active?.kind === kind ? active.value : anello[0];
    const ordine = ruota(anello, inTestaOra);
    return (
      <div className="monitor-tile-group">
        <span className="monitor-tile-label">{etichetta}</span>
        {ordine.map((valore) => {
          const n = conta(items, campo, valore);
          const isTesta = inTesta(kind, valore);
          return (
            <button
              type="button"
              key={valore}
              className={`monitor-tile ${classeColore(kind, valore)} ${isTesta ? "in-testa" : ""}`}
              disabled={disabled}
              onClick={() => onSelect?.({ kind, value: valore })}
              title={
                disabled
                  ? `${n} titoli con ${etichetta.toLowerCase()} ${valore}`
                  : `Metti ${valore} in testa all'ordine (${n} titoli)`
              }
            >
              {isTesta ? "▼ " : null}
              <b>{n}</b> {valore}
            </button>
          );
        })}
      </div>
    );
  };

  return (
    <div className="monitor-tile-groups">
      {gruppo("Fase", "fase", "Market_Phase")}
      {gruppo("Indicazione", "indicazione", "Entry_Signal")}
      {gruppo("Rischio", "rischio", "Rischio_Trend")}
      {nota ? <span className="monitor-tile-nota">{nota}</span> : null}
    </div>
  );
}
