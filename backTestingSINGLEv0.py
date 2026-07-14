from ChartManagerBt import AlligatorChartManager

import matplotlib.pyplot as plt
from summary import add_summary_columns, write_summary_excel
from typing import Optional
# Import delle utility (devono essere disponibili nel modulo utils.py)
from utils import create_conditions_from_json, build_conditions
# Importa la tua classe
from TechnicalAnalyzer import TechnicalAnalyzer
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
from typing import Optional

def plot_entry_exit_simple(
    ta_or_df,
    ticker: Optional[str] = None,
    days: int = 230,
    signal_col: str = "Trading_Signal",   # 1 = long, -1 = exit, 0 = flat
    rule_col: Optional[str] = "SIG_MA_SAR",  # opzionale: >0 = bias long, <0 = bias exit
    use_candles: bool = True,
    show_rule_triggers: bool = True,
    figsize=(14, 6),
    dpi: int = 120,
):
    """
    Plot semplice per strategie SOLO LONG:
      - Long Entry (1) → triangolo verde ▲
      - Long Exit  (-1) → croce rossa X
      - Sfondo verde solo quando si è in posizione LONG
      - Nessun short, nessuno sfondo rosso
      - EMA 30 + SAR + (opz) trigger SIG_MA_SAR ↑ ↓
    """
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    # --- df & ticker ---
    if hasattr(ta_or_df, "dataframe"):
        df = ta_or_df.dataframe.copy()
        if ticker is None:
            ticker = getattr(ta_or_df, "ticker", "")
    else:
        df = ta_or_df.copy()
        ticker = ticker or ""

    if df is None or df.empty:
        raise ValueError("DataFrame vuoto.")

    if days and days > 0:
        df = df.tail(days)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    # --- Prezzo: candele se ci sono OHLC, altrimenti linea Close
    drew_candles = False
    if use_candles and all(c in df.columns for c in ["Open", "High", "Low", "Close"]):
        try:
            from mplfinance.original_flavor import candlestick_ohlc
            ohlc = df[["Open", "High", "Low", "Close"]].copy()
            ohlc["DateNum"] = mdates.date2num(pd.to_datetime(ohlc.index).to_pydatetime())
            ohlc = ohlc[["DateNum", "Open", "High", "Low", "Close"]]
            candlestick_ohlc(ax, ohlc.values, width=0.6, colorup="g", colordown="r", alpha=0.9)
            xs_num = ohlc["DateNum"].to_numpy()
            drew_candles = True
        except Exception:
            drew_candles = False

    if not drew_candles:
        ax.plot(df.index, df["Close"], color="black", lw=1.8, label="Close")
        xs_num = mdates.date2num(pd.to_datetime(df.index).to_pydatetime())

    # --- EMA 30
    if "EMA_30" in df.columns:
        ax.plot(df.index, df["EMA_30"], lw=1.8, ls="--", label="EMA 30")

    # --- SAR
    if "SAR" in df.columns:
        above = df["SAR"] > df["Close"]
        below = ~above
        ax.scatter(df.index[below], df["SAR"][below], s=18, label="SAR (Buy)", zorder=4)
        ax.scatter(df.index[above], df["SAR"][above], s=18, label="SAR (Sell)", zorder=4)

    # --- segnali ingresso/uscita (SOLO LONG)
    sig = df[signal_col].fillna(0)

    entry_long = (sig == 1) & (sig.shift(1) != 1)     # ingresso
    exit_long  = (sig == -1) & (sig.shift(1) == 1)    # uscita da long

    # --- Sfondo verde solo durante i LONG
    blocks = sig.ne(sig.shift()).cumsum()
    for _, block in df.groupby(blocks):
        mode = int(block[signal_col].iloc[0])
        if mode == 1:  # solo long ha sfondo
            left = xs_num[df.index.get_loc(block.index[0])]
            right = xs_num[df.index.get_loc(block.index[-1])]
            ax.axvspan(left, right, color="green", alpha=0.12, lw=0)

    # --- Marker ingresso/uscita
    ax.scatter(df.index[entry_long], df["Close"][entry_long],
               marker="^", s=160, edgecolor="black", color="lime", zorder=6, label="Long Entry")

    ax.scatter(df.index[exit_long], df["Close"][exit_long],
               marker="X", s=170, edgecolor="black", color="red", zorder=6, label="Long Exit")

    # --- Trigger del rule score (opzionali)
    if show_rule_triggers and (rule_col is not None) and (rule_col in df.columns):
        rule = df[rule_col]
        if not rule.isna().all():
            cross_up = (rule.shift(1) <= 0) & (rule > 0)
            cross_dn = (rule.shift(1) >= 0) & (rule < 0)
            ax.scatter(df.index[cross_up], df["Close"][cross_up],
                       marker="o", s=70, zorder=6, label=f"{rule_col} ↑")
            ax.scatter(df.index[cross_dn], df["Close"][cross_dn],
                       marker="o", s=70, zorder=6, label=f"{rule_col} ↓")

    # --- layout
    ax.set_title(f"{ticker or ''} — Entry/Exit view (last {len(df)} bars)")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.30)
    ax.legend(loc="upper left", ncol=2, frameon=True, framealpha=0.9)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    plt.tight_layout()
    return fig, ax



def calculateTAIndicators(ta):
    # Calcola gli indicatori necessari (puoi aggiungerne/toglierne a piacere)
    ta.calculate_TA_Indicators("ADX,ATR,MACD,VOL_PERC,RSI,SAR,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30,PCTV")
    ta.calculate_alligator_signal6()
    return ta


    # --- Scoring personalizzato ---
def calculateScoring(ta):

    custom_weights = {
        'MACD': 0.18,
        'RSI': 0.12,
        'STOCH': 0.10,
        'MA_TREND': 0.12,
        'VOLUME': 0.08,
        'SAR': 0.06,
        'PCTV': 0.06,
        'ALLIGATOR': 0.08,
        'Signal6': 0.12,
        'ADX': 0.12,
        'ATR': 0.06,

    }
    ta.calculate_technical_score(weights=custom_weights)
    return ta
def print_chart(
    days: int = 200,
    entry_col: str = "Entry_Signal",
    exit_col: str = "Exit_Signal",
    fallback_from_trading_signal: bool = True,
    trading_col: str = "Trading_Signal",
    execution_offset_bars: int = 0,   # metti 1 se il backtest esegue alla barra successiva
    marker_size_entry: int = 160,
    marker_size_exit: int = 170,
):
    # 1) prendi la stessa finestra che userà il manager
    df_full = ta.dataframe
    if df_full is None or df_full.empty:
        raise ValueError("DataFrame del TA vuoto.")

    df = df_full.tail(days).copy()

    # normalizza indice datetime → naive e poi date number (coerente con candlestick_ohlc)
    idx_dt = pd.to_datetime(df.index)
    if getattr(idx_dt, 'tz', None) is not None:
        idx_dt = idx_dt.tz_localize(None)
    x_num = mdates.date2num(idx_dt.to_pydatetime())

    # 2) ricava entry/exit dalla fonte di verità
    if {entry_col, exit_col}.issubset(df.columns):
        entry_mask = df[entry_col] == 1
        exit_mask  = df[exit_col]  == 1
    elif fallback_from_trading_signal and (trading_col in df.columns):
        sig = df[trading_col].fillna(0)
        entry_mask = (sig == 1) & (sig.shift(1) != 1)
        exit_mask  = (sig == -1) & (sig.shift(1) == 1)
    else:
        raise KeyError(
            f"Mancano '{entry_col}'/'{exit_col}' e non posso fare fallback su '{trading_col}'."
        )

    # 3) offset visivo se esecuzione next-bar
    if execution_offset_bars != 0:
        # shiftiamo i mask in modo safe
        entry_mask = entry_mask.shift(execution_offset_bars, fill_value=False)
        exit_mask  = exit_mask.shift(execution_offset_bars,  fill_value=False)

    # 4) disegna il grafico base SENZA entry/exit interni
    cm = AlligatorChartManager(technical_analyzer=ta)
    cm.plot_simple_alligator(
        days=days,
        chart_type='candlestick',
        show_entries_exits=False,   # li aggiungiamo noi
        show_sar=True,
        show_moving_averages=True,
        show_signals=False
    )

    ax = plt.gca()

    # 5) overlay marker coerenti (x come date number; y come Close)
    #    (ripuliamo eventuali NaN)
    close = df["Close"].astype(float)
    em = entry_mask.fillna(False).to_numpy()
    xm = exit_mask.fillna(False).to_numpy()

    ax.scatter(x_num[em], close[em],
               marker="^", s=marker_size_entry, edgecolor="black",
               color="lime", zorder=6, label="Long Entry")

    ax.scatter(x_num[xm], close[xm],
               marker="X", s=marker_size_exit, edgecolor="black",
               color="red", zorder=6, label="Long Exit")

    # 6) sistema limiti asse X sulla nostra finestra (evita “1970”)
    ax.set_xlim(x_num.min(), x_num.max())

    # 7) dedup della legenda
    handles, labels = ax.get_legend_handles_labels()
    seen, h2, l2 = set(), [], []
    for h, l in zip(handles, labels):
        if l not in seen:
            seen.add(l); h2.append(h); l2.append(l)
    ax.legend(h2, l2, loc="upper left", ncol=2, frameon=True, framealpha=0.9)

    plt.tight_layout()
    plt.show()

def print_chartv0(ndays=200):
    cm = AlligatorChartManager(technical_analyzer=ta)
    cm.plot_simple_alligator(
        days=ndays,
        chart_type='candlestick',
        show_entries_exits=True,
        show_sar=True,  # <— nasconde i puntini SAR
        show_moving_averages=True,
        show_signals=False  # <— nasconde Uptrend*/Downtrend* ecc.
    )
    # oppure
    # cm.plot_ta_dashboard(days=200, chart_type='line', show_entries_exits=True)
    plt.show()






json_long=[{"col": "Close", "op": ">", "col2": "EMA_30"},
            {"col": "RSI",   "op": ">", "val": 55},]
json_short = [{"col": "RSI",   "op": "<", "val": 45}]


json_long=[{"col": "SIG_MA_SAR", "op": ">", "val": 0},
            {"col": "ADX", "op": ">=", "val": 25},]
json_short = [
              {"col": "Close",   "op": "<",  "col2": "Alligator_Lips"},
              {"col": "Close", "op": "<", "col2": "EMA_30"}]


json_long=[ {"col": "MACDH_Trend", "op": "==", "val": "Up"},
            {"col": "MACDH_Trend_Days", "op": ">=", "val": 3},
            #{"col": "RSI", "op": ">=", "val": 40},
            ]
json_long=[{"col": "Stoch_K","op": "<=","val": 30},
      {"col": "Stoch_K","op": ">","col2": "Stoch_D"},
      {"col": "SK_Trend","op": "==","val": "Up"},
      {"col": "SK_Trend_Days","op": ">=","val": 3}
           ]
json_short = [
    {"col": "Close", "op": "<", "col2": "Stop_Level"},]


##### ---- BEGIN ------ #####
TICKER = "3LMI.mi"
PERIOD = "2y"          # es. "6mo", "2y", "max"
ta=calculateTAIndicators(TechnicalAnalyzer(TICKER, period=PERIOD))
ta.add_prev_true_range()  # aggiunge colonna stop level
ta=calculateScoring(ta)
ta.generate_signal_SAR_MA(use_ema30=1, use_ema50=0, use_sar=1,column="SIG_MA_SAR")

#ta.start_Signals_Generation(json_long_strategy=json_long,json_short_strategy=json_short,signal_name="Trading_Signal")
#stats=ta.backTestingVBT(plotChart=False)
#print(stats)


stats=ta.backTestingVBTLogic(plotChart=False,json_long=json_long, json_short=json_short,
                          long_logic="AND", short_logic="AND")
cols = ["Trading_Signal","Entry_Signal","Exit_Signal","MACDH_Trend","SIG_MA_SAR","Close","Alligator_Lips", "SAR","SAR_Above_Price","EMA_30"]
cols = ["Trading_Signal","Entry_Signal","Exit_Signal","Long_Days","Short_Days","Close","MACDH_Trend","MACDH_Trend_Days","MACD_Hist","Stoch_K","Stoch_D","SK_Trend","SK_Trend_Days","SIG_MA_SAR", "SAR","SAR_Above_Price"]
print(stats)
print("basic VBTLogic")
print(ta.dataframe.tail(5).to_string())
print(ta.dataframe[cols].tail(30).to_string())
print(stats["Total Return [%]"])
print_chartv0(ndays=100)
