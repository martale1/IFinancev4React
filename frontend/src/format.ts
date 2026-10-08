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
