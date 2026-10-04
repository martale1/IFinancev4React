import { useMemo, useState } from "react";
import type { WatchlistRow } from "../types";

type ColumnKind = "text" | "number" | "percent" | "date" | "bool";

type ColumnMeta = {
  label?: string;
  kind?: ColumnKind;
  digits?: number;
  group?: string;
};

type Column = {
  key: string;
  label: string;
  kind: ColumnKind;
  digits?: number;
  group: string;
};

type Props = {
  rows: WatchlistRow[];
  market: string;
  loading?: boolean;
  error?: string;
  sourcePath?: string | null;
  sourceUpdatedAt?: string | null;
  onChart: (row: WatchlistRow) => void;
  onAi: (row: WatchlistRow) => void;
};

/**
 * Metadati di presentazione per le colonne note (etichetta italiana, formato e
 * gruppo). Non è più un elenco chiuso: qualunque colonna presente nell'Excel e
 * non elencata qui viene comunque mostrata in fondo, con etichetta e formato
 * dedotti dal nome e dai valori (vedi `buildColumns`).
 */
/**
 * Convenzioni comuni a tutti gli indicatori, come sono calcolati in
 * `main.py` / `TechnicalAnalyzer.py`.
 */
const GUIDE_CONVENTIONS: Array<{ title: string; text: string }> = [
  { title: "t e t-1", text: "t è la seduta esaminata, t-1 la precedente. Un incrocio è vero solo nel giorno in cui la relazione cambia stato: era falsa o uguale in t-1 e diventa vera in t." },
  { title: "Candela rialzista", text: "Significa soltanto Close(t) > Open(t), cioè chiusura sopra l'apertura della stessa seduta. Non implica che la chiusura sia sopra quella del giorno prima." },
  { title: "Arrotondamento", text: "Al termine del calcolo tutti i valori del dataframe vengono arrotondati a 3 decimali, quindi alcune colonne mostrano zeri di troppo (es. ADX_Change)." },
  { title: "Storico minimo", text: "Con meno di 40 righe il titolo viene marcato INSUFFICIENT_HISTORY e gli indicatori lunghi (SMA200, Alligator, PCTV_180D) restano vuoti." },
  { title: "Fonte", text: "Prezzi daily da Yahoo Finance via yfinance, senza cache locale: il download avviene a ogni esecuzione dell'analisi. Nessun dato viene aggiustato per dividendi (auto_adjust=False)." },
];

type GuideGroup = {
  id: string;
  title: string;
  formula: string;
  params: string;
  columns: string;
  read: string;
  note?: string;
};

/** Tutti i gruppi di colonne calcolati da main.py, con modalità di calcolo. */
const INDICATOR_GUIDE: GuideGroup[] = [
  {
    id: "prezzi",
    title: "OHLCV (input da Yahoo Finance)",
    formula: "Open / High / Low / Close / Adj Close / Volume così come restituiti da yfinance, periodo 1y, intervallo 1d.",
    params: "period=1y, auto_adjust=False",
    columns: "Date, Ticker, Name, Open, High, Low, Close, Adj Close, Volume",
    read: "Close è il prezzo di riferimento di ogni regola. Open serve alle candele (pattern S8/S9), High/Low agli ATR e ai canali, Volume alla liquidità e ai breakout.",
  },
  {
    id: "adx",
    title: "ADX e direzionali (forza e direzione del trend)",
    formula: "ta-lib ADX, PLUS_DI, MINUS_DI. ADX_Change = ADX.diff(). ADX_Trend = Bullish se DI+ >= DI- altrimenti Bearish. ADX_Cross = BullCross/BearCross quando le due linee si incrociano. ADX_Slope = Up/Down. I *_Days contano le sedute consecutive nello stato.",
    params: "periodo 14",
    columns: "ADX, ADX_Change, PLUS_DI, MINUS_DI, ADX_Strong, ADX_Trend, ADX_Cross, ADX_Slope, ADX_Slope_Days, ADX_Trend_Days, ADX_Bullish_Days, ADX_Bearish_Days, ADX_Strong_Days",
    read: "ADX misura la forza del trend, non la direzione: sotto 20 è lateralità, sopra 25 trend solido. La direzione la danno DI+ e DI-. ADX_Slope positivo indica forza in aumento.",
    note: "La soglia di ADX_Strong (>= 25) è cablata nel codice e non è configurabile.",
  },
  {
    id: "atr",
    title: "ATR e canali di uscita (volatilità)",
    formula: "ATR = ta-lib ATR. ATR_PCT = ATR / Close * 100. ATR_Upper = Close + 3*ATR, ATR_Lower = Close - 3*ATR. CE_Long = max(High, 22 sedute) - 3*ATR. CE_Short = min(Low, 22 sedute) + 3*ATR. ATR_Long_OK = Close > CE_Long.",
    params: "periodo 14, moltiplicatore 3.0, lookback 22",
    columns: "ATR, ATR_PCT, ATR_Upper, ATR_Lower, CE_Long, CE_Short, ATR_Long_OK, ATR_Short_OK",
    read: "ATR_PCT è la volatilità in percentuale: oltre 3% la posizione è considerata rischiosa e fa scattare l'avviso High Volatility. CE_Long è il canale di uscita tipo Chandelier, usato sia come stop di tendenza sia dentro il calcolo dello score e della zona di pullback.",
    note: "Il metodo set_atr_parameters ha default multiplier=2.0, ma l'istanza usa 3.0: il valore effettivo è 3.0.",
  },
  {
    id: "macd",
    title: "MACD (momentum di tendenza)",
    formula: "ta-lib MACD: MACD = EMA(12) - EMA(26), MACD_Signal = EMA(9) del MACD, MACD_Hist = MACD - Signal. MACD_vs_Signal è la striscia con segno: +n se MACD è sopra Signal da n sedute, -n se sotto. MACDH_Trend = Up/Down dall'istogramma. MACD_Positive_Days / MACD_Negative_Days contano le sedute con MACD sopra o sotto zero.",
    params: "fast 12, slow 26, signal 9",
    columns: "MACD, MACD_Signal, MACD_Hist, MACD_vs_Signal, MACDH_Trend, MACDH_Trend_Days, MACD_Positive_Days, MACD_Negative_Days, MACD_Sign_Streak, MCS, MCS_Smoothed, MCS_Conf, MCS_z_hist, MCS_z_slope, MCS_z_macd0, MCS_z_streak",
    read: "L'incrocio MACD sopra Signal è il trigger del pattern S3. MACD_vs_Signal è usato anche come ordinamento nella watchlist: 1 significa incrocio appena avvenuto. Un valore grande indica un incrocio vecchio, quindi meno fresco.",
    note: "MCS è un indicatore proprietario derivato dal MACD (z-score di istogramma, pendenza, distanza da zero e striscia, combinati 0.40/0.25/0.20/0.15 e lisciati); MCS_Conf ne misura l'affidabilità.",
  },
  {
    id: "rsi",
    title: "RSI (forza relativa)",
    formula: "ta-lib RSI a 14 sedute. RSI_Trend = Up/Down/Flat dalla differenza, RSI_Trend_Days = lunghezza della striscia.",
    params: "periodo 14",
    columns: "RSI, RSI_Trend, RSI_Trend_Days",
    read: "Sopra 50 il momentum è rialzista, sotto è ribassista. Sotto 30 ipervenduto, sopra 70 ipercomprato (lo score penalizza oltre 70). Nel pattern S5 la soglia usata è 30.",
  },
  {
    id: "willr",
    title: "Williams %R",
    formula: "ta-lib WILLR a 14 sedute, scala -100..0. WILLR_Overbought = vero sopra -20, WILLR_Oversold = vero sotto -80, WILLR_Neutral altrimenti. WILLR_Trend = Up/Down/Flat.",
    params: "periodo 14",
    columns: "Williams_R, WILLR_Trend, WILLR_Trend_Days, WILLR_Overbought, WILLR_Oversold, WILLR_Neutral",
    read: "Valori vicini a 0 indicano ipercomprato, vicini a -100 ipervenduto. Il pattern S2 richiede Williams %R crescente e sopra -80, cioè uscita dalla zona di ipervenduto.",
  },
  {
    id: "stoch",
    title: "Stocastico",
    formula: "ta-lib STOCH, valori limitati a 0..100. Stoch_KvsD = Stoch_K - Stoch_D (positivo = K sopra D). SK_Trend = Up/Down/Flat sulla K, SK_Trend_Days = lunghezza della striscia.",
    params: "fastk 14, slowk 3, slowd 3, matype 0 (nell'analisi principale). Lo scanner del Multi-Pattern Lab usa invece fastk 5.",
    columns: "Stoch_K, Stoch_D, Stoch_KvsD, SK_Trend, SK_Trend_Days",
    read: "Incrocio K sopra D = segnale rialzista di breve. Sotto 20 ipervenduto, sopra 80 ipercomprato. Attenzione: le soglie di ipervenduto usate valgono 20 nel trading state e 30 nei pattern S5/S9.",
    note: "Il periodo del fastk non è lo stesso in tutti i moduli: l'analisi principale usa 14, il Multi-Pattern Lab 5. È una divergenza nota fra i due percorsi.",
  },
  {
    id: "alligator",
    title: "Alligator di Bill Williams",
    formula: "Jaw = WMA(13) spostata di 8 sedute avanti, Teeth = WMA(8) spostata di 5, Lips = WMA(5) spostata di 3. L'ordine delle tre linee definisce lo stato.",
    params: "13/8/5 con shift 8/5/3",
    columns: "Alligator_Jaw, Alligator_Teeth, Alligator_Lips, Signal6 (+ descrizioni e Signal6_Trend_Days)",
    read: "Jaw più in alto = mercato che dorme; allineamento rialzista Jaw < Teeth < Lips con Close sopra Lips = Uptrend. wakeup1/wakeup2 sono le fasi di risveglio, Downtrend_revS3Sig+/++/+++ i tentativi di inversione.",
    note: "Sleep, wakeup, Uptrend e Downtrend descrivono la posizione del prezzo rispetto alle tre linee, non un segnale operativo diretto.",
  },
  {
    id: "ema",
    title: "Medie mobili e filtro SMA200",
    formula: "ta-lib EMA a 9, 21, 30, 50 sedute e SMA a 200 sedute sulla chiusura. Il backend duplica la EMA_30 nella colonna EMA30.",
    params: "EMA 9/21/30/50, SMA 200",
    columns: "EMA_9, EMA_21, EMA_30, EMA_50, EMA30, SMA200, SMA200_Filter_Ok",
    read: "EMA30 > EMA50 descrive la struttura rialzista (ordine delle medie), Close sopra la EMA30 la tenuta di breve. EMA9/EMA21 servono al pattern S4; la SMA200 al filtro di tendenza di lungo e al livello S7 Strong.",
  },
  {
    id: "sar",
    title: "Parabolic SAR",
    formula: "ta-lib SAR. SAR_Above_Price = SAR > Close. SAR_Flip_RunDown conta le sedute consecutive con SAR sotto il prezzo (run-down), SIG_MA_SAR è la striscia di validità della condizione Close > EMA30 AND SAR < Close.",
    params: "accelerazione 0.02, massimo 0.2",
    columns: "SAR, SAR_Above_Price, SIG_MA_SAR, SAR_Flip_RunDown",
    read: "SAR sotto il prezzo = trend rialzista in corso; il numero di sedute consecutive indica da quanto dura. SIG_MA_SAR a 1 significa condizione appena entrata (livello 1-2 = fresco), valori negativi condizione persa.",
  },
  {
    id: "volume",
    title: "Volumi e liquidità",
    formula: "Vol_Perc_vs_MA5/10/20 = (Volume - MA(n)) / MA(n) * 100. Vol_MA20 = media semplice dei volumi a 20 sedute. Vol_ZeroDays_30 e Vol_LowDays_30 contano le sedute senza volume o con volume molto basso nelle ultime 30. Vol_SpikeRatio_30 = massimo volume / volume medio.",
    params: "MA 5/10/20, finestra 30, soglie 2000 e 8000, spike 15x",
    columns: "Volume, Volume_MA20, Vol_MA20, Vol_Perc_vs_MA5, Vol_Perc_vs_MA10, Vol_Perc_vs_MA20, Vol_ZeroDays_30, Vol_LowDays_30, Vol_SpikeRatio_30, Liquidity",
    read: "Vol_Perc_vs_MA20 positivo significa volume sopra la media (conferma al breakout). Il pattern S4/S8 richiede Volume > MA20 * 1.5. Liquidity riassume tutto in OK / LOW / AVOID: AVOID blocca le indicazioni operative (Azione = AVOID) e WAIT, quindi i titoli illiquidi non ricevono mai BUY/ADD.",
    note: "Vol_MA20 e Volume_MA20 convivono senza un motivo chiaro: sono la stessa cosa calcolata in punti diversi del codice.",
  },
  {
    id: "performance",
    title: "Performance (variazioni percentuali)",
    formula: "PCTV_nD = (Close(t) / Close(t-n) - 1) * 100, con n in sedute di borsa (non giorni di calendario).",
    params: "1, 5, 10, 30, 180 sedute",
    columns: "PCTV_1D, PCTV_5D, PCTV_10D, PCTV_30D, PCTV_180D",
    read: "Usate per le tab Migliori/Peggiori, per l'ordinamento e come componente dello score (PCTV_5D pesa 50 + 5 * valore).",
  },
  {
    id: "score",
    title: "TECH_SCORE (punteggio tecnico 0-100)",
    formula: "TECH_SCORE = 0.35*TECH_STRUCTURE + 0.35*TECH_MOMENTUM + 0.30*TECH_PARTICIPATION - TECH_EXTENSION_PENALTY, limitato a 0..100. Struttura = posizione del prezzo rispetto a EMA30, EMA50, Alligator e SAR (50 = neutro). Momentum = media di MACD/Signal, istogramma crescente, livello RSI, trend RSI, Stoch K > D e PCTV_5D. Partecipazione = 70% forza direzionale da ADX/DI + 30% volumi. Penalità = fino a 20 punti tolti per estensione (distanza dalla EMA30, ATR_PCT, RSI, Stoch).",
    params: "pesi interni 0.35/0.35/0.30, scale 6% e 3%, ginocchia 4%/3%/70/80",
    columns: "TECH_SCORE, TECH_STRUCTURE, TECH_MOMENTUM, TECH_PARTICIPATION, TECH_EXTENSION_PENALTY",
    read: "Sintesi leggibile del quadro tecnico: sopra 65 sostiene le indicazioni di acquisto, sotto 35 le indicazioni di vendita; l'ordinamento della sezione Migliori tiene conto anche della penalità di estensione.",
  },
  {
    id: "fase",
    title: "Market_Phase e azione operativa",
    formula: "Market_Phase è decisa in ordine di priorità: BREAKOUT (nuovo massimo a 20 sedute con buffer 0.3%, ADX >= 25, istogramma MACD crescente, volume sopra media, stoch non ipercomprato e Signal6 rialzista), altrimenti REVERSAL_RISK, UPTREND (Close > EMA30 > EMA50 con DI+ > DI-), DOWNTREND simmetrico, PULLBACK (struttura rialzista con almeno 2 segnali di raffreddamento) e RANGE come ripiego. L'azione è poi filtrata dalla liquidità: AVOID se illiquido, WAIT se non OK, altrimenti BUY/SELL/ADD/REDUCE/EXIT/HOLD secondo trigger e soglie TECH_SCORE.",
    params: "ADX 20/25, RSI 45/50, TECH_SCORE 65/35, buffer breakout 0.3%",
    columns: "Market_Phase, Trend_Phase_Detail, Action, Action_Reason, Layer3_Warning, Trading_State, Layer1_Action, Layer2_Score, Layer2_Label",
    read: "Market_Phase dice in che stato è il titolo, Action cosa fare. Trend_Phase_Detail distingue la maturità del movimento (EARLY_TREND, EXPANSION, MATURE_TREND, OVEREXTENDED, PULLBACK_HEALTHY/NORMAL/RISKY). Layer3_Warning segnala le condizioni di cautela: volatilità alta, segnale fresco, momentum maturo, stocastico estremo.",
    note: "Un titolo con Liquidity diversa da OK non riceve mai BUY: l'azione ripiega su WAIT o AVOID.",
  },
  {
    id: "livelli",
    title: "Livelli operativi e rischio",
    formula: "Zona di pullback = max(EMA30, CE_Long) più o meno l'ATR (da +0.25 a -0.50 ATR). Trend_Stop_Level = EMA50. Profit_Protect_Level = max(EMA30 - 0.25 ATR, SAR). SL1_RiskPct e SL2_RiskPct esprimono la distanza percentuale del prezzo dagli stop di trend e dal canale CE_Long.",
    params: "buffer ATR 0.25 / 0.50, tipo stop STRUCTURE_EMA50",
    columns: "Pullback_Entry_Level, Pullback_Entry_Zone_Low, Pullback_Entry_Zone_High, Pullback_Stop_Level, Pullback_Invalidation, Pullback_Entry_Note, Trend_Stop_Level, Trend_Stop_Invalidation, Trend_Stop_Type, Profit_Protect_Level, Profit_Protect_Invalidation, Profit_Protect_Type, SL1_RiskPct, SL2_RiskPct, PB_RANK",
    read: "Pullback_Entry_Note dice se il prezzo è IN_ZONE (entrata a limite possibile), ABOVE_ZONE (attendi conferma), BELOW_ZONE (discesa troppo profonda) o INVALIDATED (sotto lo stop). SL1_RiskPct negativo indica di quanto il prezzo sta sopra lo stop.",
    note: "Questi livelli sono calcolati solo quando la fase è coerente (es. trend stop solo in UPTREND con BUY o ADD), quindi molte righe risultano vuote: è atteso.",
  },
  {
    id: "pattern",
    title: "Pattern S2-S9 (sezione Multi-Pattern Lab)",
    formula: "S2 Williams %R + Stoch in ripartenza; S3 incrocio MACD con volume sopra 1.2 volte la media; S4 EMA9 > EMA21 con RSI 55-70 crescente, MACD sopra Signal e volume sopra 1.5 volte la media; S5 RSI sotto 30 con incrocio rialzista dello stocastico; S6 Golden Cross EMA30/EMA50 con ADX > 25; S7 Early/Confirmed/Strong sono tre livelli di Alligator rialzista (con SAR e DI+, poi EMA30/EMA50 e ADX >= 20, infine ADX >= 25, sopra SMA200 e volume); S8 candela verde con volume sopra 1.5 volte la media; S9 ripartenza dopo sell-off (almeno 4 candele rosse su 6, calo del 7% in 10 sedute o drawdown del 10% dal massimo a 20, poi candela verde con RSI in recupero).",
    params: "soglie vedi sopra; stoch: 35/50 in S2, 20 in S5, 30 nel pattern S9",
    columns: "Pattern_S2..S9_Days_Ago (sedute dall'ultima occorrenza), Pattern_*_Match (booleano nella seduta), Pattern_Combined_*, Red_Candles_6, Selloff_Return_10_Pct, Selloff_Drawdown_20_Pct, Volume_Ratio_MA20, SAR_Filter_Ok, SMA200_Filter_Ok",
    read: "I *_Days_Ago misurano l'anzianità: 0 significa pattern attivo oggi, 999 nessuna occorrenza recente. Sono il dato usato dal Multi-Pattern Lab quando legge l'Excel invece di riscaricare i prezzi. I *Filter_Ok dicono se il titolo rispetta i filtri richiesti (sopra SAR, sopra SMA200) nella seduta del pattern.",
    note: "I Pattern_*_Match sono ridondanti: la stessa informazione è ricavabile da Days_Ago = 0, e il codice attuale legge Days_Ago.",
  },
  {
    id: "categoria",
    title: "Categorie e qualità del dato",
    formula: "Category / EntryTrigger / StopHint / Notes classificano il titolo combinando Signal6, TECH_SCORE e MCS (soglie 70/60/55/45). Data_Quality dipende dal numero di righe scaricate.",
    params: "soglie score 70/60/55/45, MCS_Conf 0.50",
    columns: "Category, EntryTrigger, StopHint, Notes, Data_Quality, History_Rows, Date",
    read: "Category è una lettura discorsiva (BUY NOW, BUY ON PULLBACK, WATCHLIST, REDUCE, REVERSAL CANDIDATE, HOLD, AVOID). Queste colonne sono prodotte solo se l'analisi gira con generateCategory attivo: nel main.py attuale è disattivato, quindi di norma non compaiono nel file.",
    note: "Nel main.py la chiamata usa generateCategory=0: Category, EntryTrigger, StopHint e Notes non vengono calcolate. Nella tabella compaiono come colonne vuote perché il backend le aggiunge comunque.",
  },
];

/** Ordine con cui main.py esegue i calcoli. */
const GUIDE_ORDER: string[] = [
  "1. Download OHLCV da Yahoo Finance (1 anno, daily)",
  "2. Indicatori di base: ADX/DI, ATR e derivati, volumi e liquidità, MACD (+MCS), RSI, Williams %R, Stocastico, Alligator, EMA e SMA200, Parabolic SAR, PCTV",
  "3. Segnali: SIG_MA_SAR, Signal6, segnali di inversione dello stocastico",
  "4. TECH_SCORE e sue componenti",
  "5. Market_Phase, Trend_Phase_Detail, Action e livelli operativi",
  "6. Pattern S2-S9 e relative metriche",
  "7. Scrittura atomica del workbook e invio degli alert",
];

/** Suffissi ricorrenti nei nomi delle colonne. */
const GUIDE_SUFFIXES: Array<{ name: string; text: string }> = [
  { name: "_Trend", text: "direzione dell'indicatore: Up, Down o Flat" },
  { name: "_Trend_Days", text: "quante sedute consecutive dura quella direzione" },
  { name: "_Days", text: "numero di sedute consecutive nello stato" },
  { name: "_Change", text: "differenza rispetto alla seduta precedente" },
  { name: "_PCT", text: "valore espresso in percentuale del prezzo" },
  { name: "Vol_Perc_vs_MA*", text: "scostamento percentuale del volume dalla sua media" },
  { name: "_Days_Ago", text: "sedute trascorse dall'ultima occorrenza (999 = mai)" },
  { name: "_Match", text: "1 se la condizione è vera nella seduta, 0 altrimenti" },
  { name: "_OK", text: "flag booleano: condizione rispettata" },
  { name: "_Conf", text: "affidabilità del segnale MCS, da 0 a 1" },
  { name: "_z_*", text: "componente normalizzata (z-score) dell'MCS" },
  { name: "_Score", text: "punteggio numerico, non una percentuale" },
];

const COLUMN_META: Record<string, ColumnMeta> = {
  Date: { label: "Data", kind: "date", group: "Titolo" },
  Ticker: { label: "Ticker", kind: "text", group: "Titolo" },
  Name: { label: "Nome", kind: "text", group: "Titolo" },
  Open: { label: "Open", kind: "number", digits: 3, group: "Prezzo" },
  High: { label: "High", kind: "number", digits: 3, group: "Prezzo" },
  Low: { label: "Low", kind: "number", digits: 3, group: "Prezzo" },
  Close: { label: "Prezzo", kind: "number", digits: 3, group: "Prezzo" },
  "Adj Close": { label: "Adj Close", kind: "number", digits: 3, group: "Prezzo" },
  PCTV_1D: { label: "1D", kind: "percent", group: "Performance" },
  PCTV_5D: { label: "5D", kind: "percent", group: "Performance" },
  PCTV_10D: { label: "10D", kind: "percent", group: "Performance" },
  PCTV_30D: { label: "30D", kind: "percent", group: "Performance" },
  PCTV_180D: { label: "180D", kind: "percent", group: "Performance" },
  TECH_SCORE: { label: "TECH", kind: "number", digits: 0, group: "Score" },
  TECH_STRUCTURE: { label: "Struttura", kind: "number", digits: 0, group: "Score" },
  TECH_MOMENTUM: { label: "Momentum", kind: "number", digits: 0, group: "Score" },
  TECH_PARTICIPATION: { label: "Partecipazione", kind: "number", digits: 0, group: "Score" },
  TECH_EXTENSION_PENALTY: { label: "Penalità", kind: "number", digits: 0, group: "Score" },
  Entry_Signal: { label: "Segnale", kind: "text", group: "Scenario" },
  Entry_Reason: { label: "Motivo segnale", kind: "text", group: "Scenario" },
  Action: { label: "Azione", kind: "text", group: "Scenario" },
  Action_Reason: { label: "Motivo azione", kind: "text", group: "Scenario" },
  Market_Phase: { label: "Scenario", kind: "text", group: "Scenario" },
  Trend_Phase_Detail: { label: "Dettaglio trend", kind: "text", group: "Scenario" },
  Trading_State: { label: "Stato", kind: "text", group: "Scenario" },
  Layer1_Action: { label: "Layer1", kind: "text", group: "Scenario" },
  Layer2_Score: { label: "Layer2 score", kind: "number", digits: 0, group: "Scenario" },
  Layer2_Label: { label: "Layer2", kind: "text", group: "Scenario" },
  Layer3_Warning: { label: "Layer3 avvisi", kind: "text", group: "Scenario" },
  SL1_RiskPct: { label: "Rischio SL1 %", kind: "percent", group: "Trend" },
  SL2_RiskPct: { label: "Rischio SL2 %", kind: "percent", group: "Trend" },
  PB_RANK: { label: "Rank pullback", kind: "number", digits: 0, group: "Trend" },
  Pullback_Entry_Level: { label: "PB entrata", kind: "number", digits: 3, group: "Trend" },
  Pullback_Entry_Zone_Low: { label: "PB zona bassa", kind: "number", digits: 3, group: "Trend" },
  Pullback_Entry_Zone_High: { label: "PB zona alta", kind: "number", digits: 3, group: "Trend" },
  Pullback_Stop_Level: { label: "PB stop", kind: "number", digits: 3, group: "Trend" },
  Pullback_Invalidation: { label: "PB invalidato", kind: "bool", group: "Trend" },
  Pullback_Entry_Note: { label: "PB nota", kind: "text", group: "Trend" },
  Trend_Stop_Level: { label: "Trend stop", kind: "number", digits: 3, group: "Trend" },
  Trend_Stop_Invalidation: { label: "Trend stop inv.", kind: "bool", group: "Trend" },
  Trend_Stop_Type: { label: "Trend stop tipo", kind: "text", group: "Trend" },
  Profit_Protect_Level: { label: "Profit protect", kind: "number", digits: 3, group: "Trend" },
  Profit_Protect_Invalidation: { label: "Profit protect inv.", kind: "bool", group: "Trend" },
  Profit_Protect_Type: { label: "Profit protect tipo", kind: "text", group: "Trend" },
  EMA30: { label: "EMA30 (alias)", kind: "number", digits: 3, group: "Medie" },
  ADX: { label: "ADX", kind: "number", digits: 1, group: "DMI" },
  PLUS_DI: { label: "DI+", kind: "number", digits: 1, group: "DMI" },
  MINUS_DI: { label: "DI-", kind: "number", digits: 1, group: "DMI" },
  DI_diff: { label: "DI diff", kind: "number", digits: 1, group: "DMI" },
  ATR: { label: "ATR", kind: "number", digits: 3, group: "Volatilità" },
  ATR_PCT: { label: "ATR %", kind: "number", digits: 2, group: "Volatilità" },
  ATR_Upper: { label: "ATR Upper", kind: "number", digits: 3, group: "Volatilità" },
  ATR_Lower: { label: "ATR Lower", kind: "number", digits: 3, group: "Volatilità" },
  CE_Long: { label: "CE Long", kind: "number", digits: 3, group: "Volatilità" },
  CE_Short: { label: "CE Short", kind: "number", digits: 3, group: "Volatilità" },
  Volume: { label: "Volume", kind: "number", digits: 0, group: "Volume" },
  Volume_MA20: { label: "Vol MA20", kind: "number", digits: 0, group: "Volume" },
  Vol_Perc_vs_MA5: { label: "Vol vs MA5", kind: "percent", group: "Volume" },
  Vol_Perc_vs_MA10: { label: "Vol vs MA10", kind: "percent", group: "Volume" },
  Vol_Perc_vs_MA20: { label: "Vol vs MA20", kind: "percent", group: "Volume" },
  Liquidity: { label: "Liquidità", kind: "text", group: "Volume" },
  EMA_9: { label: "EMA9", kind: "number", digits: 3, group: "Medie" },
  EMA_21: { label: "EMA21", kind: "number", digits: 3, group: "Medie" },
  EMA_30: { label: "EMA30", kind: "number", digits: 3, group: "Medie" },
  EMA_50: { label: "EMA50", kind: "number", digits: 3, group: "Medie" },
  SMA200: { label: "SMA200", kind: "number", digits: 3, group: "Medie" },
  RSI: { label: "RSI", kind: "number", digits: 1, group: "Oscillatori" },
  Stoch_K: { label: "Stoch K", kind: "number", digits: 1, group: "Oscillatori" },
  Stoch_D: { label: "Stoch D", kind: "number", digits: 1, group: "Oscillatori" },
  Stoch_KvsD: { label: "K-D", kind: "number", digits: 2, group: "Oscillatori" },
  Williams_R: { label: "Will %R", kind: "number", digits: 1, group: "Oscillatori" },
  MACD: { label: "MACD", kind: "number", digits: 3, group: "MACD" },
  MACD_Signal: { label: "Signal", kind: "number", digits: 3, group: "MACD" },
  MACD_Hist: { label: "Hist", kind: "number", digits: 3, group: "MACD" },
  MACD_vs_Signal: { label: "MACD-Signal", kind: "number", digits: 3, group: "MACD" },
  MCS: { label: "MCS", kind: "number", digits: 2, group: "MACD" },
  MCS_Smoothed: { label: "MCS smoothed", kind: "number", digits: 2, group: "MACD" },
  MCS_Conf: { label: "MCS conf", kind: "number", digits: 2, group: "MACD" },
  Signal6: { label: "Alligator", kind: "text", group: "Trend" },
  Signal6_Trend_Days: { label: "Alligator giorni", kind: "number", digits: 0, group: "Trend" },
  SAR: { label: "SAR", kind: "number", digits: 3, group: "Trend" },
  SAR_Above_Price: { label: "SAR sopra prezzo", kind: "bool", group: "Trend" },
  SIG_MA_SAR: { label: "SARMA", kind: "number", digits: 0, group: "Trend" },
  Pattern_S2_Days_Ago: { label: "S2 giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S3_Days_Ago: { label: "S3 giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_Combined_Days_Ago: { label: "S2&S3 giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S4_Days_Ago: { label: "S4 giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S5_Days_Ago: { label: "S5 giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S6_Days_Ago: { label: "S6 giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S7_Days_Ago: { label: "S7 giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S7_EARLY_Days_Ago: { label: "S7 early giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S7_CONFIRMED_Days_Ago: { label: "S7 conf giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S7_STRONG_Days_Ago: { label: "S7 strong giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S8_Days_Ago: { label: "S8 giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S9_Days_Ago: { label: "S9 giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S9_EARLY_Days_Ago: { label: "S9 early giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_S9_CONFIRMED_Days_Ago: { label: "S9 conf giorni", kind: "number", digits: 0, group: "Pattern" },
  Pattern_Type: { label: "Pattern", kind: "text", group: "Pattern" },
  Pattern_Days_Ago: { label: "Pattern giorni", kind: "number", digits: 0, group: "Pattern" },
  Data_Quality: { label: "Qualità dati", kind: "text", group: "Dati" },
  History_Rows: { label: "Storico", kind: "number", digits: 0, group: "Dati" },
  Market: { label: "Mercato", kind: "text", group: "Dati" },
};

/** Colonne in coda alla tabella: sono derivate dalla UI, non dall'Excel. */
const UI_KEYS = new Set(["WL_Source_Market", "Chart_Data_Source", "Chart_Data_Fetched_At"]);

/**
 * Colonne che risultano prive di consumatori logici (audit su tutto il codice):
 * nessun modulo le legge per nome. Restano calcolate e salvate nell'Excel, ma
 * sono nascoste di default in questa tabella per non allargarla inutilmente.
 * L'interruttore "Mostra colonne inutilizzate" le riporta in vista.
 */
const UNUSED_COLUMNS = new Set([
  // Pattern: la stessa informazione è in *_Days_Ago, che è ciò che lo scanner legge.
  "Pattern_Combined_Match", "Pattern_S2_Match", "Pattern_S3_Match", "Pattern_S4_Match",
  "Pattern_S5_Match", "Pattern_S6_Match", "Pattern_S7_Match", "Pattern_S7_EARLY_Match",
  "Pattern_S7_CONFIRMED_Match", "Pattern_S7_STRONG_Match", "Pattern_S8_Match",
  "Pattern_S9_Match", "Pattern_S9_EARLY_Match", "Pattern_S9_CONFIRMED_Match",
  // Contatori di giorni mai letti (restano ADX_Slope e ADX_Trend, che servono).
  "ADX_Bullish_Days", "ADX_Bearish_Days", "ADX_Strong_Days", "ADX_Slope_Days",
  // Segnali stocastici salvati con nomi che nessuno legge (il trading state usa
  // Entry_Signal/Exit_Signal, generati altrove).
  "sk_trad_signal", "sk_Entry_Signal", "sk_Exit_Signal",
  // Ridondanti o duplicati.
  "MCS_z_hist", "MACD_Sign_Streak", "WILLR_Neutral", "Vol_MA20",
]);

const PREFERRED_ORDER = [
  "Date", "Ticker", "Name", "Market", "Close",
  "Entry_Signal", "Entry_Reason", "Action", "Action_Reason", "Market_Phase", "Trend_Phase_Detail",
];

const ACRONYMS = new Set([
  "adx", "atr", "macd", "macdh", "rsi", "sar", "ema", "sma", "ma", "pctv", "mcs", "di", "sk", "willr",
  "ce", "vol", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "pb", "sl1", "sl2", "ok", "ai", "wl", "id",
]);

const LABEL_OVERRIDES: Record<string, string> = {
  MACDH_Trend: "MACDH Trend",
  MACDH_Trend_Days: "MACDH giorni",
  RSI_Trend_Days: "RSI giorni",
  SK_Trend_Days: "Stoch K giorni",
  WILLR_Trend_Days: "Will %R giorni",
  ADX_Trend_Days: "ADX giorni",
  Signal6_Trend_Days: "Alligator giorni",
  Vol_ZeroDays_30: "Vol zero (30g)",
  Vol_LowDays_30: "Vol bassi (30g)",
  Vol_SpikeRatio_30: "Vol spike ratio (30g)",
  ATR_Long_OK: "ATR long OK",
  ATR_Short_OK: "ATR short OK",
  UPTREDING_COOLING: "UPTRENDING COOLING",
};

/**
 * Gruppo di ripiego per le colonne non descritte in COLUMN_META: senza questo
 * tutte finirebbero in un unico gruppo enorme, rendendo inutile il filtro.
 * È solo presentazione: le colonne vengono mostrate in ogni caso.
 */
const GROUP_BY_PREFIX: Array<[RegExp, string]> = [
  [/^ADX|_DI\b|^DI_|^PLUS_DI|^MINUS_DI/, "DMI"],
  [/^ATR|^CE_/, "Volatilità"],
  [/^MACD|^MCS/, "MACD"],
  [/^EMA|^SMA|^MA_/, "Medie"],
  [/^RSI|^Stoch|^SK_|^Williams|^WILLR/, "Oscillatori"],
  [/^PCTV/, "Performance"],
  [/^Vol_|^Volume/, "Volume"],
  [/^Pattern/, "Pattern"],
  [/^Pullback|^Trend_Stop|^Profit_Protect|^PB_/, "Trend"],
  [/^SL1_|^SL2_/, "Trend"],
  [/^TECH_/, "Score"],
  [/^Data_Quality|^History_Rows|^Market$/, "Dati"],
];

function groupForKey(key: string): string {
  for (const [pattern, group] of GROUP_BY_PREFIX) {
    if (pattern.test(key)) return group;
  }
  return "Altre colonne";
}

function labelForKey(key: string): string {
  const override = LABEL_OVERRIDES[key];
  if (override) return override;
  return key
    .split("_")
    .map((part) => {
      if (!part) return part;
      const lower = part.toLowerCase();
      if (ACRONYMS.has(lower)) return lower.toUpperCase();
      if (/^\d+[A-Za-z]*$/.test(part)) return part.toUpperCase();
      return part.charAt(0).toUpperCase() + part.slice(1);
    })
    .join(" ");
}

function numericValue(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "boolean") return value ? 1 : 0;
  if (typeof value === "string") {
    const text = value.trim();
    if (!text) return null;
    const parsed = Number(text.replace(/\s/g, "").replace(/[\u202f\u00a0]/g, "").replace(",", "."));
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function isBlank(value: unknown): boolean {
  return value === null || value === undefined || value === "" || value === "-";
}

/** Deduce tipo e decimali di una colonna non descritta in COLUMN_META. */
function inferKind(rows: WatchlistRow[], key: string): { kind: ColumnKind; digits: number } {
  const values: unknown[] = [];
  for (const row of rows) {
    const value = row[key];
    if (isBlank(value)) continue;
    values.push(value);
    if (values.length >= 40) break;
  }
  if (!values.length) return { kind: "text", digits: 0 };

  let numeric = 0;
  let booleans = 0;
  let decimals = 0;
  for (const value of values) {
    if (typeof value === "boolean") { booleans += 1; numeric += 1; continue; }
    if (typeof value === "number" && Number.isFinite(value)) {
      numeric += 1;
      const text = String(value);
      const dot = text.indexOf(".");
      if (dot >= 0) decimals = Math.max(decimals, text.length - dot - 1);
      continue;
    }
    if (typeof value === "string" && numericValue(value) !== null) {
      const normalized = value.replace(",", ".");
      const dot = normalized.indexOf(".");
      if (dot >= 0) decimals = Math.max(decimals, normalized.length - dot - 1);
      numeric += 1;
    }
  }
  if (numeric !== values.length) return { kind: "text", digits: 0 };
  if (booleans === values.length) return { kind: "bool", digits: 0 };
  const cents = Math.max(0, Math.min(4, decimals));
  const whole = values.every((value) => typeof value === "boolean" || Math.abs(Number(numericValue(value) ?? 0)) >= 1000);
  return { kind: "number", digits: whole ? 0 : cents };
}

function buildColumns(rows: WatchlistRow[], includeUnused: boolean): Column[] {
  // L'ordine delle chiavi di ogni riga riproduce quello del DataFrame, quindi
  // l'ordine delle colonne dell'Excel viene preservato.
  const ordered: string[] = [];
  const seen = new Set<string>();
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (key === "__proto__" || seen.has(key)) continue;
      seen.add(key);
      if (UI_KEYS.has(key)) continue;
      if (!includeUnused && UNUSED_COLUMNS.has(key)) continue;
      ordered.push(key);
    }
  }

  const known = ordered.filter((key) => key in COLUMN_META);
  const unknown = ordered.filter((key) => !(key in COLUMN_META));
  const decorated = [...known, ...unknown].map((key) => {
    const meta = COLUMN_META[key] ?? {};
    const inferred = meta.kind ? { kind: meta.kind, digits: meta.digits ?? 0 } : inferKind(rows, key);
    return {
      key,
      label: meta.label ?? labelForKey(key),
      kind: inferred.kind,
      digits: meta.digits ?? inferred.digits,
      group: meta.group ?? groupForKey(key),
    };
  });

  const rank = (key: string) => {
    const index = PREFERRED_ORDER.indexOf(key);
    if (index >= 0) return index;
    return key in COLUMN_META ? PREFERRED_ORDER.length : PREFERRED_ORDER.length + 1;
  };
  return decorated.sort((a, b) => rank(a.key) - rank(b.key));
}

function formatValue(row: WatchlistRow, column: Column): string {
  const value = row[column.key];
  if (isBlank(value)) return "-";
  if (column.kind === "date") return String(value).slice(0, 10);
  const parsed = numericValue(value);
  if (column.kind === "percent") {
    if (parsed === null) return String(value);
    return `${parsed > 0 ? "+" : ""}${parsed.toFixed(2)}%`;
  }
  if (column.kind === "number") {
    if (parsed === null) return String(value);
    return parsed.toLocaleString("it-IT", {
      minimumFractionDigits: column.digits ?? 0,
      maximumFractionDigits: column.digits ?? 0,
    });
  }
  if (column.kind === "bool") {
    if (typeof value === "boolean") return value ? "Sì" : "No";
    if (parsed !== null) return parsed ? "Sì" : "No";
  }
  return String(value).replace(/_/g, " ");
}

const SIGNED_KEYS = new Set([
  "PCTV_1D", "PCTV_5D", "PCTV_10D", "PCTV_30D", "PCTV_180D",
  "PCTV_5D", "MACD_vs_Signal", "MACD_Hist", "DI_diff", "Vol_Perc_vs_MA20",
  "Vol_Perc_vs_MA10", "Vol_Perc_vs_MA5", "Selloff_Return_10_Pct", "Selloff_Drawdown_20_Pct",
  "ADX_Change", "SL1_RiskPct", "SL2_RiskPct",
]);

function valueClass(row: WatchlistRow, column: Column): string {
  const parsed = numericValue(row[column.key]);
  if (parsed === null || parsed === 0) return "";
  if (SIGNED_KEYS.has(column.key)) return parsed > 0 ? "positive" : "negative";
  if (column.key === "PLUS_DI") return "positive";
  if (column.key === "MINUS_DI") return "negative";
  if (column.kind === "bool") return parsed ? "positive" : "negative";
  return "";
}

function compareRows(a: WatchlistRow, b: WatchlistRow, key: string, dir: "asc" | "desc"): number {
  const av = a[key];
  const bv = b[key];
  const an = numericValue(av);
  const bn = numericValue(bv);
  let result = 0;
  if (an !== null || bn !== null) result = (an ?? Number.NEGATIVE_INFINITY) - (bn ?? Number.NEGATIVE_INFINITY);
  else result = String(av ?? "").localeCompare(String(bv ?? ""), "it", { sensitivity: "base" });
  return dir === "asc" ? result : -result;
}

function hasAnyValue(rows: WatchlistRow[], key: string): boolean {
  if (["Ticker", "Name", "Date"].includes(key)) return true;
  return rows.some((row) => !isBlank(row[key]));
}

function fmtSourceTs(value?: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("it-IT");
}

export default function IndicatorsTablePanel({ rows, market, loading, error, sourcePath, sourceUpdatedAt, onChart, onAi }: Props) {
  const [search, setSearch] = useState("");
  const [group, setGroup] = useState("Tutte");
  const [hideEmpty, setHideEmpty] = useState(false);
  const [showUnused, setShowUnused] = useState(false);
  const [sortKey, setSortKey] = useState("Ticker");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const allColumns = useMemo(() => buildColumns(rows, showUnused), [rows, showUnused]);
  const hiddenUnusedCount = useMemo(
    () => (showUnused ? 0 : buildColumns(rows, true).filter((column) => UNUSED_COLUMNS.has(column.key)).length),
    [rows, showUnused]
  );

  const groups = useMemo(
    () => ["Tutte", ...Array.from(new Set(allColumns.map((column) => column.group)))],
    [allColumns]
  );

  const filteredRows = useMemo(() => {
    const term = search.trim().toLowerCase();
    const base = term
      ? rows.filter((row) => `${String(row.Ticker ?? "")} ${String(row.Name ?? "")}`.toLowerCase().includes(term))
      : rows;
    return [...base].sort((a, b) => compareRows(a, b, sortKey, sortDir));
  }, [rows, search, sortKey, sortDir]);

  const columns = useMemo(() => {
    return allColumns.filter((column) => {
      if (group !== "Tutte" && column.group !== group) return false;
      if (hideEmpty && !hasAnyValue(rows, column.key)) return false;
      return true;
    });
  }, [allColumns, group, hideEmpty, rows]);

  function handleSort(key: string) {
    if (sortKey === key) setSortDir((current) => current === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("asc"); }
  }

  return (
    <section className="indicators-panel">
      <div className="indicators-heading">
        <div>
          <h2>📈 Indicatori calcolati · {market}</h2>
          <p className="muted">
            Tutte le colonne del file di analisi del mercato selezionato, nell'ordine in cui compaiono
            nell'Excel{hiddenUnusedCount ? `; ${hiddenUnusedCount} colonne senza consumatori logici sono nascoste (riattivabili dal comando qui sotto)` : ""}.
            Le colonne in coda al gruppo «{groups[groups.length - 1]}» non hanno un'etichetta dedicata ma
            sono mostrate e ordinabili.
          </p>
          <p className="source-meta compact">Last update: {fmtSourceTs(sourceUpdatedAt)} · Source: <span className="source-path">{sourcePath ?? "-"}</span></p>
        </div>
        <div className="indicator-stats">
          <strong>{filteredRows.length}</strong>
          <span>ticker visualizzati</span>
        </div>
      </div>

      <div className="indicators-toolbar">
        <label>
          Cerca
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Ticker o nome" />
        </label>
        <label>
          Gruppo colonne
          <select value={group} onChange={(event) => setGroup(event.target.value)}>
            {groups.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label className="indicator-check">
          <input type="checkbox" checked={hideEmpty} onChange={(event) => setHideEmpty(event.target.checked)} />
          Nascondi colonne vuote
        </label>
        <label className="indicator-check">
          <input type="checkbox" checked={showUnused} onChange={(event) => setShowUnused(event.target.checked)} />
          Mostra colonne inutilizzate
        </label>
        <span className="indicator-column-count">
          <strong>{columns.length}</strong> / {allColumns.length} colonne
          {hiddenUnusedCount ? <em className="indicator-column-hidden"> · {hiddenUnusedCount} nascoste</em> : null}
        </span>
      </div>

      {loading ? <p>Carico indicatori...</p> : null}
      {error ? <p className="err">{error}</p> : null}
      {!loading && !error ? (
        <div className="indicators-table-wrap">
          <table className="indicators-table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column.key} className={column.key === "Ticker" ? "sticky-ticker" : undefined}>
                    <button className={sortKey === column.key ? "table-sort active" : "table-sort"} onClick={() => handleSort(column.key)}>
                      <small>{column.group}</small>
                      {column.label}{sortKey === column.key ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                    </button>
                  </th>
                ))}
                <th>Azioni</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row, index) => (
                <tr key={`${String(row.Ticker ?? "-")}-${index}`}>
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={`${column.kind === "number" || column.kind === "percent" ? "numeric" : ""} ${valueClass(row, column)} ${column.key === "Ticker" ? "sticky-ticker" : ""}`}
                    >
                      {formatValue(row, column)}
                    </td>
                  ))}
                  <td className="table-actions sticky-actions">
                    <button className="btn" onClick={() => onChart(row)}>Grafico</button>
                    <button className="btn ghost" onClick={() => onAi(row)}>AI</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!filteredRows.length ? <p className="muted empty-indicators">Nessun ticker trovato con questi filtri.</p> : null}
          {filteredRows.length && !columns.length ? <p className="muted empty-indicators">Nessuna colonna da mostrare con questi filtri.</p> : null}
        </div>
      ) : null}

      {/* ══════════════ GUIDA INDICATORI (fondo pagina) ══════════════ */}
      <details className="indicators-guide">
        <summary>
          <span>📚 Guida agli indicatori e modalità di calcolo</span>
          <small>{INDICATOR_GUIDE.length} famiglie · come sono calcolate e come si leggono</small>
        </summary>
        <div className="indicators-guide-body">
          <section className="indicators-guide-block">
            <h3>Convenzioni comuni</h3>
            <ul className="indicators-guide-conventions">
              {GUIDE_CONVENTIONS.map((item) => (
                <li key={item.title}><strong>{item.title}</strong> {item.text}</li>
              ))}
            </ul>
          </section>

          <section className="indicators-guide-block">
            <h3>Ordine di calcolo in main.py</h3>
            <ol className="indicators-guide-order">
              {GUIDE_ORDER.map((step) => <li key={step}>{step}</li>)}
            </ol>
          </section>

          {INDICATOR_GUIDE.map((group) => (
            <section className="indicators-guide-block" key={group.id}>
              <h3>{group.title}</h3>
              <dl className="indicators-guide-details">
                <dt>Come si calcola</dt>
                <dd>{group.formula}</dd>
                <dt>Parametri</dt>
                <dd>{group.params}</dd>
                <dt>Colonne</dt>
                <dd><code>{group.columns}</code></dd>
                <dt>Come si legge</dt>
                <dd>{group.read}</dd>
                {group.note ? (<><dt>Nota</dt><dd className="indicators-guide-note">{group.note}</dd></>) : null}
              </dl>
            </section>
          ))}

          <section className="indicators-guide-block">
            <h3>Suffissi ricorrenti nei nomi delle colonne</h3>
            <ul className="indicators-guide-suffixes">
              {GUIDE_SUFFIXES.map((item) => (
                <li key={item.name}><code>{item.name}</code> {item.text}</li>
              ))}
            </ul>
          </section>

          <section className="indicators-guide-block">
            <h3>Colonne nascoste perché senza consumatori</h3>
            <p className="indicators-guide-intro">
              Un audit su tutto il codice ha verificato quali colonne vengono lette da qualcuno. Le {UNUSED_COLUMNS.size} seguenti
              non sono lette da nessun modulo per nome: restano calcolate e salvate nell'Excel, ma qui sono nascoste per
              non allargare la tabella. Il comando «Mostra colonne inutilizzate» le riporta in vista.
            </p>
            <dl className="indicators-guide-details">
              <dt>Pattern_*_Match (14)</dt>
              <dd>
                Flag booleani di S2-S9 (Combined, S2..S6, S7, S7 Early/Confirmed/Strong, S8, S9, S9 Early/Confirmed).
                Ridondanti: la stessa informazione sta in <code>Pattern_*_Days_Ago</code>, che è ciò che lo scanner legge
                davvero. Anche i filtri applicati da main.py usano le serie interne, non queste colonne.
              </dd>
              <dt>ADX_Bullish_Days, ADX_Bearish_Days, ADX_Strong_Days, ADX_Slope_Days (4)</dt>
              <dd>
                Contatori di giorni consecutivi mai letti. Attenzione: <code>ADX_Slope</code> e <code>ADX_Trend</code> restano
                visibili, perché usati dalle regole di mercato e da uno script di backtest.
              </dd>
              <dt>sk_trad_signal, sk_Entry_Signal, sk_Exit_Signal (3)</dt>
              <dd>
                Segnali di inversione dello stocastico salvati con nomi personalizzati che nessuno legge: il trading state
                usa <code>Entry_Signal</code> ed <code>Exit_Signal</code>, generati da un altro percorso.
              </dd>
              <dt>MCS_z_hist, MACD_Sign_Streak, WILLR_Neutral, Vol_MA20 (4)</dt>
              <dd>
                Ridondanti: <code>MCS_z_hist</code> è una componente dell'MCS, <code>MACD_Sign_Streak</code> ripete
                <code>MACD_vs_Signal</code>, <code>WILLR_Neutral</code> è l'inverso di ipercomprato/ipervenduto e
                <code>Vol_MA20</code> duplica <code>Volume_MA20</code>.
              </dd>
            </dl>
            <p className="indicators-guide-intro">
              Non sono invece rimovibili <code>SAR_Filter_Ok</code> e <code>SMA200_Filter_Ok</code>: sono colonne obbligatorie
              per la scansione precalcolata, e senza di esse i pattern cadono sul download in tempo reale o restituiscono
              un errore. Restano pure necessarie <code>Alligator_Jaw/Teeth/Lips</code>, <code>ADX_Slope</code>, <code>ADX_Cross</code>,
              <code>ADX_Strong</code>, <code>SK_Trend</code>, <code>WILLR_Trend/Overbought/Oversold</code>,
              <code>MACD_Positive_Days</code>, <code>MACD_Negative_Days</code>, <code>MCS_z_slope</code>,
              <code>MCS_z_macd0</code>, <code>MCS_z_streak</code> e <code>SAR_Flip_RunDown</code>: alimentano lo score, i grafici o
              le configurazioni di backtest.
            </p>
          </section>
        </div>
      </details>
    </section>
  );
}
