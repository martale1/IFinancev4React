import type { WatchlistRow } from "../types";
import { toNum } from "../format";

/**
 * Ordinamento per variazione percentuale.
 *
 * Stessa logica per il Monitor e il tab All. Il verso naturale e' decrescente —
 * chi sale di piu' in cima — e cliccando due volte si inverte.
 */

export type CampoPercentuale = "PCTV_1D" | "PCTV_5D" | "PCTV_10D" | "PCTV_30D" | "PCTV_180D";

/** I periodi proposti, nell'ordine in cui si leggono. */
export const PERIODI_PERCENTUALE: { key: CampoPercentuale; label: string }[] = [
  { key: "PCTV_1D", label: "1D" },
  { key: "PCTV_5D", label: "5D" },
  { key: "PCTV_10D", label: "10D" },
  { key: "PCTV_30D", label: "30D" },
  { key: "PCTV_180D", label: "180D" },
];

export interface OrdinePercentuale {
  key: CampoPercentuale;
  dir: "asc" | "desc";
}

/**
 * Regola dei clic: primo clic decrescente (chi sale di piu' in cima), secondo
 * crescente, terzo toglie l'ordinamento tornando a quello per indicazione.
 */
export function prossimoOrdinePercentuale(
  corrente: OrdinePercentuale | null,
  key: CampoPercentuale,
): OrdinePercentuale | null {
  if (!corrente || corrente.key !== key) return { key, dir: "desc" };
  if (corrente.dir === "desc") return { key, dir: "asc" };
  return null;
}

/**
 * Ordina per variazione percentuale. Le righe senza il dato finiscono in fondo:
 * non sono "zero per cento", sono un'informazione che manca.
 */
export function ordinaPerPercentuale(rows: WatchlistRow[], ordine: OrdinePercentuale): WatchlistRow[] {
  const segno = ordine.dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const va = toNum(a[ordine.key]);
    const vb = toNum(b[ordine.key]);
    if (va === null && vb === null) return 0;
    if (va === null) return 1;
    if (vb === null) return -1;
    return segno * (va - vb);
  });
}

/** Comando per scegliere il periodo e il verso dell'ordinamento percentuale. */
export function PercentualeSort({
  ordine,
  onChange,
}: {
  ordine: OrdinePercentuale | null;
  onChange: (prossimo: OrdinePercentuale | null) => void;
}) {
  return (
    <div className="percent-sort" aria-label="Ordina per variazione percentuale">
      <span className="percent-sort-label">Variazione %</span>
      {PERIODI_PERCENTUALE.map((p) => {
        const attivo = ordine?.key === p.key;
        return (
          <button
            key={p.key}
            type="button"
            className={`percent-chip${attivo ? " selected" : ""}`}
            aria-pressed={attivo}
            title={`Ordina per la variazione a ${p.label}`}
            onClick={() => onChange(prossimoOrdinePercentuale(ordine, p.key))}
          >
            {p.label}
            {attivo ? (ordine.dir === "desc" ? " ▼" : " ▲") : ""}
          </button>
        );
      })}
      {ordine ? (
        <button type="button" className="percent-reset" onClick={() => onChange(null)}>
          Reset
        </button>
      ) : null}
    </div>
  );
}
