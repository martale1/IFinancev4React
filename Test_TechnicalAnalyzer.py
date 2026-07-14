from scipy.stats import pearsonr, spearmanr
import matplotlib.pyplot as plt
import seaborn as sns
from TechnicalAnalyzer import TechnicalAnalyzer
import pandas as pd
import numpy as np
import pandas as pd
import numpy as np


# --- NEW: MACD streaks ---
def add_macd_streaks(df: pd.DataFrame,
                     macd_col: str = "MACD",
                     out_pos_col: str = "MACD_Positive_Days",
                     out_neg_col: str = "MACD_Negative_Days") -> pd.DataFrame:
    if macd_col not in df.columns:
        raise ValueError(f"Colonna '{macd_col}' non trovata.")
    out = df.copy()
    s = pd.to_numeric(out[macd_col], errors="coerce")

    # Streak > 0
    pos_mask = s > 0
    pos_groups = (~pos_mask).cumsum()
    pos_streak = pos_mask.groupby(pos_groups).cumsum()
    out[out_pos_col] = pos_streak.where(pos_mask, 0).astype("int64")

    # Streak < 0 (opzionale)
    neg_mask = s < 0
    neg_groups = (~neg_mask).cumsum()
    neg_streak = neg_mask.groupby(neg_groups).cumsum()
    out[out_neg_col] = neg_streak.where(neg_mask, 0).astype("int64")
    return out
# --- END NEW ---

def add_simple_ma_sar_signals(df: pd.DataFrame,
                              col: str = "SIG_MA_SAR",
                              out_col: str = "Signal",
                              include_first: bool = False) -> pd.DataFrame:
    """
    Segnali impulsivi:
      +1 quando SIG_MA_SAR passa da <=0 a >0
      -1 quando SIG_MA_SAR passa da >0 a <=0
       0 altrimenti

    include_first=False: la prima riga non genera segnali.
    include_first=True:  la prima riga genera +1 se >0, altrimenti -1.
    """
    if col not in df.columns:
        raise ValueError(f"Colonna '{col}' non trovata nel DataFrame.")

    out = df.copy()

    # Stato booleano: True se >0, False altrimenti (NaN -> 0)
    s = pd.to_numeric(out[col], errors="coerce").fillna(0)
    state = s > 0                       # bool
    prev  = state.shift(1)              # può contenere NaN

    # Riempio i NaN prima di fare operazioni booleane
    prev_f = prev.fillna(False)

    # Transizioni (evito l'uso di ~ su float):
    entry = state & (~prev_f)           # False -> True
    exit_ = (~state) & prev_f           # True  -> False

    signal = pd.Series(0, index=out.index, dtype="int8")
    signal[entry] =  1
    signal[exit_]  = -1

    if not include_first and len(signal) > 0:
        signal.iloc[0] = 0

    # opzionale: posizione cumulativa
    # pos = signal.replace({-1:0, 1:1}).where(signal!=0, np.nan).ffill().fillna(0).astype(int)
    # out["Position"] = pos

    out[out_col] = signal
    return out


def compute_returns_from_signal(
    df: pd.DataFrame,
    price_col: str = "Close",
    signal_col: str = "Signal",
    cost_bps: float = 0.0,           # costi+slippage per lato in basis points (es. 5 = 0.05%)
    close_last_open: bool = True     # se ultimo trade resta aperto, chiudi all'ultimo prezzo
):
    """
    Aggiunge colonne con posizione ed equity e ritorna anche una tabella trades.

    Richiede:
      - df[price_col] con i prezzi (close)
      - df[signal_col] con segnali impulsivi: +1 (ENTRY), -1 (EXIT), 0 altrimenti

    Output:
      df_out: DataFrame con colonne:
        Position (0/1), BarRet, StratRetGross, StratRetNet, EquityGross, EquityNet
      trades: DataFrame con EntryDate, EntryPrice, ExitDate, ExitPrice, TradeReturnPct, TradeReturnPctNet, Bars
      summary: dict con metriche aggregate
    """
    if price_col not in df.columns or signal_col not in df.columns:
        raise ValueError(f"'{price_col}' e/o '{signal_col}' non presenti nel DataFrame.")

    out = df.copy().sort_index()
    px = pd.to_numeric(out[price_col], errors="coerce")

    # Posizione derivata dai segnali impulsivi
    # (rimani in LONG dopo un +1 finché non arriva un -1)
    pos = out[signal_col].replace({1: 1, -1: 0})
    pos = pos.where(out[signal_col] != 0, np.nan).ffill().fillna(0).astype(int)

    # Rendimento per barra (decimale, es. 0.01 = 1%)
    bar_ret = px.pct_change().fillna(0.0)

    # Rendimento strategia (gross) = ritorno solo quando in posizione
    strat_gross = bar_ret * pos

    # Costi per lato in decimale
    cost_dec = float(cost_bps) / 10_000.0

    # Applica costi su barre di entry/exit (-cost_dec ciascuna)
    strat_net = strat_gross.copy()
    entry_mask = (out[signal_col] == 1)
    exit_mask  = (out[signal_col] == -1)
    strat_net.loc[entry_mask] -= cost_dec
    strat_net.loc[exit_mask]  -= cost_dec

    # Curve equity (base 1.0)
    equity_gross = (1.0 + strat_gross).cumprod()
    equity_net   = (1.0 + strat_net).cumprod()

    out["Position"]     = pos
    out["BarRet"]       = bar_ret
    out["StratRetGross"] = strat_gross
    out["StratRetNet"]   = strat_net
    out["EquityGross"]   = equity_gross
    out["EquityNet"]     = equity_net

    # ---- Per-trade (pairing ENTRY/EXIT) ----
    entries = out.index[out[signal_col] == 1].tolist()
    exits   = out.index[out[signal_col] == -1].tolist()

    # Allinea coppie entry-exit
    ei, xi = 0, 0
    pairs = []
    while ei < len(entries) and xi < len(exits):
        e = entries[ei]; x = exits[xi]
        if x <= e:
            xi += 1  # scarta exit prima dell'entry
            continue
        pairs.append((e, x))
        ei += 1; xi += 1

    # Se rimane un entry senza exit
    open_tail = (ei < len(entries))
    if open_tail and close_last_open:
        pairs.append((entries[ei], out.index[-1]))

    # Costruisci tabella trades
    rows = []
    for e, x in pairs:
        entry_px = float(px.loc[e])
        exit_px  = float(px.loc[x])
        gross = (exit_px / entry_px - 1.0) * 100.0
        # costi: due lati se chiuso nello stesso bar set, altrimenti comunque 2 lati
        sides = 2 if (x != e) else 2
        net = gross - sides * cost_bps / 100.0
        rows.append({
            "EntryDate": e, "EntryPrice": entry_px,
            "ExitDate": x,  "ExitPrice": exit_px,
            "Bars": (out.index.get_loc(x) - out.index.get_loc(e)),
            "TradeReturnPct": gross,
            "TradeReturnPctNet": net
        })
    trades = pd.DataFrame(rows)

    # ---- Riepilogo ----
    if len(equity_net) > 0:
        total_ret_gross = (equity_gross.iloc[-1] - 1.0) * 100.0
        total_ret_net   = (equity_net.iloc[-1]   - 1.0) * 100.0
    else:
        total_ret_gross = total_ret_net = 0.0

    summary = {
        "TotalReturnPctGross": total_ret_gross,
        "TotalReturnPctNet": total_ret_net,
        "NumTrades": int(len(trades)),
        "WinRate": float((trades["TradeReturnPctNet"] > 0).mean()*100) if len(trades) else np.nan,
        "AvgTradePctNet": float(trades["TradeReturnPctNet"].mean()) if len(trades) else np.nan,
        "MedianTradePctNet": float(trades["TradeReturnPctNet"].median()) if len(trades) else np.nan,
    }

    return out, trades, summary
import pandas as pd
import numpy as np

def trade_report_from_signal(
    df: pd.DataFrame,
    price_col: str = "Close",
    signal_col: str = "Signal",
    cost_bps: float = 0.0,         # costi+slippage per lato in basis points (es. 5 = 0.05%)
    close_last_open: bool = True,  # se ultimo trade è aperto, chiudi all'ultimo prezzo disponibile
    round_digits: int = 2
) -> pd.DataFrame:
    """
    Ritorna una tabella con: EntryDate, EntryPrice, ExitDate, ExitPrice, ReturnPct, ReturnPctNet, HoldBars, HoldDays.

    Richiede:
      - df[price_col] prezzi (close)
      - df[signal_col] segnali impulsivi: 1 (ENTRY), -1 (EXIT), 0 altrimenti
    """
    if price_col not in df.columns or signal_col not in df.columns:
        raise ValueError(f"Colonne richieste non trovate: '{price_col}', '{signal_col}'")

    data = df.copy().sort_index()
    px = pd.to_numeric(data[price_col], errors="coerce")

    entries = data.index[data[signal_col] == 1].tolist()
    exits   = data.index[data[signal_col] == -1].tolist()

    # Abbina ogni ENTRY con la successiva EXIT
    pairs = []
    ei, xi = 0, 0
    while ei < len(entries) and xi < len(exits):
        e = entries[ei]; x = exits[xi]
        if x <= e:       # ignora exit "prima" dell'entry corrispondente
            xi += 1
            continue
        pairs.append((e, x))
        ei += 1; xi += 1

    # Se resta un entry senza exit
    if ei < len(entries) and close_last_open:
        pairs.append((entries[ei], data.index[-1]))

    rows = []
    for e, x in pairs:
        # salta coppie con prezzi mancanti
        if pd.isna(px.loc[e]) or pd.isna(px.loc[x]):
            continue

        entry_px = float(px.loc[e])
        exit_px  = float(px.loc[x])
        ret_pct  = (exit_px / entry_px - 1.0) * 100.0

        # costi per lato in percento
        cost_per_side_pct = cost_bps / 100.0
        sides = 2  # ingresso + uscita
        ret_pct_net = ret_pct - sides * cost_per_side_pct

        # durata
        try:
            hold_days = (pd.to_datetime(x) - pd.to_datetime(e)).days
        except Exception:
            hold_days = np.nan
        hold_bars = int(data.index.get_loc(x) - data.index.get_loc(e))

        rows.append({
            "EntryDate": e,
            "EntryPrice": entry_px,
            "ExitDate": x,
            "ExitPrice": exit_px,
            "ReturnPct": ret_pct,
            "ReturnPctNet": ret_pct_net,
            "HoldBars": hold_bars,
            "HoldDays": hold_days,
        })

    report = pd.DataFrame(rows)
    if not report.empty:
        report = report.sort_values("EntryDate").reset_index(drop=True)
        # arrotondamenti
        report["EntryPrice"]   = report["EntryPrice"].round(round_digits)
        report["ExitPrice"]    = report["ExitPrice"].round(round_digits)
        report["ReturnPct"]    = report["ReturnPct"].round(round_digits)
        report["ReturnPctNet"] = report["ReturnPctNet"].round(round_digits)

    return report

ticker="3LPP.MI"
ta = TechnicalAnalyzer(ticker, period="2y")
ta.calculate_TA_Indicators("MACD,VOL_PERC,RSI,SAR,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30,PCTV")
custom_weights = {  # versione bilanciata per principianti
    'MACD': 0.2,
    'RSI': 0.15,
    'STOCH': 0.15,
    'WILLR': 0.15,  # Nuovo peso per Williams %R
    'MA_TREND': 0.15,
    'VOLUME': 0.1,
    'SAR': 0.05,
    'PCTV': 0.05,
    'ALLIGATOR': 0.1}
ta.calculate_alligator_signal6()
ta.calculate_technical_score(weights=custom_weights)
ta.calculate_technical_score(weights=custom_weights)

ta.add_category()  # crea Category, EntryTrigger, StopHint, Notes
ta.generate_signal_SAR_MA(
    use_ema30=1, use_ema50=0, use_sar=1,
    column="SIG_MA_SAR"


)

ta.generate_simple_trend_breakout()
#ta.generate_simple_trend_breakout(
#    macdh_up_min_days=2,
#    rsi_min=50,
#    breakout_lookback=7,
#    vol_rel_min=30,
#    use_stoch=True,
#    stoch_cross=True
#)
#ta.analyze_signal6_distribution()
#print(ta.get_signal6_description('Uptrend*'))
#print(ta.dataframe.tail(20).to_string())
col_order = [
    "Category","TrendStart","Breakout","Signal_Simple","MACD_Positive_Days", "MACD_Negative_Days", "MACD_Sign_Streak","PCTV_1D","PCTV_5D","PCTV_10D", "PCTV_30D", "PCTV_180D","Close",'Vol_Perc_vs_MA5', "SIG_MA_SAR", "MCS",  "Volume", "Vol_Perc_vs_MA5", "Vol_Perc_vs_MA20", "Signal6",
    "Signal6_Trend_Days", "TECH_SCORE_S6",
    "MCS_Smoothed", "MCS_Conf", "Close",
    "RSI", "RSI_Trend", "RSI_Trend_Days",
    "MACD", "MACD_Signal", "MACD_Hist",
    "MACDH_Trend", "MACDH_Trend_Days",

    "Stoch_K", "Stoch_D", "SK_Trend", "SK_Trend_Days",
    "SAR", "SAR_Above_Price","SAR_Flip_RunDown",
    "Alligator_Jaw", "Alligator_Teeth", "Alligator_Lips",
    "EMA_50", "EMA_30",
    "Williams_R", "WILLR_Trend", "WILLR_Trend_Days",
    "WILLR_Overbought", "WILLR_Oversold", "WILLR_Neutral",
]
print(ta.dataframe[col_order].tail(50).to_string())

# 1) Crea i segnali impulsivi da SIG_MA_SAR
#df2 = add_simple_ma_sar_signals(ta.dataframe, col="SIG_MA_SAR", out_col="Signal", include_first=False)

# 2) Calcola rendimenti (con 5 bps per lato tra fee+slippage)
#df_out, trades, summary = compute_returns_from_signal(df2, price_col="Close", signal_col="Signal", cost_bps=5)

#print(summary)
#print(trades.tail())
#df_out[['Close','Signal','Position','StratRetNet','EquityNet']].tail(10)


#print(df2[col_order].tail(100).to_string())

#trade_table = trade_report_from_signal(df2, price_col="Close", signal_col="Signal", cost_bps=5)

#print(trade_table.to_string())
#print(ta.dataframe[col_order].tail(100).to_string())
'''
#ALLIGATOR GRAFICI
from ChartManager import AlligatorChartManager
chart_manager = AlligatorChartManager(ta)


# Grafico semplice
fig1 = chart_manager.plot_simple_alligator(days=90,
                                           chart_type='candlestick',
                                          show_sar=True,
                                           show_moving_averages=True)
plt.show()

# Grafico avanzato con background
fig2 = chart_manager.plot_advanced_alligator(days=100,
                                             chart_type='candlestick',
                                             show_sar=True,
                                             show_moving_averages=True)
plt.show()


#GRAFICI MCS ed ALTRO
chart_manager.plot_indicator_dashboard(
    days=180,
    chart_type='candlestick',   # <-- invece di use_candlesticks
    show_sar=True,
    show_mas=True
)
plt.show()'''






