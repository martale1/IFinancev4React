# Action, BUY/SELL e Market Phase - condizioni operative

## Action: AVOID / WAIT / HOLD
- AVOID: `Liquidity = AVOID`
- WAIT: `Liquidity != OK` (se non AVOID)
- HOLD: fallback finale, nessun trigger BUY/SELL/ADD/REDUCE/EXIT

## Action: BUY (strict trigger)
Tutte vere:
- Phase in `{BREAKOUT, UPTREND, PULLBACK}`
- `Liquidity = OK`
- `ADX >= 20`
- `ADX_Trend = Bullish`
- `+DI > -DI`
- `0 < MACD_vs_Signal <= 100`
- `MACDH_Trend = Up`
- `RSI >= 45`
- `RSI_Trend = Up`
- `Close > EMA_30` e `Close > EMA_50`
- `SAR_Above_Price = No`
- `TECH_SCORE >= 65`

## Action: SELL (strict trigger)
Tutte vere:
- Phase in `{DOWNTREND, REVERSAL_RISK}`
- `Liquidity = OK`
- `ADX >= 20`
- `ADX_Trend = Bearish`
- `-DI > +DI`
- `MACD_vs_Signal = -1`
- `MACDH_Trend = Down`
- `RSI <= 50`
- `RSI_Trend = Down`
- `Close < EMA_30` e `Close < EMA_50`
- `SAR_Above_Price = Yes`
- `TECH_SCORE <= 35`

## Action: ADD / REDUCE / EXIT
- EXIT: se phase = `DOWNTREND`
- REVERSAL_RISK: `Close > EMA_50 -> REDUCE`, altrimenti `EXIT`
- EXIT: se struttura bullish rotta `(EMA30 > EMA50) and (Close < EMA50)`
- REDUCE: in fase bullish (`UPTREND/BREAKOUT/PULLBACK`) con `Close > EMA50` e:
  - `Stoch_K >= 80` oppure
  - `ATR_PCT > 3`
- ADD (bullish quality): `phase in {BREAKOUT, UPTREND}` AND `+DI > -DI` AND `ADX >= 25` AND `Close > EMA50`
- ADD su PULLBACK: `EMA30 > EMA50` AND `Close > EMA50` AND `+DI >= -DI` AND segnale stoch rebound

## Market Phase: BREAKOUT (strict)
Tutte vere:
- `Close > recent_high(20) * 1.003`
- `0 < MACD_vs_Signal <= 100`
- `ADX >= 25`
- `ADX slope > 0`
- `MACD_Hist` in crescita
- `Vol_Perc_vs_MA20 > 0`
- `Stoch_K < 80`
- filtro `Signal6` coerente (wakeup/uptrend family)

## Market Phase: UPTREND
- Struttura rialzista (`Close > EMA30 > EMA50`)
- `+DI > -DI`
- Trend forte (`ADX`) e SAR bullish

## Market Phase: DOWNTREND
- Struttura ribassista (`Close < EMA30 < EMA50`)
- `-DI > +DI`
- Trend forte (`ADX`) e SAR bearish

## Market Phase: PULLBACK
- Struttura ancora bullish (`EMA30 > EMA50` e `Close > EMA50`)
- Segnali di ritracciamento (RSI/Stoch/MACD/Close vs EMA30)

## Market Phase: REVERSAL_RISK
- Conflitti strutturali su trend/DI/SAR/Signal6
- Possibile inversione

## Market Phase: RANGE
- Fase laterale / fallback
- ADX debole e assenza di trend netto
