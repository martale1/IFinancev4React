Utilizzo della class TechnicalAnalyzer

from TechnicalAnalyzer import TechnicalAnalyzer
ticker="RACE.MI"
ta = TechnicalAnalyzer(ticker, period="2y")
ta.calculate_TA_Indicators("MACD,RSI,SAR,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30,PCTV")
Questa e` tabella create con la funzione indicata sopra
 Open   High    Low  Close  Adj Close  Volume    MACD  MACD_Signal  MACD_Hist MACDH_Trend
 MACDH_Trend_Days    MCS  MCS_Smoothed  MCS_Conf  MCS_z_hist  MCS_z_slope  MCS_z_macd0  MCS_z_streak
 EMA_50   EMA_30     RSI RSI_Trend  RSI_Trend_Days  Williams_R WILLR_Trend  WILLR_Trend_Days
 WILLR_Overbought  WILLR_Oversold  WILLR_Neutral  Stoch_K  Stoch_D SK_Trend  SK_Trend_Days  Alligator_Jaw
 Alligator_Teeth  Alligator_Lips  PCTV_1D  PCTV_5D  PCTV_10D  PCTV_30D  PCTV_180D SAR  SAR_Above_Price


ta.calculate_alligator_signal6()
Questa aggiunge le colonne: Signal6  Signal6_Trend_Days


Questa aggiunge: TECH_SCORE
La seconda tiene conto anche di signal6 per calcolare lo scoring
>>ta.calculate_technical_score(weights=custom_weights)
>>ta.calculate_technical_score_with_signal6(weights=custom_weights)


Questa aggiunge l'indicazione di trading BUY, WATCHLIST, BUY ON PULLBACK, ETC
>>ta.add_category()  # crea Category, EntryTrigger, StopHint, Notes
Questa aggiunge: Category, EntryTrigger, StopHint,Notes

-  - -  Regole ed indicazioni per segnale MACD - - -
Trend / Momentum / Qualità

min_streak (int, default 7)
Quanti giorni consecutivi con MACD > 0 servono prima di considerare il titolo “in trend”.

Più alto → ingressi più lenti ma più robusti (9–12).

Più basso → ingressi anticipati ma più rumorosi (5–6).

conf_min (float, default 0.30)
Soglia minima di MCS_Conf (0..1). Filtra i segnali con bassa qualità/affidabilità.

0.25–0.35 tipico; 0.40–0.50 per selezione “premium”.

pct1d_range (tuple, default (-1.5, 2.0))
Finestra di variazione % giornaliera ammessa per gli ingressi base (evita “chasing”).

Stringi per evitare rimbalzi eccessivi: (-1.0, 1.5).

Allarga per titoli molto volatili: (-2.5, 3.5).

require_signal6_up (bool, default True)
Richiede che Signal6 sia in famiglia Uptrend/Wakeup. Aumenta la qualità del trend di fondo.

require_close_above_ema30 (bool, default True)
Richiede Close > EMA_30. Evita ingressi contro-trend di prezzo.

cap_score (int, default 100)
Tetto massimo al punteggio (“ranking”) scritto in score_column.

Lascia 100 salvo esigenze specifiche.

score_column (str, default "SIG_MACD_STREAK")
Nome della colonna score (0..cap_score). Usi questa per ordinare i titoli.

Breakout (via alternativa di ingresso)

use_breakout (bool, default True)
Abilita l’ingresso alternativo solo su breakout del massimo N barre con volume e MACDH in ripresa.

Nota: quando RSI ≥ rsi_ob_hard, questa diventa l’unica via consentita.

breakout_lookback (int, default 5)
Lookback (in barre) per il massimo su cui fare breakout (calcolato fino a ieri).

5–10 tipico daily; 10–20 su titoli meno volatili.

vol_break_min (float, default 20.0)
Minimo % vs MA20 volumi per convalidare il breakout.

Aumenta (30–50) per più rigore; diminuisci (10–15) se il titolo è poco liquido.

Segnale impulsivo (opzionale)

gen_impulse_signal (bool, default False)
Se True, scrive anche il segnale +1/-1/0 in impulse_col.

+1 quando “eligible” (ingresso)

−1 su condizioni di exit (esaurimento, inversione, perdita struttura, RSI debole)

impulse_col (str, default "Trading_Signal_MACD")
Nome della colonna del segnale impulsivo.

RSI (gates, score ed exit)

rsi_min (float, default 50.0)
Valore minimo di RSI per ammettere l’ingresso base.

50→ bias long; 55 se vuoi più selettivo; 48 se vuoi anticipare.

rsi_trend_required (str, default "Up")
Richiede RSI_Trend == "Up" (o passa None/"" per disattivare).

Aumenta la qualità del momentum.

rsi_days_min (int, default 1)
Giorni minimi di RSI_Trend richiesti.

2–3 per essere più selettivo.

rsi_ob_soft (float, default 70.0)
Soglia overbought “soft”: tra rsi_ob_soft e rsi_ob_hard lo score subisce una penalità (fino a −7).

rsi_ob_hard (float, default 78.0)
Overbought “hard”: blocca l’ingresso base; resta permesso solo l’ingresso breakout (se use_breakout=True).

rsi_exit_soft (float, default 45.0)
Uscita (−1) se RSI scende sotto questa soglia in trend maturo (streak alto).

Alzala a 48–50 per uscire prima.

rsi_trend_down_exit_days (int, default 3)
Uscita (−1) se RSI_Trend == "Down" per ≥ N giorni.

Metti 2 per reagire più in fretta.

Preset pronti (puoi copiarli al volo)

Baseline (daily, bilanciato)