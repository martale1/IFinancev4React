/**
 * Formattazione condivisa: prima `num` e `pct` erano copiati in cinque
 * componenti (scheda, tabella, monitor, modale del grafico), con firme diverse
 * e quindi risultati diversi a schermo. Qui c'e' una versione sola.
 */

/** Numero leggibile, o "-" se il valore manca. */
export function num(value: unknown, digits = 2): string {
  const parsed = typeof value === "number" ? value : Number(value);
  if (value === null || value === undefined || value === "" || !Number.isFinite(parsed)) return "-";
  return parsed.toLocaleString("it-IT", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** Variazione percentuale con segno, o "-" se manca. */
export function pct(value: unknown): string {
  const parsed = typeof value === "number" ? value : Number(value);
  if (value === null || value === undefined || value === "" || !Number.isFinite(parsed)) return "-";
  const segno = parsed > 0 ? "+" : "";
  return `${segno}${parsed.toFixed(2)}%`;
}

/** Numero, o null se il valore non e' utilizzabile (per i confronti). */
export function toNum(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/** Classe di colore per una variazione: verde sopra zero, rosso sotto. */
export function pctClass(value: unknown): string {
  const parsed = toNum(value);
  return parsed === null || parsed === 0 ? "neutral" : parsed > 0 ? "positive" : "negative";
}

/**
 * Perche' un titolo non e' ENTRA: la condizione che manca, detta in modo
 * comprensibile, con il numero che serve per rientrare.
 *
 * Serve perche' sulla card si legge `OSSERVA` e `Rischio TESO` ma non il
 * collegamento fra i due: senza sapere QUALE soglia e' stata superata e di
 * quanto, l'indicazione sembra arbitraria. Nel caso piu' frequente la
 * spiegazione e' la distanza dalla media, non la volatilita'.
 *
 * Le soglie qui dentro sono quelle di `four_axes.py`: rischio NORMALE sotto
 * 3% di ATR e 5% di distanza dalla EMA50, forza FORTE_SU da ADX 22.
 */
export function percheNonEntra(row: Record<string, unknown>): string | null {
  const indicazione = String(row.Entry_Signal ?? "").trim().toUpperCase();
  if (indicazione !== "OSSERVA") return null;

  const fase = String(row.Market_Phase ?? "").trim().toUpperCase();
  const momento = String(row.Momento_Trend ?? "").trim().toUpperCase();
  const rischio = String(row.Rischio_Trend ?? "").trim().toUpperCase();
  const forza = String(row.Forza_Trend ?? "").trim().toUpperCase();
  const haDati = (v: number | null): v is number => v !== null;

  const close = toNum(row.Close);
  const ema = toNum(row.EMA_50);
  const atr = toNum(row.ATR_PCT);
  const adx = toNum(row.ADX);

  // Condizione 1: il rischio deve tornare NORMALE. E' il blocco piu' frequente.
  if (rischio !== "NORMALE") {
    const distanza = haDati(close) && haDati(ema) && ema !== 0 ? Math.abs(close / ema - 1) * 100 : null;
    const perAtr = haDati(atr) && atr >= 3;
    const perDistanza = haDati(distanza) && distanza >= 5;
    // Il target e' il prezzo che riporta la distanza sotto il 5%.
    const prezzoOk = haDati(ema) ? ema * 1.05 : null;

    if (perDistanza && !perAtr && haDati(distanza) && haDati(prezzoOk)) {
      return `manca solo il rischio: ${rischio}, distanza dalla media ${distanza.toFixed(2)}% (soglia 5%), serve sotto ${prezzoOk.toFixed(3)}`;
    }
    if (perAtr && !perDistanza && haDati(atr)) {
      return `manca solo il rischio: ${rischio}, volatilità (ATR) ${atr.toFixed(2)}% (soglia 3%)`;
    }
    if (perAtr && perDistanza && haDati(atr) && haDati(distanza) && haDati(prezzoOk)) {
      return `manca solo il rischio: ${rischio}, ATR ${atr.toFixed(2)}% (soglia 3%) e distanza ${distanza.toFixed(2)}% (soglia 5%), serve sotto ${prezzoOk.toFixed(3)}`;
    }
    return `manca solo il rischio: ora è ${rischio}, deve tornare NORMALE`;
  }

  // Condizione 2: la forza deve arrivare a FORTE_SU (ADX almeno 22).
  if (forza !== "FORTE_SU" && (fase === "TENDENZA" || fase === "RIPRESA")) {
    if (haDati(adx)) {
      return `manca la forza: serve FORTE_SU, ADX ${adx.toFixed(1)} contro la soglia 22`;
    }
    return "manca la forza: serve FORTE_SU";
  }

  // Condizione 3: il momento non deve calare.
  if (momento === "CALANTE") {
    return "manca il momento: è CALANTE, deve risalire";
  }

  return null;
}
