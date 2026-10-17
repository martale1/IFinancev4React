/**
 * Calcolo dei quattro blocchi della pagina Highlights.
 *
 * PERCHE' NON SONO CONTEGGI. La versione precedente mostrava le distribuzioni
 * (`19 ATTENDI`, `17 RIBASSO`): numeri veri ma che non dicono cosa guardare. Su
 * 1684 ETF, `63 ENTRA` non aiuta a scegliere, e i 305 titoli con TECH_SCORE >= 80
 * che NON sono ENTRA non comparivano da nessuna parte.
 *
 * Qui i titoli si scelgono per quanto sono VICINI ALL'AZIONE, e ogni riga porta
 * con se' il motivo:
 *
 *   1. Pronti adesso        -> tutti e tre i requisiti soddisfatti (ENTRA)
 *   2. A un passo           -> OSSERVA a cui manca UNA sola condizione
 *   3. Forti ma frenati     -> TECH_SCORE alto e non ENTRA, raggruppati per freno
 *   4. Nuovi oggi           -> cosa e' cambiato: richiede lo stato di ieri
 *
 * Le soglie sono quelle di `four_axes.py`: rischio NORMALE sotto 3% di ATR e 5%
 * di distanza dalla EMA50, forza FORTE_SU da ADX 22, momento non CALANTE.
 */
import { toNum } from "./format";
import type { WatchlistRow } from "./types";

/** Quante righe mostrare per blocco: oltre, non sono piu' "evidenze". */
export const MAX_PER_BLOCCO = 5;

/** Un titolo nei blocchi, con il motivo scritto in una frase. */
export type VoceHighlight = {
  row: WatchlistRow;
  ticker: string;
  nome: string;
  /** Perche' e' qui, in una frase leggibile. */
  motivo: string;
  /** Valore per ordinare dentro il blocco (piu' alto = piu' interessante). */
  peso: number;
};

const su = (v: unknown) => String(v ?? "").trim().toUpperCase();

/** I tre requisiti di ENTRA, uno per uno, con il valore che manca. */
export function requisiti(row: WatchlistRow): { fase: boolean; momento: boolean; rischio: boolean } {
  return {
    fase: su(row.Market_Phase) === "TENDENZA",
    momento: su(row.Momento_Trend) !== "CALANTE",
    rischio: su(row.Rischio_Trend) === "NORMALE",
  };
}

/** Quante delle tre condizioni mancano (0 = pronto, 1 = a un passo). */
export function mancanti(row: WatchlistRow): number {
  const r = requisiti(row);
  return [r.fase, r.momento, r.rischio].filter((x) => !x).length;
}

/** Il testo del freno, con il numero che servirebbe per rientrare. */
export function testoFreno(row: WatchlistRow): string {
  const fase = su(row.Market_Phase);
  const rischio = su(row.Rischio_Trend);
  const forza = su(row.Forza_Trend);
  const momento = su(row.Momento_Trend);
  const close = toNum(row.Close);
  const ema = toNum(row.EMA_50);
  const atr = toNum(row.ATR_PCT);
  const adx = toNum(row.ADX);

  // La fase viene per prima: se il titolo non e' in TENDENZA nessun altro
  // requisito basta. Misurato: ETF con TECH 93, rischio NORMALE e forza
  // FORTE_SU restano ATTENDI perche' la fase e' LATERALE, e senza questo
  // controllo il motivo restava vuoto.
  if (fase !== "TENDENZA") {
    if (fase === "RIPRESA") return "fase RIPRESA: serve TENDENZA (forza ancora debole)";
    return `fase ${fase}: serve TENDENZA`;
  }

  if (rischio !== "NORMALE") {
    const dist = close !== null && ema !== null && ema !== 0 ? Math.abs(close / ema - 1) * 100 : null;
    const prezzoOk = ema !== null ? ema * 1.05 : null;
    const perAtr = atr !== null && atr >= 3;
    const perDist = dist !== null && dist >= 5;
    if (perDist && !perAtr && dist !== null && prezzoOk !== null) {
      return `rischio ${rischio}: distanza dalla media ${dist.toFixed(2)}% (soglia 5%), serve sotto ${prezzoOk.toFixed(3)}`;
    }
    if (perAtr && !perDist && atr !== null) {
      return `rischio ${rischio}: volatilità (ATR) ${atr.toFixed(2)}% (soglia 3%)`;
    }
    if (perAtr && perDist && atr !== null && dist !== null && prezzoOk !== null) {
      return `rischio ${rischio}: ATR ${atr.toFixed(2)}% e distanza ${dist.toFixed(2)}%, serve sotto ${prezzoOk.toFixed(3)}`;
    }
    return `rischio ${rischio}`;
  }

  if (forza !== "FORTE_SU") {
    return adx !== null
      ? `forza ${forza}: ADX ${adx.toFixed(1)} contro la soglia 22`
      : `forza ${forza}: serve FORTE_SU`;
  }

  if (momento === "CALANTE") return "momento CALANTE";
  return "";
}

/**
 * 1. Pronti adesso: indicazione ENTRA. Hanno tutti e tre i requisiti.
 * Si ordinano per TECH_SCORE, poi per ADX: fra i pronti, i piu' solidi prima.
 */
export function prontiAdesso(righe: WatchlistRow[]): VoceHighlight[] {
  return righe
    .filter((r) => su(r.Entry_Signal) === "ENTRA")
    .map((r) => ({
      row: r,
      ticker: String(r.Ticker ?? ""),
      nome: String(r.Name ?? ""),
      motivo: `direzione SU, forza FORTE_SU, momento ${su(r.Momento_Trend).toLowerCase()}, rischio NORMALE`,
      peso: toNum(r.TECH_SCORE) ?? 0,
    }))
    .sort((a, b) => b.peso - a.peso || (toNum(b.row.ADX) ?? 0) - (toNum(a.row.ADX) ?? 0));
}

/**
 * 2. A un passo: OSSERVA con UNA sola condizione mancante.
 * E' il blocco piu' utile: sono i candidati di domani, e il motivo dice quale
 * livello serve per rientrare.
 */
export function aUnPasso(righe: WatchlistRow[]): VoceHighlight[] {
  return righe
    .filter((r) => su(r.Entry_Signal) === "OSSERVA" && mancanti(r) === 1)
    .map((r) => ({
      row: r,
      ticker: String(r.Ticker ?? ""),
      nome: String(r.Name ?? ""),
      motivo: testoFreno(r),
      // Chi ha il TECH_SCORE piu' alto e' il candidato piu' forte.
      peso: toNum(r.TECH_SCORE) ?? 0,
    }))
    .sort((a, b) => b.peso - a.peso);
}

/**
 * 3. Forti ma frenati: TECH_SCORE alto e indicazione diversa da ENTRA.
 * Raggruppati per freno, perche' il freno dice cosa aspettare.
 *
 * `escludi` contiene i ticker gia' mostrati in "Pronti adesso" e "A un passo":
 * misurato sui dati veri, CPR.MI ha TECH 90 ed e' anche "a un passo", quindi
 * senza questo comparirebbe in due blocchi. Ogni titolo sta in un blocco solo.
 */
export function fortiMaFrenati(
  righe: WatchlistRow[],
  escludi: ReadonlySet<string> = new Set(),
  /**
   * Soglia di TECH_SCORE. Misurata sui dati veri: con 80 il blocco restava
   * VUOTO sul MIB30 (dove i titoli forti o sono gia' a un passo, o stanno sotto
   * 80) e mostrava solo 2 titoli sugli ETF. Con 75 si popola su entrambi.
   */
  sogliaScore = 75,
): Array<{ freno: string; voci: VoceHighlight[] }> {
  const perFreno = new Map<string, VoceHighlight[]>();

  for (const r of righe) {
    const ticker = String(r.Ticker ?? "");
    if (escludi.has(ticker)) continue;
    const score = toNum(r.TECH_SCORE);
    if (score === null || score < sogliaScore) continue;
    // EVITA e' fuori perimetro: non e' "frenato", e' escluso.
    const ind = su(r.Entry_Signal);
    if (ind === "ENTRA" || ind === "EVITA") continue;

    const freno = testoFreno(r) || `indicazione ${ind.toLowerCase()}`;
    // Il gruppo e' la CAUSA, non la frase intera: cosi' titoli con lo stesso
    // freno finiscono insieme anche se i numeri cambiano.
    const causa = freno.startsWith("fase")
      ? "fase non ancora di tendenza"
      : freno.startsWith("rischio")
        ? "rischio da rientrare"
        : freno.startsWith("forza")
          ? "forza non ancora confermata"
          : freno.startsWith("momento")
            ? "momento in calo"
            : freno;
    const lista = perFreno.get(causa) ?? [];
    lista.push({ row: r, ticker, nome: String(r.Name ?? ""), motivo: freno, peso: score });
    perFreno.set(causa, lista);
  }

  return [...perFreno.entries()]
    .map(([freno, voci]) => ({
      freno,
      voci: voci.sort((a, b) => b.peso - a.peso),
    }))
    // I gruppi piu' numerosi prima: sono i freni piu' diffusi sul mercato.
    .sort((a, b) => b.voci.length - a.voci.length);
}
