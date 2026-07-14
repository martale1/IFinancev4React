from scipy.stats import pearsonr, spearmanr
import matplotlib.pyplot as plt
import seaborn as sns
from TechnicalAnalyzer import TechnicalAnalyzer
import pandas as pd
import numpy as np
import pandas as pd
import numpy as np

def compute_strategy_return(
    df: pd.DataFrame,
    price_col: str = "Close",
    signal_col: str = "Trading_Signal",
    compound: bool = True,
    close_open_at_end: bool = False
):
    """
    Calcola il rendimento percentuale della strategia:
    - Entra quando trovi il PRIMO 1 (se sei flat)
    - Ignora eventuali altri 1 se sei già dentro
    - Esce quando trovi il PRIMO -1 (se sei dentro)
    - Prezzi di esecuzione: Close della barra del segnale

    Parametri:
      df: DataFrame con almeno [price_col, signal_col]
      price_col: nome colonna prezzi (default 'Close')
      signal_col: nome colonna segnali (default 'Trading_Signal')
      compound: se True usa composizione (∏(1+r_i)-1), altrimenti somma semplice (Σ r_i)
      close_open_at_end: se True e l’ultimo trade è aperto, chiude sull’ultimo prezzo

    Ritorna:
      total_return_pct (float), trades (DataFrame con entry/exit/return)
    """
    in_pos = False
    entry_idx = None
    entry_px = None
    trades = []

    signals = df[signal_col].fillna(0)
    prices  = df[price_col].astype(float)

    for idx, sig in signals.items():
        px = prices.loc[idx]

        if not in_pos:
            # entra solo al PRIMO 1
            if sig == 1:
                in_pos = True
                entry_idx = idx
                entry_px  = px
        else:
            # esci solo al PRIMO -1
            if sig == -1:
                ret = (px / entry_px) - 1.0
                trades.append({
                    "entry_idx": entry_idx,
                    "exit_idx": idx,
                    "entry_price": entry_px,
                    "exit_price": px,
                    "return_pct": ret * 100.0
                })
                in_pos = False
                entry_idx = None
                entry_px  = None
            # eventuali altri 1 vengono ignorati

    # opzionale: chiudi l’ultimo trade rimasto aperto all’ultimo prezzo disponibile
    if in_pos and close_open_at_end:
        last_idx = prices.index[-1]
        last_px  = prices.iloc[-1]
        ret = (last_px / entry_px) - 1.0
        trades.append({
            "entry_idx": entry_idx,
            "exit_idx": last_idx,
            "entry_price": entry_px,
            "exit_price": last_px,
            "return_pct": ret * 100.0
        })

    trades_df = pd.DataFrame(trades)

    if trades_df.empty:
        return 0.0, trades_df

    if compound:
        # rendimento composto: ∏(1+r_i) - 1
        total_return = 1.0
        for r in trades_df["return_pct"].values:
            total_return *= (1.0 + r/100.0)
        total_return_pct = (total_return - 1.0) * 100.0
    else:
        # somma semplice dei rendimenti percentuali
        total_return_pct = trades_df["return_pct"].sum()

    return round(total_return_pct, 4), trades_df




def backTestingRun(ticker):
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
    ta.add_category()  # crea Category BUY NOW, ETC, EntryTrigger, StopHint, Notes
    ta.generate_signal_SAR_MA(
        use_ema30=1, use_ema50=0, use_sar=1,
        column="SIG_MA_SAR"
    )

    ta.generate_signal_generic(
        long_conditions=[
            lambda d: d["Close"] > d["EMA_50"],
            lambda d: d["SAR"] < d["Close"],
            lambda d: d["MCS"] > 30,

        ],
        short_conditions=[
            lambda d: (d["Close"] < d["EMA_30"]) | (d["SAR"] > d["Close"]) | (d["MCS"] < 40) | (d["Close"] < d["Alligator_Lips"])


#            lambda d: d["SAR"] > d["Close"]

        ],
        signal_column="Trading_Signal"
    )
    return ta

mta=backTestingRun("LCFE.MI")
df=mta.dataframe


col_order = ["Close","SAR","EMA_50","MCS","Trading_Signal"]

print(df.tail(1).to_string())

print(df[col_order].tail(50).to_string())


total_ret_pct, trades = compute_strategy_return(
    df, price_col="Close", signal_col="Trading_Signal",
    compound=True, close_open_at_end=False
)

print("Rendimento totale (%) =", total_ret_pct)
print(trades.tail(30).to_string(index=False))