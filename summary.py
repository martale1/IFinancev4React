# summary.py
import numpy as np
import pandas as pd

TH = dict(
    BUY_NOW_MIN=70,
    BUY_PB_MIN=60,
    WATCH_MIN=55,
    BEARISH_MAX=45,
    MCS_CONF_OK=0.55,
    MCS_CONF_WEAK=0.50,
    RSI_OB=75,
    RSI_OS=30,
    LOOKBACK_BREAKOUT=5,
    VOL_ROLL=20,
    MCS_SLOPE_LOOKBACK=2
)

BULL_STRONG = {'Uptrend', 'Uptrend*', 'wakeup2', 'wakeup2*'}
BULL_MODERATE = {'Uptrend-', 'Uptrend--', 'Uptrend---', 'wakeup1', 'wakeup2-'}
SLEEP = {'sleep1', 'sleep2'}
BEAR = {'Downtrend', 'Downtrend*', 'Downtrend_revS3Sig+', 'Downtrend_revS3Sig++', 'Downtrend_revS3Sig+++'}
REVERSAL_SET = {'Downtrend_revS3Sig+', 'Downtrend_revS3Sig++', 'Downtrend_revS3Sig+++'}

def _bool(x): return bool(x) if pd.notna(x) else False

def _trend_ok(row):
    return _bool(not row.get('SAR_Above_Price', True)) and (row.get('EMA_30', np.nan) >= row.get('EMA_50', np.nan))

def _mcs_slope_up(series, i, lookback=1):
    if i <= 0 or pd.isna(series.iloc[i]) or pd.isna(series.iloc[i-1]):
        return False
    if lookback == 1:
        return (series.iloc[i] - series.iloc[i-1]) > 0
    j = i - lookback
    if j < 0 or pd.isna(series.iloc[j]): return False
    return (series.iloc[i] - series.iloc[j]) > 0

def _rolling_avg(series, i, win):
    if i < win: return np.nan
    return series.iloc[i-win+1:i+1].mean()

def _primary_category(row):
    s6 = row.get('Signal6', None)
    score = row.get('TECH_SCORE', np.nan)
    mcs = row.get('MCS_Smoothed', np.nan)
    conf = row.get('MCS_Conf', np.nan)

    if s6 in BEAR or (pd.notna(score) and score < TH['BEARISH_MAX']):
        return 'AVOID / BEARISH'
    if s6 in REVERSAL_SET and (mcs > 0) and (conf >= TH['MCS_CONF_OK']):
        return 'REVERSAL CANDIDATE'
    if s6 in (BULL_STRONG | BULL_MODERATE):
        if (s6 in BULL_STRONG) and (score >= TH['BUY_NOW_MIN']) and (mcs > 0) and (conf >= TH['MCS_CONF_OK']):
            return 'BUY NOW'
        if (score >= TH['BUY_PB_MIN']) and (score < TH['BUY_NOW_MIN']) and (mcs >= 0):
            return 'BUY ON PULLBACK'
        if (score >= TH['WATCH_MIN']) and (score < TH['BUY_PB_MIN']) and (conf >= TH['MCS_CONF_OK']):
            return 'WATCHLIST'
        return 'HOLD / NEUTRAL'
    if s6 in SLEEP:
        return 'HOLD / NEUTRAL'
    return 'HOLD / NEUTRAL'

def _decoratev0(row, df, idx):
    notes = []
    # RSI
    rsi = row.get('RSI', np.nan)
    if pd.notna(rsi):
        if rsi > TH['RSI_OB']: notes.append('RSI overbought')
        elif rsi < TH['RSI_OS']: notes.append('RSI oversold')

    # Trend quality
    trend_ok = _trend_ok(row)
    notes.append('Trend OK' if trend_ok else 'Trend fragile')

    # Volume alert
    vol20 = np.nan
    if 'Volume' in df.columns:
        vol20 = _rolling_avg(df['Volume'], idx, TH['VOL_ROLL'])
        vol = row.get('Volume', np.nan)
        if pd.notna(vol) and pd.notna(vol20) and vol < vol20:
            notes.append('Bassa liquidità')

    # MCS slope
    mcs_s = df['MCS_Smoothed'] if 'MCS_Smoothed' in df.columns else pd.Series([np.nan]*len(df))
    slope1 = _mcs_slope_up(mcs_s, idx, 1)
    slope2 = _mcs_slope_up(mcs_s, idx, TH['MCS_SLOPE_LOOKBACK'])
    if slope1: notes.append('MCS↑')
    elif pd.notna(mcs_s.iloc[idx]) and idx > 0: notes.append('MCS↓')

    # Base category
    cat = row['Category']

    # Light adjustments
    if cat == 'BUY NOW':
        if (not slope2) and (mcs_s.iloc[idx] <= mcs_s.iloc[idx-1] if idx > 0 else False):
            cat = 'BUY ON PULLBACK'
            notes.append('Momentum in raffreddamento (downgrade)')
    if cat == 'BUY ON PULLBACK' and not trend_ok:
        cat = 'WATCHLIST'
        notes.append('Trend fragile (downgrade)')
    if cat == 'WATCHLIST' and trend_ok and slope1:
        cat = 'BUY ON PULLBACK'
        notes.append('Miglioramento momentum (upgrade)')

    # Reduce/TP check
    if row['Category'] in ('BUY NOW', 'BUY ON PULLBACK'):
        conf = row.get('MCS_Conf', np.nan)
        mcs_val = row.get('MCS_Smoothed', np.nan)
        score = row.get('TECH_SCORE', np.nan)
        if pd.notna(score) and score >= TH['BUY_NOW_MIN'] and ((pd.notna(mcs_val) and mcs_val <= 0) or (pd.notna(conf) and conf < TH['MCS_CONF_WEAK'])):
            cat = 'REDUCE / TAKE PROFIT'
            notes.append('Momentum stanco / conf bassa')

    # Entry/Stop
    if cat == 'BUY NOW':
        entry = f"Breakout > High({TH['LOOKBACK_BREAKOUT']})"; stop = "Sotto Alligator_Teeth / SAR"
    elif cat == 'BUY ON PULLBACK':
        entry = "Rebound su EMA30/Lips con close > high prev."; stop = "Sotto EMA30 / Alligator_Teeth"
    elif cat == 'WATCHLIST':
        entry = "Attendi: score ≥60 e close > EMA30"; stop = "n/a"
    elif cat == 'REDUCE / TAKE PROFIT':
        entry = "n/a"; stop = "Trailing con SAR / sotto Lips"
    elif cat == 'AVOID / BEARISH':
        entry = "Evita; attendi reversal"; stop = "n/a"
    elif cat == 'REVERSAL CANDIDATE':
        entry = "Conferme: RSI>50 e close>EMA30"; stop = "Sotto minimo recente"
    else:
        entry = "n/a"; stop = "n/a"

    return cat, entry, stop, "; ".join(notes)

def _decorate(row, df, idx):
    notes = []
    # RSI
    rsi = row.get('RSI', np.nan)
    if pd.notna(rsi):
        if rsi > TH['RSI_OB']: notes.append('RSI overbought')
        elif rsi < TH['RSI_OS']: notes.append('RSI oversold')

    # Trend quality
    trend_ok = _trend_ok(row)
    notes.append('Trend OK' if trend_ok else 'Trend fragile')

    # Volume alert
    vol20 = np.nan
    if 'Volume' in df.columns:
        vol20 = _rolling_avg(df['Volume'], idx, TH['VOL_ROLL'])
        vol = row.get('Volume', np.nan)
        if pd.notna(vol) and pd.notna(vol20) and vol < vol20:
            notes.append('Bassa liquidità')

    # MCS slope
    mcs_s = df['MCS_Smoothed'] if 'MCS_Smoothed' in df.columns else pd.Series([np.nan]*len(df))
    slope1 = _mcs_slope_up(mcs_s, idx, 1)
    slope2 = _mcs_slope_up(mcs_s, idx, TH['MCS_SLOPE_LOOKBACK'])
    if slope1: notes.append('MCS↑')
    elif pd.notna(mcs_s.iloc[idx]) and idx > 0: notes.append('MCS↓')

    # Base category
    cat = row['Category']

    # Light adjustments
    if cat == 'BUY NOW':
        if (not slope2) and (mcs_s.iloc[idx] <= mcs_s.iloc[idx-1] if idx > 0 else False):
            cat = 'BUY ON PULLBACK'
            notes.append('Momentum in raffreddamento (downgrade)')
    if cat == 'BUY ON PULLBACK' and not trend_ok:
        cat = 'WATCHLIST'
        notes.append('Trend fragile (downgrade)')
    if cat == 'WATCHLIST' and trend_ok and slope1:
        cat = 'BUY ON PULLBACK'
        notes.append('Miglioramento momentum (upgrade)')

    # Reduce/TP check
    # Reduce/TP check (usa 'cat' dopo gli aggiustamenti)
    if cat in ('BUY NOW', 'BUY ON PULLBACK'):
        conf = row.get('MCS_Conf', np.nan)
        mcs_val = row.get('MCS_Smoothed', np.nan)
        score = row.get('TECH_SCORE', np.nan)

        # Momentum in raffreddamento su 1 e 2 barre
        mcs_down = (not slope1) and (not slope2)

        # Flip di segno dell'MCS: da >0 a ≤0
        sign_flip = (
            idx > 0 and pd.notna(mcs_val) and pd.notna(mcs_s.iloc[idx-1])
            and (mcs_s.iloc[idx-1] > 0) and (mcs_val <= 0)
        )

        # Confidence bassa
        weak_conf = (pd.notna(conf) and conf < TH['MCS_CONF_WEAK'])        # < 0.50
        almost_weak_conf = (pd.notna(conf) and conf < TH['MCS_CONF_OK'])   # < 0.55

        # Trigger REDUCE:
        # - score ≥ BUY_PB_MIN (60) e momentum in raffreddamento, oppure
        # - flip di segno MCS, oppure
        # - conf bassa
        if (pd.notna(score) and score >= TH['BUY_PB_MIN'] and (mcs_down or almost_weak_conf)) \
           or sign_flip or weak_conf:
            cat = 'REDUCE / TAKE PROFIT'
            notes.append('Momentum stanco / conf bassa')



    # Entry/Stop
    if cat == 'BUY NOW':
        entry = f"Breakout > High({TH['LOOKBACK_BREAKOUT']})"; stop = "Sotto Alligator_Teeth / SAR"
    elif cat == 'BUY ON PULLBACK':
        entry = "Rebound su EMA30/Lips con close > high prev."; stop = "Sotto EMA30 / Alligator_Teeth"
    elif cat == 'WATCHLIST':
        entry = "Attendi: score ≥60 e close > EMA30"; stop = "n/a"
    elif cat == 'REDUCE / TAKE PROFIT':
        entry = "n/a"; stop = "Trailing con SAR / sotto Lips"
    elif cat == 'AVOID / BEARISH':
        entry = "Evita; attendi reversal"; stop = "n/a"
    elif cat == 'REVERSAL CANDIDATE':
        entry = "Conferme: RSI>50 e close>EMA30"; stop = "Sotto minimo recente"
    else:
        entry = "n/a"; stop = "n/a"

    return cat, entry, stop, "; ".join(notes)

def add_summary_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['Category'] = df.apply(_primary_category, axis=1)

    adj_cats, entries, stops, notes = [], [], [], []
    for i, row in df.iterrows():
        cat, entry, stop, note = _decorate(row, df, i)
        adj_cats.append(cat); entries.append(entry); stops.append(stop); notes.append(note)

    df['Category'] = pd.Categorical(adj_cats, categories=[
        'BUY NOW','BUY ON PULLBACK','WATCHLIST','REDUCE / TAKE PROFIT',
        'REVERSAL CANDIDATE','HOLD / NEUTRAL','AVOID / BEARISH'
    ], ordered=True)
    df['EntryTrigger'] = entries
    df['StopHint'] = stops
    df['Notes'] = notes
    return df

def write_summary_excel(df: pd.DataFrame, out_path: str):
    groups = {cat: df[df['Category'] == cat] for cat in df['Category'].cat.categories}
    overview = (df.groupby('Category')
                  .agg(Count=('Ticker', 'count'),
                       Avg_SCORE=('TECH_SCORE', 'mean'),
                       Avg_MCS=('MCS_Smoothed', 'mean'),
                       Avg_RSI=('RSI', 'mean'))
                  .reset_index())
    with pd.ExcelWriter(out_path, engine='openpyxl') as xw:
        overview.to_excel(xw, sheet_name='Overview', index=False)
        for name, gdf in groups.items():
            if not gdf.empty:
                gdf.sort_values(['TECH_SCORE','MCS_Smoothed'], ascending=[False, False])\
                   .to_excel(xw, sheet_name=name.replace('/', '-')[:31], index=False)
        df.to_excel(xw, sheet_name='Full_Data', index=False)


def load_and_filter_macd_vs_signal(
    market: str,
    *,
    base_dir: str = r"C:\Users\theoi\PycharmProjects\LearningPython\IFinancev4\analyses",
    macd_zero_filter: str = "any",          # "gt0" | "lt0" | "any"
    vs_signal_filter: str = "any",          # "above" | "below" | "any"
    min_days: int = 1,                      # minimo giorni consecutivi (abs(MACD_vs_Signal))
    sort_desc: bool = True,                 # True: più giorni in alto
    min_volume: int = 0,                    # 👈 VOLUME MINIMO (0 = disabilitato)
) -> "pd.DataFrame":
    """
    Legge <market>_TA_Analyses.xlsx e filtra:
      - MACD > 0 oppure MACD < 0
      - MACD vs Signal sopra/sotto
      - volume minimo (opzionale)
    Ordina per giorni condizione: abs(MACD_vs_Signal)
    """
    import os
    import numpy as np
    import pandas as pd

    # ---- path file ----
    fname = f"{market}_TA_Analyses.xlsx"
    fpath = os.path.join(base_dir, fname)
    if not os.path.exists(fpath):
        raise FileNotFoundError(f"File non trovato: {fpath}")

    # ---- load ----
    df = pd.read_excel(fpath)

    # ---- colonne richieste ----
    required = ["Ticker", "Name", "MACD", "MACD_vs_Signal"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Mancano colonne nel file {fname}: {missing}")

    # ---- cast numerico robusto ----
    df["MACD"] = pd.to_numeric(df["MACD"], errors="coerce")
    df["MACD_vs_Signal"] = pd.to_numeric(df["MACD_vs_Signal"], errors="coerce")

    # ---- filtro volume minimo (SE richiesto) ----
    if min_volume and "Volume" in df.columns:
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)
        df = df[df["Volume"] >= int(min_volume)]

    # ---- giorni condizione (magnitudo streak) ----
    df["MACD_vs_Signal_Days"] = df["MACD_vs_Signal"].abs()

    out = df.copy()

    # ---- filtro MACD > 0 / < 0 ----
    macd_zero_filter = (macd_zero_filter or "any").lower().strip()
    if macd_zero_filter == "gt0":
        out = out[out["MACD"] > 0]
    elif macd_zero_filter == "lt0":
        out = out[out["MACD"] < 0]
    elif macd_zero_filter != "any":
        raise ValueError("macd_zero_filter deve essere: 'gt0' | 'lt0' | 'any'")

    # ---- filtro MACD vs Signal ----
    vs_signal_filter = (vs_signal_filter or "any").lower().strip()
    if vs_signal_filter == "above":
        out = out[out["MACD_vs_Signal"] > 0]
    elif vs_signal_filter == "below":
        out = out[out["MACD_vs_Signal"] < 0]
    elif vs_signal_filter != "any":
        raise ValueError("vs_signal_filter deve essere: 'above' | 'below' | 'any'")

    # ---- minimo giorni ----
    if min_days and int(min_days) > 1:
        out = out[out["MACD_vs_Signal_Days"] >= int(min_days)]
    else:
        out = out[out["MACD_vs_Signal_Days"] >= 1]

    # ---- ordinamento ----
    out = out.sort_values(
        by=["MACD_vs_Signal_Days", "MACD_vs_Signal"],
        ascending=[not sort_desc, not sort_desc],
        na_position="last"
    )

    return out
