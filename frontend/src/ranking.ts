import type { WatchlistRow } from "./types";

/**
 * Ordinamento per indicazione, fase e rischio.
 *
 * Un clic su una tessera NON filtra: porta quel valore in testa. Per le
 * indicazioni i quattro valori seguono un anello fisso
 * ENTRA -> OSSERVA -> ATTENDI -> EVITA, quindi:
 *   clic ENTRA   -> ENTRA, OSSERVA, ATTENDI, EVITA
 *   clic OSSERVA -> OSSERVA, ATTENDI, EVITA, ENTRA
 *   clic ATTENDI -> ATTENDI, EVITA, ENTRA, OSSERVA
 *   clic EVITA   -> EVITA, ENTRA, OSSERVA, ATTENDI
 * cosi' c'e' una regola sola invece di due diverse a seconda della tessera.
 *
 * Fase e rischio fanno da discriminante a parita' di indicazione: prima i titoli
 * con il valore scelto, poi gli altri. Si fermano li' perche' alternare due
 * classifiche complete darebbe un ordine difficile da seguire a occhio.
 */

export const ANELLO_INDICAZIONE = ["ENTRA", "OSSERVA", "ATTENDI", "EVITA"] as const;

/** Ruota l'anello in modo che il valore scelto venga per primo. */
export function ruotaIndicazione(inTesta: string): string[] {
  const anello: readonly string[] = ANELLO_INDICAZIONE;
  const i = anello.indexOf(String(inTesta ?? "").toUpperCase());
  if (i < 0) return [...anello];
  return [...anello.slice(i), ...anello.slice(0, i)];
}

export interface Rango {
  /** Valore di indicazione da mettere in testa. */
  indicazione?: string | null;
  /** Valore di fase da preferire a parita' di indicazione. */
  fase?: string | null;
  /** Valore di rischio da preferire a parita' di indicazione e fase. */
  rischio?: string | null;
}

function posizione(valore: unknown, classifica: string[]): number {
  const i = classifica.indexOf(String(valore ?? "").toUpperCase());
  return i < 0 ? classifica.length : i;
}

/**
 * Testa usata per l'ordinamento di indicazione.
 *
 * Se l'utente ha scelto un valore, si usa quello **solo se il mercato ha titoli
 * con quel valore**: altrimenti si ripiega come per il predefinito. Serve a non
 * creare una contraddizione: cliccando "EVITA" quando non ci sono titoli EVITA,
 * la freccia direbbe "EVITA" ma a comandare resterebbe un altro gruppo.
 *
 * Senza scelta si parte da ENTRA e si scende: OSSERVA, ATTENDI, EVITA.
 */
export function testaIndicazione(rows: WatchlistRow[], preferita?: string | null): string {
  const richiesta = String(preferita ?? "").toUpperCase();
  const presenti = new Set(rows.map((r) => String(r.Entry_Signal ?? "").toUpperCase()));
  const desiderata = ["ENTRA", "OSSERVA", "ATTENDI", "EVITA"];

  if (richiesta && presenti.has(richiesta)) return richiesta;
  const primo = desiderata.find((v) => presenti.has(v));
  if (primo) return primo;
  return richiesta || "ENTRA";
}

/** 0 se il valore corrisponde a quello scelto, 1 altrimenti. */
function preferenza(valore: unknown, scelto: string | null | undefined): number {
  if (!scelto) return 0;
  return String(valore ?? "").toUpperCase() === String(scelto).toUpperCase() ? 0 : 1;
}

export function ordinaPerRango(rows: WatchlistRow[], rango: Rango): WatchlistRow[] {
  // Testa effettiva: quella scelta, oppure il primo valore presente partendo da
  // ENTRA. Cosi' il gruppo in cima non e' mai vuoto.
  const indicazioni = ruotaIndicazione(testaIndicazione(rows, rango.indicazione));

  return [...rows].sort((a, b) => {
    const diffInd = posizione(a.Entry_Signal, indicazioni) - posizione(b.Entry_Signal, indicazioni);
    if (diffInd !== 0) return diffInd;

    const diffFase = preferenza(a.Market_Phase, rango.fase) - preferenza(b.Market_Phase, rango.fase);
    if (diffFase !== 0) return diffFase;

    return preferenza(a.Rischio_Trend, rango.rischio) - preferenza(b.Rischio_Trend, rango.rischio);
  });
}
