import type { WatchlistRow } from "./types";

/**
 * Ordinamento per indicazione, fase e rischio.
 *
 * Un clic su una tessera NON filtra: mette quel valore in testa all'ordine. La
 * dimensione cliccata diventa la PRIMA da guardare, e le altre due seguono:
 *
 *   clic su Indicazione -> prima l'indicazione, poi fase, poi rischio
 *   clic su Fase        -> prima la fase, poi indicazione, poi rischio
 *   clic su Rischio     -> prima il rischio, poi indicazione, poi fase
 *
 * Prima l'indicazione veniva sempre per prima, quindi cliccare Fase o Rischio
 * non cambiava nulla a schermo: il difetto era questo.
 */

export const ANELLO_INDICAZIONE = ["ENTRA", "OSSERVA", "ATTENDI", "EVITA"] as const;
export const ANELLO_FASE = ["TENDENZA", "RIPRESA", "LATERALE", "RIBASSO"] as const;
export const ANELLO_RISCHIO = ["NORMALE", "TESO", "ESTREMO"] as const;

export type Dimensione = "indicazione" | "fase" | "rischio";

/** Ruota un anello in modo che il valore scelto venga per primo. */
export function ruota(anello: readonly string[], inTesta: string): string[] {
  const i = anello.indexOf(String(inTesta ?? "").toUpperCase());
  if (i < 0) return [...anello];
  return [...anello.slice(i), ...anello.slice(0, i)];
}

/** Come prima si chiamava, per compatibilita'. */
export function ruotaIndicazione(inTesta: string): string[] {
  return ruota(ANELLO_INDICAZIONE, inTesta);
}

export interface Rango {
  /** Valore di indicazione da mettere in testa. */
  indicazione?: string | null;
  /** Valore di fase da mettere in testa. */
  fase?: string | null;
  /** Valore di rischio da mettere in testa. */
  rischio?: string | null;
}

function posizione(valore: unknown, classifica: string[]): number {
  const i = classifica.indexOf(String(valore ?? "").toUpperCase());
  return i < 0 ? classifica.length : i;
}

/**
 * Testa effettiva di una dimensione.
 *
 * Se l'utente ha scelto un valore, si usa quello **solo se il mercato ha titoli
 * con quel valore**: altrimenti si ripiega sul primo presente. Serve a non
 * contraddirsi: cliccando "EVITA" senza titoli EVITA, la freccia direbbe "EVITA"
 * mentre a comandare resterebbe un altro gruppo.
 */
export function testa(
  rows: WatchlistRow[],
  campo: string,
  anello: readonly string[],
  preferita?: string | null,
): string {
  const richiesta = String(preferita ?? "").toUpperCase();
  const presenti = new Set(rows.map((r) => String(r[campo] ?? "").toUpperCase()));
  if (richiesta && presenti.has(richiesta)) return richiesta;
  const primo = anello.find((v) => presenti.has(v));
  if (primo) return primo;
  return richiesta || anello[0];
}

/** Testa dell'indicazione: ENTRA, e se manca OSSERVA, ATTENDI, EVITA. */
export function testaIndicazione(rows: WatchlistRow[], preferita?: string | null): string {
  return testa(rows, "Entry_Signal", ANELLO_INDICAZIONE, preferita);
}

/**
 * Ordine secondo il rango. `dimensione` dice quale guardare per prima: e' la
 * tessera su cui si e' cliccato per ultimo.
 */
export function ordinaPerRango(
  rows: WatchlistRow[],
  rango: Rango,
  dimensione: Dimensione = "indicazione",
): WatchlistRow[] {
  const ind = ruota(ANELLO_INDICAZIONE, testa(rows, "Entry_Signal", ANELLO_INDICAZIONE, rango.indicazione));
  const fas = ruota(ANELLO_FASE, testa(rows, "Market_Phase", ANELLO_FASE, rango.fase));
  const ris = ruota(ANELLO_RISCHIO, testa(rows, "Rischio_Trend", ANELLO_RISCHIO, rango.rischio));

  const confronto = (a: WatchlistRow, b: WatchlistRow, d: Dimensione): number => {
    if (d === "indicazione") return posizione(a.Entry_Signal, ind) - posizione(b.Entry_Signal, ind);
    if (d === "fase") return posizione(a.Market_Phase, fas) - posizione(b.Market_Phase, fas);
    return posizione(a.Rischio_Trend, ris) - posizione(b.Rischio_Trend, ris);
  };

  // La dimensione cliccata per prima, poi le altre due in ordine fisso.
  const ordine: Dimensione[] = dimensione === "fase"
    ? ["fase", "indicazione", "rischio"]
    : dimensione === "rischio"
      ? ["rischio", "indicazione", "fase"]
      : ["indicazione", "fase", "rischio"];

  return [...rows].sort((a, b) => {
    for (const d of ordine) {
      const diff = confronto(a, b, d);
      if (diff !== 0) return diff;
    }
    return 0;
  });
}
