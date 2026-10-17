/** Tipi del portafoglio virtuale (fase 1). */

export type PortafoglioElenco = {
  id: string;
  nome: string;
  stato: string;
  valuta_base: string;
  capitale_iniziale: number;
  liquidita: number;
  /** Valore attuale: liquidita' piu' posizioni ai prezzi correnti. */
  valore_totale: number;
  valore_posizioni: number;
  pnl_eur: number;
  pnl_pct: number;
  esposizione_pct: number;
  num_posizioni: number;
  num_operazioni: number;
  creato?: string | null;
};

export type PosizionePortafoglio = {
  id: string;
  ticker: string;
  nome?: string;
  valuta: string;
  /** Azione, ETF, ETC, Cripto. */
  strumento: string;
  mercato: string;
  quantita: number;
  prezzo_ingresso: number;
  prezzo_corrente: number;
  valore_eur: number;
  /** Solo movimento di prezzo, senza commissioni. */
  pnl_eur: number;
  pnl_pct: number;
  /** Se vendessi adesso: dopo commissioni di acquisto e vendita, Tobin e slippage. */
  pnl_netto_eur: number;
  pnl_netto_pct: number;
  costi_ingresso_eur: number;
  costo_vendita_eur: number;
  importo_investito_eur?: number;
  stop_iniziale: number;
  stop_attuale: number;
  obiettivo: number;
  distanza_stop_pct: number | null;
  rischio_iniziale_eur: number;
  giorni_detenuti?: number;
  data_ingresso?: string;
  prezzo_valido: boolean;
  prezzo_fonte?: string;
  /** Istante della quotazione usata (ISO). */
  prezzo_quando?: string | null;
  prezzo_fresco?: boolean;
};


export type StatistichePortafoglio = {
  vinte: number;
  perse: number;
  win_rate: number | null;
  profit_factor: number | null;
  pnl_medio_eur: number | null;
};

export type CostiPortafoglio = {
  commissione_pct: number;
  commissione_min_eur: number;
  tobin_pct: number;
  cambio_pct: number;
  slippage_pct: number;
};

export type ParametriPortafoglio = {
  rischio_per_operazione_pct: number;
  max_per_titolo_pct: number;
  max_posizioni: number;
  esposizione_max_pct: number;
  riserva_liquidita_pct: number;
  stop_atr_mult: number;
  stop_min_pct: number;
  stop_max_pct: number;
  trailing_atr_mult: number;
  obiettivo_pct: number;
  rischio_ammesso: string[];
  /** Quanto sopra la EMA50 un titolo puo' essere per essere comprato. */
  distanza_max_media_pct: number;
  /** Mercati su cui il portafoglio puo' operare. */
  mercati: string[];
  tech_score_min: number;
  ingressi_da: string[];
  scadenza_segnale_sedute: number;
  uscita_tempo_sedute: number;
  max_nuove_posizioni_giorno: number;
  rotazione: boolean;
  liquidita_minima_ordine_eur: number;
};

export type Portafoglio = {
  id: string;
  nome: string;
  stato: string;
  valuta_base: string;
  capitale_iniziale: number;
  liquidita: number;
  valore_posizioni: number;
  valore_totale: number;
  investito: number;
  esposizione_pct: number;
  pnl_totale_eur: number;
  pnl_totale_pct: number;
  num_posizioni: number;
  num_operazioni: number;
  statistiche: StatistichePortafoglio;
  parametri: ParametriPortafoglio;
  posizioni: PosizionePortafoglio[];
  /** La piu' recente delle quotazioni usate. */
  quotazioni_aggiornate?: string | null;
  prezzi_freschi?: boolean;
  costi: CostiPortafoglio;
  creato?: string | null;
  note?: string;
};

export type AnteprimaAcquisto = {
  ticker: string;
  nome: string;
  valuta: string;
  prezzo: number;
  prezzo_eseguito: number;
  cambio: number;
  quantita: number;
  importo_eur: number;
  commissione_eur: number;
  imposta_tobin_eur: number;
  costo_cambio_eur: number;
  totale_eur: number;
  stop: number;
  obiettivo: number;
  perdita_massima_eur: number;
  limite?: string;
  limiti?: { rischio: number; tetto_titolo: number; cassa: number };
  liquidita_eur: number;
  prezzo_fonte?: string;
  atr: number | null;
  indicazione?: string | null;
  tech_score?: number | null;
  rischio_trend?: string | null;
  ordine_troppo_piccolo: boolean;
};

export type OperazioneChiusa = {
  posizione?: string;
  ticker: string;
  nome?: string;
  quantita: number;
  data_ingresso?: string;
  prezzo_ingresso?: number;
  data_uscita?: string;
  prezzo_uscita?: number;
  motivo_uscita: string;
  commissioni_totali_eur?: number;
  pnl_lordo_eur?: number;
  pnl_netto_eur?: number;
  pnl_pct?: number;
  r_multiplo?: number | null;
  giorni_detenuti?: number;
};
