import type { WatchlistRow } from "../types";
import { toNum } from "../format";

/**
 * Barra di ordinamento condivisa fra la tab All e il Monitor.
 *
 * Prima esisteva solo nel tab All, con i pulsanti scritti a mano li' dentro: il
 * Monitor non aveva alcun ordinamento. Qui la logica sta in un posto solo, cosi'
 * le due viste ordinano allo stesso modo e i campi si possono cambiare una volta
 * sola.
 */

export type SortKey = string;

export interface CampoOrdinamento {
  label: string;
  key: SortKey;
}

/** Campi proposti, gli stessi in entrambe le viste. */
export const CAMPI_ORDINAMENTO: CampoOrdinamento[] = [
  { label: "Ticker", key: "Ticker" },
  { label: "Prezzo", key: "Close" },
  { label: "Var. Giorn. (1D)", key: "PCTV_1D" },
  { label: "Var. 5D", key: "PCTV_5D" },
  { label: "Var. 30D", key: "PCTV_30D" },
  { label: "TECH SCORE", key: "TECH_SCORE" },
  { label: "Indicazione", key: "Entry_Signal" },
  { label: "Fase", key: "Market_Phase" },
  { label: "S3", key: "MACD_vs_Signal" },
  { label: "SARMA", key: "SIG_MA_SAR" },
  { label: "RSI", key: "RSI" },
  { label: "ADX", key: "ADX" },
  { label: "ADX + (DI+>DI−)", key: "ADX_DI_PLUS" },
  { label: "ADX − (DI+<DI−)", key: "ADX_DI_MINUS" },
  { label: "willR", key: "Williams_R" },
];

/** Ordine di merito delle indicazioni: prima cio' su cui c'e' da agire. */
const PRIORITA_INDICAZIONE: Record<string, number> = { ENTRA: 0, OSSERVA: 1, ATTENDI: 2, EVITA: 3 };
/** Ordine di forza delle fasi. */
const PRIORITA_FASE: Record<string, number> = { TENDENZA: 0, RIPRESA: 1, LATERALE: 2, RIBASSO: 3 };

/** Verso naturale del campo: le percentuali e i punteggi si leggono dal migliore. */
export function versoNaturale(key: SortKey): "asc" | "desc" {
  return ["Ticker", "MACD_vs_Signal", "SIG_MA_SAR", "Entry_Signal", "Market_Phase"].includes(key) ? "asc" : "desc";
}

/**
 * Regola dei clic, una sola per entrambe le viste.
 *
 * Primo clic su un campo: verso naturale (per i punteggi il migliore in cima).
 * Secondo clic: verso invertito. Terzo clic: ordinamento tolto.
 * Il verso naturale del campo vince sempre su quello dell'altro tab, altrimenti
 * la stessa barra si comporterebbe in due modi diversi.
 */
export function prossimoOrdinamento(
  corrente: { key: SortKey | null; dir: "asc" | "desc" | null },
  key: SortKey | null,
): { key: SortKey | null; dir: "asc" | "desc" | null } {
  if (key === null) return { key: null, dir: null };
  if (corrente.key !== key) return { key, dir: versoNaturale(key) };
  const naturale = versoNaturale(key);
  if (corrente.dir === naturale) return { key, dir: naturale === "asc" ? "desc" : "asc" };
  return { key: null, dir: null };
}

/** Ordina le righe secondo campo e verso. Restituisce una copia. */
export function ordinaRighe(
  rows: WatchlistRow[],
  key: SortKey | null,
  dir: "asc" | "desc" | null,
): WatchlistRow[] {
  const copia = [...rows];
  if (!key || !dir) return copia;
  const segno = dir === "asc" ? 1 : -1;

  return copia.sort((a, b) => {
    if (key === "ADX_DI_PLUS" || key === "ADX_DI_MINUS") {
      const direzionale = (row: WatchlistRow) => {
        const plus = toNum(row.PLUS_DI);
        const minus = toNum(row.MINUS_DI);
        if (plus === null || minus === null) return false;
        return key === "ADX_DI_PLUS" ? plus > minus : plus < minus;
      };
      const aOk = direzionale(a);
      const bOk = direzionale(b);
      if (aOk !== bOk) return aOk ? -segno : segno;
      return segno * ((toNum(a.ADX) ?? 0) - (toNum(b.ADX) ?? 0));
    }

    if (key === "Entry_Signal") {
      const pa = PRIORITA_INDICAZIONE[String(a.Entry_Signal ?? "ATTENDI").toUpperCase()] ?? 9;
      const pb = PRIORITA_INDICAZIONE[String(b.Entry_Signal ?? "ATTENDI").toUpperCase()] ?? 9;
      return segno * (pa - pb);
    }

    if (key === "Market_Phase") {
      const pa = PRIORITA_FASE[String(a.Market_Phase ?? "").toUpperCase()] ?? 9;
      const pb = PRIORITA_FASE[String(b.Market_Phase ?? "").toUpperCase()] ?? 9;
      return segno * (pa - pb);
    }

    if (key === "Ticker") {
      return segno * String(a.Ticker ?? "").localeCompare(String(b.Ticker ?? ""));
    }

    const na = toNum(a[key]);
    const nb = toNum(b[key]);
    // I valori mancanti finiscono in fondo, in entrambi i versi: non sono "zero".
    if (na === null && nb === null) return 0;
    if (na === null) return 1;
    if (nb === null) return -1;
    return segno * (na - nb);
  });
}

export function SortBar({
  sortKey,
  sortDir,
  onChange,
  fields = CAMPI_ORDINAMENTO,
}: {
  sortKey: SortKey | null;
  sortDir: "asc" | "desc" | null;
  /** Il componente decide il verso: chi chiama riceve la scelta gia' risolta. */
  onChange: (key: SortKey | null, dir: "asc" | "desc" | null) => void;
  fields?: CampoOrdinamento[];
}) {
  return (
    <div className="sort-bar" role="group" aria-label="Ordina i titoli">
      <span className="sort-bar-label">⇅ Ordina per:</span>
      {fields.map((opt) => {
        const attivo = sortKey === opt.key;
        return (
          <button
            key={opt.key}
            type="button"
            className={`sort-pill ${attivo ? "active" : ""}`}
            aria-pressed={attivo}
            onClick={() => {
              const prossimo = prossimoOrdinamento({ key: sortKey, dir: sortDir }, opt.key);
              onChange(prossimo.key, prossimo.dir);
            }}
          >
            {opt.label}
            {attivo ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
          </button>
        );
      })}
      {sortKey ? (
        <button type="button" className="sort-reset" onClick={() => onChange(null, null)}>
          Reset
        </button>
      ) : null}
    </div>
  );
}
