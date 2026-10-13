/**
 * Livelli di uscita per una posizione aperta, su richiesta.
 *
 * PERCHE' SERVE: il sistema calcola gli stop solo quando suggerisce un'operazione
 * (`four_axes._levels_from_axes`): `Trend_Stop_Level` (EMA50) esiste solo se
 * l'azione e' BUY o ADD, `Profit_Protect_Level` solo se e' REDUCE. Quando l'azione
 * diventa HOLD — cioe' proprio quando hai una posizione aperta e il titolo si e'
 * allontanato — **i livelli spariscono**. Misurato su Campari: azione HOLD, quindi
 * `Trend_Stop_Level` e `Profit_Protect_Level` entrambi vuoti.
 *
 * Qui i livelli si CALCOLANO dai numeri che la riga ha gia' (Close, ATR, EMA30,
 * EMA50, SAR, CE_Long), senza toccare il backend e senza salvare nulla. Sono gli
 * stessi ancoraggi che il backend usa, piu' due varianti di volatilita'.
 *
 * ATTENZIONE AL LIMITE: sono livelli misurati dal prezzo di OGGI. Non conosco il
 * prezzo di carico, quindi dicono "quanto e' lontano lo stop dal prezzo attuale",
 * non "se esci guadagni o perdi". Con un titolo molto esteso, come Campari a +6,9%
 * dalla media, uno stop calcolato da qui puo' stare SOPRA il prezzo di carico: in
 * quel caso protegge il profitto, non il capitale.
 */
import { toNum } from "./format";

export type LivelloUscita = {
  nome: string;
  tipo: string;
  livello: number;
  distanzaPct: number;
};

/**
 * I livelli calcolabili per questa riga, dal piu' vicino al prezzo al piu' lontano.
 * Restituisce un elenco vuoto se mancano i numeri necessari.
 */
export function livelliUscita(row: Record<string, unknown>): LivelloUscita[] {
  const close = toNum(row.Close);
  if (close === null || close === 0) return [];

  const atr = toNum(row.ATR);
  const ema30 = toNum(row.EMA_30);
  const ema50 = toNum(row.EMA_50);
  const sar = toNum(row.SAR);
  const ce = toNum(row.CE_Long);

  const grezzi: Array<{ nome: string; tipo: string; livello: number | null }> = [
    // Il chandelier exit e' quello che il backend espone come SL2_RiskPct.
    { nome: "Chandelier exit", tipo: "trailing · già nel sistema", livello: ce },
    { nome: "SAR", tipo: "trailing di Williams", livello: sar },
    // La formula del profit protect del backend: max(SAR, EMA30 − 0.25 ATR).
    {
      nome: "Protetto",
      tipo: "max(SAR, EMA30 − 0,25 ATR)",
      livello: sar !== null && ema30 !== null && atr !== null ? Math.max(sar, ema30 - 0.25 * atr) : null,
    },
    { nome: "Strutturale", tipo: "EMA50", livello: ema50 },
    { nome: "Volatilità", tipo: "2 × ATR sotto il prezzo", livello: atr !== null ? close - 2 * atr : null },
    { nome: "Volatilità", tipo: "1,5 × ATR sotto il prezzo", livello: atr !== null ? close - 1.5 * atr : null },
    { nome: "Volatilità", tipo: "3 × ATR sotto il prezzo", livello: atr !== null ? close - 3 * atr : null },
  ];

  return grezzi
    .filter((l): l is { nome: string; tipo: string; livello: number } => l.livello !== null)
    // Uno stop sopra il prezzo non e' uno stop: si scarta.
    .filter((l) => l.livello < close)
    .map((l) => ({ ...l, distanzaPct: (l.livello / close - 1) * 100 }))
    .sort((a, b) => b.livello - a.livello);
}

/** Livello piu' vicino al prezzo (protegge di piu', esce prima). */
export function piuVicino(livelli: LivelloUscita[]): LivelloUscita | null {
  return livelli.length ? livelli[0] : null;
}

/** Livello piu' lontano dal prezzo (lascia respirare, protegge meno). */
export function piuLontano(livelli: LivelloUscita[]): LivelloUscita | null {
  return livelli.length ? livelli[livelli.length - 1] : null;
}
