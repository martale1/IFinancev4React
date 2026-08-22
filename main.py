
#Note (04-01-26)
# File main.py modificato poiche` calcola i layer, inoltre la funzione si trova in technical analyzer
# Creato altro file messaging_signals per inviare i segnali
# Update server on Jan 6th 2026

from filehandling import fileHandling
from TechnicalAnalyzer import TechnicalAnalyzer
from summary import add_summary_columns, write_summary_excel
from messaging import messaging
from AlertEngine import AlertEngine

import pandas as pd
import os
from pathlib import Path
from typing import List, Optional
from zoneinfo import ZoneInfo  # Python 3.9+
import yaml
# opzionale: definisci la tz del provider SE la conosci (es. "UTC")
pd.set_option('future.no_silent_downcasting', True)
PROVIDER_TZ = None  # metti "UTC" se i tuoi timestamp sono naive ma in UTC
# --- COSTANTI GLOBALI ---
# --- COSTANTI GLOBALI ---

PROJECT_ROOT = Path(__file__).resolve().parent
_analyses_dir = Path(os.getenv("ANALYSES_DIR", "analyses")).expanduser()
if not _analyses_dir.is_absolute():
    _analyses_dir = PROJECT_ROOT / _analyses_dir
OUTPUT_FOLDER = _analyses_dir.resolve()
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FILENAME = "TA_Analyses.xlsx"



def _has_enabled_gui_rules(rules_path: Path) -> bool:
    if not rules_path.exists():
        return False
    try:
        data = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        print(f"[ALERTS] Unable to parse rules file {rules_path.name}: {exc}")
        return False

    rules = data.get("rules", []) or []
    return any(bool(r.get("enabled", True)) for r in rules)


def run_gui_alerts(
    analyses_dir: str,
    telegram_channel: int = 5,
    markets: Optional[List[str]] = None,
    require_enabled_rules: bool = True,
):
    """
    Run AlertEngine using the same rule files managed by React GUI.
    - reads alert_rules_<MARKET>.yaml in analyses_dir
    - runs only requested markets
    - optionally skips markets without enabled rules
    """
    p = Path(analyses_dir)
    if not p.exists():
        print(f"[ALERTS] analyses_dir not found: {p}")
        return {}

    target_markets = markets or ["MIB30", "Preferite", "ETF", "ETC", "DAX"]
    target_markets = [str(m).strip() for m in target_markets if str(m).strip()]

    selected_markets = []
    for market in target_markets:
        rules_path = p / f"alert_rules_{market}.yaml"
        xlsx_path = p / f"{market}_TA_Analyses.xlsx"

        if not rules_path.exists():
            print(f"[ALERTS] Skip {market}: rules file not found ({rules_path.name})")
            continue
        if require_enabled_rules and not _has_enabled_gui_rules(rules_path):
            print(f"[ALERTS] Skip {market}: no enabled rules in {rules_path.name}")
            continue
        if not xlsx_path.exists():
            print(f"[ALERTS] Skip {market}: excel file not found ({xlsx_path.name})")
            continue

        selected_markets.append(market)

    if not selected_markets:
        print("[ALERTS] No eligible GUI alert markets to run.")
        return {}

    print(f"[ALERTS] analyses_dir: {p}")
    print(f"[ALERTS] Running GUI alerts for markets: {selected_markets}")
    engine = AlertEngine(
        analyses_dir=str(p),
        markets=selected_markets,
        telegram_channel=int(telegram_channel),
    )
    return engine.run()


def v4_legenda():
    TRADING_STATE_V4_V1_DOC = """
    add_trading_statev4_v1() — Outputs & Rules (v4_v1)

    CREATED COLUMNS (kept):
    - Market_Phase: BREAKOUT / UPTREND / PULLBACK / RANGE / DOWNTREND / REVERSAL_RISK
    - Action: WAIT / AVOID / BUY / SELL / ADD / REDUCE / EXIT / HOLD
    - Action_Reason: short explanation string
    - Layer3_Warning: OK or comma-separated warnings

    TEMP COLUMNS (dropped at end):
    - __recent_high, __adx_slope, __macd_hist_rising, __vol_vs_ma20

    PARAMS (this run):
    - macd_buy_max_days=100
    - adx_min=20
    - rsi_buy_min=45
    - rsi_sell_max=50
    - tech_score_buy_min=65
    - tech_score_sell_max=35
    (other thresholds default: breakout_lookback=20, buffer=0.3%, breakout_adx_min=25,
     require_adx_slope_pos=True, require_macd_hist_rising=True, vol_vs_ma20>0,
     stoch_overbought=80, stoch_oversold=20, atr_high_vol_threshold=3,
     fresh_signal_max_days=2, mature_momentum_min_days=5, action_add_requires_adx=25)

    MARKET_PHASE:
    1) BREAKOUT (STRICT) if ALL:
       - Close > recent_high(lookback=20, shift=1) * 1.003
       - fresh momentum: 0 < MACD_vs_Signal <= 100
       - ADX >= 25 and ADX slope > 0
       - MACD_Hist rising (diff > 0)
       - Vol_Perc_vs_MA20 > 0
       - Stoch_K < 80 (if available)
       - Signal6 bullish (if present): contains 'wakeup' or equals uptrend/uptrend*
       - not in structural downtrend (Close<EMA30 and EMA30<EMA50)

    2) REVERSAL_RISK if any:
       - trend_up and MINUS_DI>PLUS_DI, or trend_down and PLUS_DI>MINUS_DI
       - trend_up and Close<EMA50, or trend_down and Close>EMA50
       - Signal6 contains 'rev' or 'reversal'

    3) UPTREND if:
       - Close>EMA30>EMA50 and PLUS_DI>MINUS_DI and (ADX>=25 or MACDH_Trend='Up')
       - SAR_Above_Price == False

    4) DOWNTREND if:
       - Close<EMA30<EMA50 and MINUS_DI>PLUS_DI and (ADX>=25 or MACDH_Trend='Down')
       - SAR_Above_Price == True

    5) PULLBACK if bullish structure intact (EMA30>EMA50 and Close>EMA50) AND >=2 votes:
       - RSI<50 or RSI_Trend='Down'
       - Stoch (K<D) or (K<40) if available
       - MACDH_Trend='Down'
       - Close<EMA30

    6) RANGE if:
       - ADX<20 and 45<=RSI<=55 and not trend_up and not trend_down
    Fallback: RANGE

    ACTION (liquidity-gated):
    - Liquidity='AVOID' -> AVOID
    - Liquidity!='OK'   -> WAIT

    STRICT SELL (phase in DOWNTREND or REVERSAL_RISK) if ALL:
    - ADX>=20, ADX_Trend='Bearish', MINUS_DI>PLUS_DI
    - MACD_vs_Signal == -1, MACDH_Trend='Down'
    - RSI<=50, RSI_Trend='Down'
    - Close<EMA30 and Close<EMA50
    - SAR_Above_Price==True
    - TECH_SCORE<=35

    STRICT BUY (phase in BREAKOUT/UPTREND/PULLBACK) if ALL:
    - ADX>=20, ADX_Trend='Bullish', PLUS_DI>MINUS_DI
    - 0<MACD_vs_Signal<=100, MACDH_Trend='Up'
    - RSI>=45, RSI_Trend='Up'
    - Close>EMA30 and Close>EMA50
    - SAR_Above_Price==False
    - TECH_SCORE>=65

    OTHER ACTIONS:
    - Phase=DOWNTREND -> EXIT
    - Phase=REVERSAL_RISK -> REDUCE if Close>EMA50 else EXIT
    - Bull structure break (EMA30>EMA50 and Close<EMA50) -> EXIT
    - REDUCE in bullish phases if (Stoch_K>=80) or (ATR_PCT>3)
    - ADD if (phase in BREAKOUT/UPTREND) and PLUS_DI>MINUS_DI and ADX>=25 and Close>EMA50
    - ADD on PULLBACK if (Close>EMA50) and PLUS_DI>=MINUS_DI and (K<=20 or (K>D and K<40))
    - else HOLD

    LAYER3_WARNING:
    - High Volatility if ATR_PCT>3
    - Fresh Signal if MACDH_Trend_Days<=2
    - Mature Momentum if RSI_Trend_Days>5
    - Stoch: Oversold(K<20), Overbought(K>80), Rebound(K<20 and K>D), Reversal(K>80 and K<D)
    """.strip()
    print(TRADING_STATE_V4_V1_DOC)


def strip_timezones_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rende tutte le datetime timezone-naive (compatibili con Excel).
    Gestisce sia colonne datetime che colonne object con Timestamp tz-aware.
    """
    df = df.copy()
    for col in df.columns:
        # Colonne datetime (anche con tz)
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            try:
                df[col] = df[col].dt.tz_localize(None)
            except Exception:
                # in rari casi la serie è già naive oppure non localizzabile
                pass
        # Colonne object che possono contenere Timestamp tz-aware
        elif df[col].dtype == object:
            def _to_naive(v):
                if isinstance(v, pd.Timestamp) and v.tzinfo is not None:
                    try:
                        return v.tz_localize(None)
                    except Exception:
                        try:
                            # fallback estremo: converti a stringa ISO senza tz
                            return v.tz_convert(None).to_pydatetime().replace(tzinfo=None)
                        except Exception:
                            return v
                return v
            df[col] = df[col].map(_to_naive)
    return df

def ordina_df_finale(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ordina il DataFrame in base a Signal6 seguendo un ordine personalizzato
    e dentro ogni gruppo ordina per Signal6_Trend_Days (discendente).
    """

    # ordine personalizzato principale
    order = [
        'Uptrend', 'Uptrend*', 'Uptrend-', 'Uptrend--', 'Uptrend---',
        'wakeup2', 'wakeup2*'
    ]

    # aggiungo tutti gli altri segnali che non sono nell'ordine predefinito
    all_signals = df['Signal6'].dropna().unique().tolist()
    remaining = [s for s in all_signals if s not in order]
    full_order = order + remaining

    # trasformo la colonna Signal6 in categoria ordinata
    df['Signal6'] = pd.Categorical(
        df['Signal6'],
        categories=full_order,
        ordered=True
    )

    # ordino: prima Signal6, poi giorni di trend discendente
    df_sorted = df.sort_values(
        by=['Signal6', 'Signal6_Trend_Days'],
        ascending=[True, False]
    ).reset_index(drop=True)

    return df_sorted





def runTA_indicators(market='ETC', numItems=0, generateSignal=False, generateScoring=False,
                     generateCategory=False, liq_keep=('OK','LOW','AVOID')):
    """
    Esegue l'analisi tecnica sui ticker di un mercato specifico.

    Args:
        market (str): Mercato da analizzare ('ETC', 'MIB30', 'ETF').
        numItems (int): Numero massimo di ticker da analizzare. Se 0 → tutti.
        generateSignal (bool): Se True genera i segnali.
        generateScoring (bool): Se True calcola lo scoring con pesi custom.

    Returns:
        pd.DataFrame: DataFrame con l'ultima riga di analisi per ciascun ticker.
    """
    fh = fileHandling()  # Gestore file e tickers

    # --- Selezione dataset in base al mercato ---
    mercati = {
        "ETC": (fh.ETCTickers, fh.ETCNames, getattr(fh, "ETCDf", None)),
        "MIB30": (fh.MIB30Tickers, fh.MIB30Names, None),
        "ETF": (fh.ETFTickers, fh.ETFNames, None),
        "Preferite": (fh.PreferiteTickers, fh.PreferiteNames, None),
        "US_ETF":(fh.US_ETFTickers,fh.US_ETFNames,None),
        "US_Others": (fh.US_OthersTickers, fh.US_OthersNames, None),
        "DAX": (fh.DAXTickers, fh.DAXNames, None)

    }
    if market not in mercati:
        raise ValueError(f"Mercato '{market}' non supportato. Usa: {list(mercati.keys())}")

    Df_Tickers, Df_names, _ = mercati[market]

    dati_ultime_righe = []
    scartati = 0

    # --- Loop su tickers ---
    for idx, (ticker, name) in enumerate(zip(Df_Tickers, Df_names)):
        if numItems and idx >= numItems:
            break

        print(f"[{idx}] Analizzo Ticker: {ticker}, Nome: {name}")

        # Normalizza ticker
        ticker = ticker.replace(" ", "")

        # Inizializza TechnicalAnalyzer

        analyzer = TechnicalAnalyzer(ticker, period="1y")

        if analyzer.dataframe.empty:
            print(f"Ticker {ticker} scartato (no dati)")
            scartati += 1
            continue

        # --- Calcolo indicatori principali ---
        analyzer.calculate_TA_Indicators(
            "ADX,ATR,MACD,VOL_PERC,RSI,SAR,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30,PCTV"
        )
        # --- Genera segnali ---
        if generateSignal:
            #print("-- GENERO SEGNALE SU SAR ed EMA30 --")
            #analyzer.generate_signals()
            #analyzer.generate_ma_sar_signal(
            #    use_ema30=1, use_ema50=0, use_sar=1,
            #    min_days=2,
            #    signal_column="SIG_MA_SAR",
            #    first_only=False
            #)
            #analyzer.generate_MA_SAR_signal(
            #    use_ema30=1, use_ema50=0, use_sar=1,
            #    days=1,
            #    mode="exact",
            #    signal_column="SIG_MA_SAR"
            #)
            analyzer.generate_signal_SAR_MA(
                use_ema30=1, use_ema50=0, use_sar=1,
                column="SIG_MA_SAR"
            )

            analyzer.calculate_alligator_signal6()
            analyzer.generate_stoch_reversal_signals(
                signal_name="sk_trad_signal",
                entry_col="sk_Entry_Signal",
                exit_col="sk_Exit_Signal",
                prefer_short_on_conflict=True,
                execute_next_bar=False  # metti True se il fill è alla barra successiva
            )

        # --- Scoring personalizzato ---
        if generateScoring:
            #print("-- GENERO SCORING --")

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

            analyzer.calculate_technical_score(weights=custom_weights)


        # --- Ultima riga del dataframe ---
        #ultima_riga = analyzer.dataframe.iloc[-1].to_dict()
        #ultima_riga = {"Ticker": ticker, "Name": name, **ultima_riga}
        #dati_ultime_righe.append(ultima_riga)
        # --- Ultima riga + DATA (presa dall'indice) ---
        # --- Ultima riga + DATA (presa dall'indice) ---
        # --- Calcolo Trading Layers (Layer1, Layer2, Trading_State) ---
        #analyzer.add_trading_layers_state_v3(
        #    macd_buy_max_days=100,
        #    adx_min=20,
        #    rsi_buy_min=45,
        #    rsi_sell_max=50,
        #    tech_score_buy_min=65,
        #    tech_score_sell_max=35,
        #)

        analyzer.add_trading_statev4_v1(
            macd_buy_max_days=100,
            adx_min=20,
            rsi_buy_min=45,
            rsi_sell_max=50,
            tech_score_buy_min=65,
        )

        # --- Calcolo dei Pattern Sperimentali (Multi-Pattern Lab) ---
        df_tmp = analyzer.dataframe.copy()
        if len(df_tmp) >= 15:
            # Assicuriamoci che tutti gli oscillatori necessari siano presenti
            required_cols = ['Williams_R', 'Stoch_K', 'Stoch_D', 'MACD', 'MACD_Signal', 'MACD_Hist']
            for col in required_cols:
                if col not in df_tmp.columns:
                    df_tmp[col] = 0.0

            # Sk vs Sd: positivo = K sopra D (crossover rialzista), come MACD_vs_Signal
            df_tmp['Stoch_KvsD'] = df_tmp['Stoch_K'] - df_tmp['Stoch_D']

            # DI+ vs DI-: positivo = DI+ sopra DI- (trend rialzista confermato da ADX)
            if 'PLUS_DI' in df_tmp.columns and 'MINUS_DI' in df_tmp.columns:
                df_tmp['DI_diff'] = df_tmp['PLUS_DI'] - df_tmp['MINUS_DI']

            w = df_tmp['Williams_R']
            w_shift1 = w.shift(1)
            w_shift2 = w.shift(2)
            
            k = df_tmp['Stoch_K']
            d = df_tmp['Stoch_D']
            k_shift1 = k.shift(1)
            d_shift1 = d.shift(1)
            
            macd = df_tmp['MACD']
            signal = df_tmp['MACD_Signal']
            macd_shift1 = macd.shift(1)
            signal_shift1 = signal.shift(1)
            hist = df_tmp['MACD_Hist']
            hist_shift1 = hist.shift(1)
            
            # S2 Pattern ottimizzato (cattura le ripartenze dai minimi con stocastico basso < 35)
            stoch_bullish = (k > d) & (k > 20)
            williams_bullish = (w > -80) & (w > w_shift1)
            stoch_trigger = ((k > 20) & (k_shift1 <= 20)) | ((k > d) & (k_shift1 <= d_shift1))
            williams_trigger = (w > -80) & (w_shift1 <= -80)
            stoch_low = k_shift1 < 35
            s2_active = stoch_bullish & williams_bullish & (stoch_trigger | williams_trigger) & stoch_low
            
            # S3 Pattern
            macd_cross = (macd > signal) & (macd_shift1 <= signal_shift1)
            macd_rose = macd > macd_shift1
            hist_ok = (hist > 0) & (hist > hist_shift1)
            s3_active = macd_cross & macd_rose & hist_ok

            # S4 Pattern – EMA Momentum Confermato con Volume
            import talib
            close_vals_s4 = df_tmp['Close'].values.flatten().astype(float)
            ema9_vals  = talib.EMA(close_vals_s4, timeperiod=9)
            ema21_vals = talib.EMA(close_vals_s4, timeperiod=21)
            df_tmp['EMA_9']  = ema9_vals
            df_tmp['EMA_21'] = ema21_vals

            # Volume MA20
            vol_vals = df_tmp['Volume'].values.flatten().astype(float)
            df_tmp['Volume_MA20'] = talib.SMA(vol_vals, timeperiod=20)

            rsi_series   = df_tmp['RSI'] if 'RSI' in df_tmp.columns else pd.Series(50.0, index=df_tmp.index)
            rsi_shift1   = rsi_series.shift(1)

            s4_ema       = df_tmp['EMA_9'] > df_tmp['EMA_21']                              # EMA9 > EMA21
            s4_rsi       = (rsi_series >= 55) & (rsi_series <= 70) & (rsi_series > rsi_shift1)  # RSI 55-70 e crescente
            s4_macd      = macd > signal                                                   # MACD > Signal
            s4_volume    = df_tmp['Volume'] > (df_tmp['Volume_MA20'] * 1.5)               # Volume > media×1.5
            s4_active    = s4_ema & s4_rsi & s4_macd & s4_volume

            # S5 Pattern – RSI Oversold con evento di incrocio stocastico rialzista
            rsi_s5    = df_tmp['RSI']     if 'RSI'     in df_tmp.columns else pd.Series(50.0, index=df_tmp.index)
            s5_active = (rsi_s5 < 30) & (k > d) & (k_shift1 <= d_shift1)

            # S6 Pattern – Golden Cross: evento di incrocio EMA30 sopra EMA50 con ADX forte
            ema30_s6  = df_tmp['EMA_30'] if 'EMA_30' in df_tmp.columns else pd.Series(0.0, index=df_tmp.index)
            ema50_s6  = df_tmp['EMA_50'] if 'EMA_50' in df_tmp.columns else pd.Series(0.0, index=df_tmp.index)
            adx_s6    = df_tmp['ADX']    if 'ADX'    in df_tmp.columns else pd.Series(0.0, index=df_tmp.index)
            s6_active = (
                (ema30_s6 > ema50_s6)
                & (ema30_s6.shift(1) <= ema50_s6.shift(1))
                & (adx_s6 > 25)
            )

            # SMA200 serve sia ai filtri sia al livello S7 Strong.
            close_vals = df_tmp['Close'].values.flatten().astype(float)
            df_tmp['SMA200'] = talib.SMA(close_vals, timeperiod=200)
            df_tmp['SMA200_Filter_Ok'] = (df_tmp['Close'] > df_tmp['SMA200']).astype(int)

            # S7 a tre livelli: Early, Confirmed e Strong.
            sar_s7 = df_tmp['SAR'] if 'SAR' in df_tmp.columns else pd.Series(0.0, index=df_tmp.index)
            signal6_s7 = df_tmp['Signal6'].astype(str) if 'Signal6' in df_tmp.columns else pd.Series('', index=df_tmp.index)
            plus_di_s7 = df_tmp['PLUS_DI'] if 'PLUS_DI' in df_tmp.columns else pd.Series(0.0, index=df_tmp.index)
            minus_di_s7 = df_tmp['MINUS_DI'] if 'MINUS_DI' in df_tmp.columns else pd.Series(0.0, index=df_tmp.index)
            vol_ma20_s7 = df_tmp['Volume_MA20'] if 'Volume_MA20' in df_tmp.columns else pd.Series(np.nan, index=df_tmp.index)

            s7_early_state = (
                (df_tmp['Close'] > sar_s7)
                & signal6_s7.isin(['Uptrend', 'Uptrend-'])
                & (plus_di_s7 > minus_di_s7)
            )
            s7_confirmed_state = (
                s7_early_state
                & signal6_s7.eq('Uptrend')
                & (ema30_s6 > ema50_s6)
                & (adx_s6 >= 20)
            )
            s7_strong_state = (
                s7_confirmed_state
                & (adx_s6 >= 25)
                & (df_tmp['Close'] > df_tmp['SMA200'])
                & (df_tmp['Volume'] >= vol_ma20_s7)
            )
            s7_early = s7_early_state & ~s7_early_state.shift(1, fill_value=False)
            s7_confirmed = s7_confirmed_state & ~s7_confirmed_state.shift(1, fill_value=False)
            s7_strong = s7_strong_state & ~s7_strong_state.shift(1, fill_value=False)
            s7_active = s7_early  # alias storico S7

            # S8 Pattern – Volume Breakout (candela rialzista + volume > MA20 × 1.5)
            open_s8     = df_tmp['Open']        if 'Open'        in df_tmp.columns else df_tmp['Close']
            vol_ma20_s8 = df_tmp['Volume_MA20'] if 'Volume_MA20' in df_tmp.columns else pd.Series(1.0, index=df_tmp.index)
            s8_active   = (df_tmp['Close'] > open_s8) & (df_tmp['Volume'] > (vol_ma20_s8 * 1.5))
            
            def _days_since(s: pd.Series) -> int:
                true_indices = s[s].index
                if len(true_indices) == 0:
                    return 999
                all_indices = s.index.tolist()
                pos = all_indices.index(true_indices[-1])
                return len(all_indices) - 1 - pos

            df_tmp['Pattern_S2_Days_Ago'] = _days_since(s2_active)
            df_tmp['Pattern_S3_Days_Ago'] = _days_since(s3_active)
            df_tmp['Pattern_Combined_Days_Ago'] = _days_since(s2_active & s3_active)
            df_tmp['Pattern_S4_Days_Ago'] = _days_since(s4_active)
            df_tmp['Pattern_S5_Days_Ago'] = _days_since(s5_active)
            df_tmp['Pattern_S6_Days_Ago'] = _days_since(s6_active)
            df_tmp['Pattern_S7_Days_Ago'] = _days_since(s7_active)
            df_tmp['Pattern_S7_EARLY_Days_Ago'] = _days_since(s7_early)
            df_tmp['Pattern_S7_CONFIRMED_Days_Ago'] = _days_since(s7_confirmed)
            df_tmp['Pattern_S7_STRONG_Days_Ago'] = _days_since(s7_strong)
            df_tmp['Pattern_S8_Days_Ago'] = _days_since(s8_active)

            df_tmp['Pattern_S2_Match'] = s2_active.astype(int)
            df_tmp['Pattern_S3_Match'] = s3_active.astype(int)
            df_tmp['Pattern_Combined_Match'] = (s2_active & s3_active).astype(int)
            df_tmp['Pattern_S4_Match'] = s4_active.astype(int)
            df_tmp['Pattern_S5_Match'] = s5_active.astype(int)
            df_tmp['Pattern_S6_Match'] = s6_active.astype(int)
            df_tmp['Pattern_S7_Match'] = s7_active.astype(int)
            df_tmp['Pattern_S7_EARLY_Match'] = s7_early.astype(int)
            df_tmp['Pattern_S7_CONFIRMED_Match'] = s7_confirmed.astype(int)
            df_tmp['Pattern_S7_STRONG_Match'] = s7_strong.astype(int)
            df_tmp['Pattern_S8_Match'] = s8_active.astype(int)
            
            # Filtri di Sicurezza
            if 'SAR' in df_tmp.columns:
                df_tmp['SAR_Filter_Ok'] = (df_tmp['Close'] > df_tmp['SAR']).astype(int)
            else:
                df_tmp['SAR_Filter_Ok'] = 0
                
        else:
            df_tmp['Pattern_S2_Match'] = 0
            df_tmp['Pattern_S3_Match'] = 0
            df_tmp['Pattern_Combined_Match'] = 0
            df_tmp['Pattern_S4_Match'] = 0
            df_tmp['Pattern_S5_Match'] = 0
            df_tmp['Pattern_S6_Match'] = 0
            df_tmp['Pattern_S7_Match'] = 0
            df_tmp['Pattern_S7_EARLY_Match'] = 0
            df_tmp['Pattern_S7_CONFIRMED_Match'] = 0
            df_tmp['Pattern_S7_STRONG_Match'] = 0
            df_tmp['Pattern_S8_Match'] = 0
            df_tmp['Pattern_S2_Days_Ago'] = 999
            df_tmp['Pattern_S3_Days_Ago'] = 999
            df_tmp['Pattern_Combined_Days_Ago'] = 999
            df_tmp['Pattern_S4_Days_Ago'] = 999
            df_tmp['Pattern_S5_Days_Ago'] = 999
            df_tmp['Pattern_S6_Days_Ago'] = 999
            df_tmp['Pattern_S7_Days_Ago'] = 999
            df_tmp['Pattern_S7_EARLY_Days_Ago'] = 999
            df_tmp['Pattern_S7_CONFIRMED_Days_Ago'] = 999
            df_tmp['Pattern_S7_STRONG_Days_Ago'] = 999
            df_tmp['Pattern_S8_Days_Ago'] = 999
            df_tmp['SAR_Filter_Ok'] = 0
            df_tmp['SMA200'] = df_tmp['Close']
            df_tmp['SMA200_Filter_Ok'] = 0
            
        analyzer.dataframe = df_tmp

        last_dt = analyzer.dataframe.index[-1]
        ts = pd.to_datetime(last_dt)
        try:
            ts = ts.tz_localize(None)  # se tz-aware -> diventa naive
        except Exception:
            pass

        ultima_riga = analyzer.dataframe.iloc[-1].to_dict()
        ultima_riga = {
            "Date": ts,  # <-- già naive
            "Ticker": ticker,
            "Name": name,
            **ultima_riga
        }
        dati_ultime_righe.append(ultima_riga)

    # --- DataFrame finale ---
    #df_finale = pd.DataFrame(dati_ultime_righe)
    #if not df_finale.empty:
    #    colonne = ['Ticker', 'Name'] + [c for c in df_finale.columns if c not in ('Ticker', 'Name')]
    #    df_finale = df_finale[colonne]
    df_finale = pd.DataFrame(dati_ultime_righe)
    if not df_finale.empty:
        # (opzionale ma consigliato) togli il timezone per Excel
        try:
            df_finale["Date"] = pd.to_datetime(df_finale["Date"]).dt.tz_localize(None)
        except Exception:
            pass

        colonne = ['Date', 'Ticker', 'Name'] + [
            c for c in df_finale.columns if c not in ('Date', 'Ticker', 'Name')
        ]
        df_finale = df_finale[colonne]

    # --- Ordine dataframe
    #df_finale_ordinato = ordina_df_finale(df_finale)
    df_finale_ordinato = df_finale

    # 2) Aggiungi colonne di sintesi (Category, EntryTrigger, StopHint, Notes)
    if generateCategory:
        df_summary = add_summary_columns(df_finale_ordinato)
    else:
        df_summary=df_finale_ordinato

    # 3) Salva il file “analitico arricchito”
    output_file = os.path.join(OUTPUT_FOLDER, f"{market}_{OUTPUT_FILENAME}")

    # Applica filtro Liquidity se disponibile
    df_to_save = df_summary.copy()
    if liq_keep is not None and 'Liquidity' in df_to_save.columns:
        df_to_save = df_to_save[df_to_save['Liquidity'].isin(liq_keep)]

    df_summary_excel = strip_timezones_for_excel(df_to_save)
    if df_summary_excel.empty:
        raise RuntimeError(
            f"Nessun dato valido per {market}: il workbook esistente non viene sovrascritto."
        )

    # Scrittura atomica: il file corrente resta intatto se Excel o il download
    # falliscono. Solo un workbook completo sostituisce quello pubblicato.
    temp_output_file = f"{output_file}.tmp.xlsx"
    try:
        df_summary_excel.to_excel(temp_output_file, index=False, engine='openpyxl')
        os.replace(temp_output_file, output_file)
    finally:
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)

    # 4) Crea anche un workbook “multi-sheet” con viste per categoria
    #summary_file = os.path.join(OUTPUT_FOLDER, f"{market}_TA_Summary.xlsx")
    #df_summary_for_writer = strip_timezones_for_excel(df_summary)
    #write_summary_excel(df_summary_for_writer, summary_file)

    print(f"\n--- REPORT ---")
    print(f"Ticker analizzati: {len(dati_ultime_righe)}")
    print(f"Ticker scartati: {scartati}")
    print(f"File salvato in: {output_file}")
    #print(f"File summary in: {summary_file}")

    return df_summary


def run_markets(markets, numItems=0, generateSignalSAR_MA_S6_SK=1, generateScoring=1, generateCategory=1,
                liq_keep=('OK','LOW','AVOID'), print_results=False):
    """
    Esegue runTA_indicators per una lista di mercati.

    :param markets: lista dei mercati da analizzare, es. ['ETC','MIB30','ETF']
    :param numItems: default 0 → analizza tutto il file
    :param generateSignalSAR_MA_S6_SK: 0/1 → se generare segnali
    :param generateScoring: 0/1 → se generare scoring
    :param print_results: True per stampare i risultati a schermo
    :return: dizionario con {mercato: DataFrame}
    """
    results = {}
    for market in markets:
        df_result = runTA_indicators(
            market=market,
            numItems=numItems,
            generateSignal=generateSignalSAR_MA_S6_SK, #Genera colonna: SIG_MA_SAR
            generateScoring=generateScoring,     #Genera colonna: TECH_SCORE
            generateCategory=generateCategory,    #Genera colonne: Category, EntryTrigger,StopHint,Notes
            liq_keep=liq_keep
        )
        results[market] = df_result #Crea un dizionario
        if print_results:
            print(f"=== {market} ===")
            print(df_result.to_string())
    return results



def print_market_analysis(market, save_filtered=False, sort_by=None, ascending=False):
    """
    Carica e stampa i dati di analisi tecnica per un mercato (MIB30, ETF, ETC).

    :param market: Nome del mercato (stringa, es. "MIB30", "ETF", "ETC")
    :param save_filtered: True per salvare il DataFrame filtrato in un nuovo Excel
    :param sort_by: Nome della colonna o lista di colonne per ordinare i risultati (es. "TECH_SCORE")
    :param ascending: True per ordine crescente, False per decrescente
    :return: DataFrame filtrato e ordinato con colonne predefinite
    """
    col_order = [
        "Date","Ticker","Close","Category","TECH_SCORE","EntryTrigger","StopHint","Notes","ADX","ATR","MACD_Positive_Days", "MACD_Negative_Days", "MACD_Sign_Streak","MACDH_Trend", "MACDH_Trend_Days","PCTV_1D", "PCTV_5D", "PCTV_10D", "Name","SIG_MA_SAR","MCS","Category","Volume","Vol_Perc_vs_MA5","Vol_Perc_vs_MA20","Signal6", "Signal6_Trend_Days", "TECH_SCORE",
        "MCS_Smoothed","MCS_Conf",
        "RSI", "RSI_Trend", "RSI_Trend_Days",
        "MACD", "MACD_Signal", "MACD_Hist",
        "PCTV_30D", "PCTV_180D",
        "Stoch_K", "Stoch_D", "SK_Trend", "SK_Trend_Days",
        "SAR", "SAR_Above_Price",
        "Alligator_Jaw", "Alligator_Teeth", "Alligator_Lips",
        "EMA_50", "EMA_30",
        "Williams_R", "WILLR_Trend", "WILLR_Trend_Days",
        "WILLR_Overbought", "WILLR_Oversold", "WILLR_Neutral",
    ]
    col_order = [
        "Date","Ticker","Close","TECH_SCORE",'Liquidity',

    ]

    # Percorso file sorgente
    file_path = os.path.join(OUTPUT_FOLDER, f"{market}_TA_Analyses.xlsx")

    # Caricamento Excel
    df_load = pd.read_excel(file_path, sheet_name=0)

    # Filtro Volume > 1500
    df_filtered = df_load[df_load["Volume"] > 1500]

    # Ordinamento se richiesto
    if sort_by:
        df_filtered = df_filtered.sort_values(by=sort_by, ascending=ascending)

    # Stampa tabella ordinata
    print("--- STAMPO COLONNE ORDINATE")
    print(df_filtered[col_order].to_string())

    # Salvataggio opzionale
    if save_filtered:
        out_path = os.path.join(OUTPUT_FOLDER, f"{market}_TA_Filtered.xlsx")
        df_filtered[col_order].to_excel(out_path, index=False)
        print(f"✅ File salvato: {out_path}")

    return df_filtered[col_order]



def print_v4_v0(market: str, max_rows: int = 200):
    market = market.strip().upper()
    file_path = os.path.join(OUTPUT_FOLDER, f"{market}_TA_Analyses.xlsx")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File non trovato: {file_path}")

    xls = pd.ExcelFile(file_path)
    sheet_to_use = market if market in xls.sheet_names else xls.sheet_names[0]

    df = pd.read_excel(file_path, sheet_name=sheet_to_use)

    # ✅ Normalizza i nomi colonne (Excel spesso introduce spazi)
    df.columns = df.columns.astype(str).str.strip()

    print(f"\nDEBUG: file caricato da: {file_path}")
    print(f"DEBUG: sheet usato: {sheet_to_use}")

    # -----------------------------
    # colonne "nuove" (se esistono)
    # -----------------------------
    pullback_cols = [
        "Pullback_Entry_Level",
        "Pullback_Entry_Zone_Low",
        "Pullback_Entry_Zone_High",
        "Pullback_Stop_Level",
        "Pullback_Invalidation",
        "Pullback_Entry_Note",
    ]

    trend_stop_cols = [
        "Trend_Stop_Level",
        "Trend_Stop_Invalidation",
        "Trend_Stop_Type",
    ]

    # ✅ CE stop level: priorità CE_Long_Level (se mai esisterà), fallback su CE_Long (che nel tuo file c'è)
    ce_stop_cols = [
        "CE_Long_Level",
        "CE_Long",
    ]

    base_cols = ["Ticker", "Close", "Action", "Action_Reason", "Market_Phase", "Layer3_Warning"]

    # tieni solo quelle presenti nel file
    present_pullback_cols = [c for c in pullback_cols if c in df.columns]
    present_trend_cols = [c for c in trend_stop_cols if c in df.columns]
    present_ce_cols = [c for c in ce_stop_cols if c in df.columns]

    # debug columns utili
    debug_cols = [c for c in df.columns if any(k in c for k in [
        "Action", "Phase", "Pullback", "Trend_Stop", "CE_Long", "Layer3"
    ])]
    print("DEBUG columns (key):", debug_cols)
    print("DEBUG CE columns:", [c for c in df.columns if "CE" in c.upper()])

    # controllo colonne base
    missing = [c for c in base_cols if c not in df.columns]
    if missing:
        raise KeyError(f"Colonne mancanti: {missing}")

    # -----------------------------
    # print tabella generale
    # -----------------------------
    cols_general = base_cols + present_pullback_cols + present_trend_cols + present_ce_cols

    # ordinamento più leggibile: Action -> Phase -> Close desc
    df_sorted = df.sort_values(by=["Action", "Market_Phase", "Close"], ascending=[True, True, False])

    print("\n==============================")
    print("📌 V4 SUMMARY (general)")
    print("==============================")
    print(df_sorted[cols_general].head(max_rows).to_string(index=False))

    print("\nAction counts:\n", df["Action"].value_counts(dropna=False))
    print("\nMarket_Phase counts:\n", df["Market_Phase"].value_counts(dropna=False))

    # -----------------------------
    # print PULLBACK levels (solo pullback)
    # -----------------------------
    if present_pullback_cols:
        df_pb = df[df["Market_Phase"].astype(str).str.upper().str.strip() == "PULLBACK"].copy()
        if not df_pb.empty:
            cols_pb = ["Ticker", "Close", "Action", "Action_Reason", "Layer3_Warning"] + present_pullback_cols + present_ce_cols
            sort_cols = [c for c in ["Pullback_Entry_Note", "Action", "Close"] if c in df_pb.columns]
            if sort_cols:
                df_pb = df_pb.sort_values(by=sort_cols, ascending=[True] * len(sort_cols))

            print("\n==============================")
            print("🟠 PULLBACK (entry zone + stop)")
            print("==============================")
            print(df_pb[cols_pb].head(max_rows).to_string(index=False))
        else:
            print("\n🟠 PULLBACK: nessuna riga con Market_Phase=PULLBACK.")
    else:
        print("\n🟠 PULLBACK: colonne livelli non presenti nel file (Pullback_Entry_Zone_*, Pullback_Stop_Level...).")

    # -----------------------------
    # print UPTREND BUY/ADD stop (solo uptrend trade)
    # -----------------------------
    if present_trend_cols:
        df_ut = df[
            (df["Market_Phase"].astype(str).str.upper().str.strip() == "UPTREND") &
            (df["Action"].astype(str).str.upper().str.strip().isin(["BUY", "ADD"]))
        ].copy()

        if not df_ut.empty:
            cols_ut = ["Ticker", "Close", "Action", "Action_Reason", "Layer3_Warning"] + present_trend_cols + present_ce_cols

            # ordina per invalidation prima (se presente)
            if "Trend_Stop_Invalidation" in df_ut.columns:
                df_ut = df_ut.sort_values(
                    by=["Trend_Stop_Invalidation", "Action", "Close"],
                    ascending=[False, True, False]
                )

            print("\n==============================")
            print("🟢 UPTREND BUY/ADD (stop levels)")
            print("==============================")
            print(df_ut[cols_ut].head(max_rows).to_string(index=False))
        else:
            print("\n🟢 UPTREND BUY/ADD: nessuna riga con Market_Phase=UPTREND e Action in {BUY,ADD}.")
    else:
        print("\n🟢 UPTREND BUY/ADD: colonne Trend_Stop_* non presenti nel file.")
def print_v4(market: str, max_rows: int = 200):
    market = market.strip()
    file_path = os.path.join(OUTPUT_FOLDER, f"{market}_TA_Analyses.xlsx")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File non trovato: {file_path}")

    xls = pd.ExcelFile(file_path)
    sheet_to_use = market if market in xls.sheet_names else xls.sheet_names[0]

    df = pd.read_excel(file_path, sheet_name=sheet_to_use)

    # ✅ Normalizza i nomi colonne
    df.columns = df.columns.astype(str).str.strip()

    print(f"\nDEBUG: file caricato da: {file_path}")
    print(f"DEBUG: sheet usato: {sheet_to_use}")

    # -----------------------------
    # ✅ colonna Name (se presente)
    # -----------------------------
    name_col = "Name" if "Name" in df.columns else None

    def with_name(cols):
        if name_col and name_col not in cols:
            if "Ticker" in cols:
                i = cols.index("Ticker") + 1
                return cols[:i] + [name_col] + cols[i:]
            return cols + [name_col]
        return cols

    # -----------------------------
    # colonne "nuove" (se esistono)
    # -----------------------------
    pullback_cols = [
        "Pullback_Entry_Level",
        "Pullback_Entry_Zone_Low",
        "Pullback_Entry_Zone_High",
        "Pullback_Stop_Level",
        "Pullback_Invalidation",
        "Pullback_Entry_Note",
    ]

    trend_stop_cols = [
        "Trend_Stop_Level",
        "Trend_Stop_Invalidation",
        "Trend_Stop_Type",
    ]

    ce_stop_cols = [
        "CE_Long_Level",
        "CE_Long",
    ]

    base_cols = ["Ticker", "Close", "Action", "Action_Reason", "Market_Phase", "Layer3_Warning"]
    base_cols = with_name(base_cols)

    present_pullback_cols = [c for c in pullback_cols if c in df.columns]
    present_trend_cols = [c for c in trend_stop_cols if c in df.columns]
    present_ce_cols = [c for c in ce_stop_cols if c in df.columns]

    # controllo colonne base (Name è opzionale)
    required_base_cols = ["Ticker", "Close", "Action", "Action_Reason", "Market_Phase", "Layer3_Warning"]
    missing = [c for c in required_base_cols if c not in df.columns]
    if missing:
        raise KeyError(f"Colonne mancanti: {missing}")

    # -----------------------------
    # print tabella generale
    # -----------------------------
    cols_general = base_cols + present_pullback_cols + present_trend_cols + present_ce_cols

    df_sorted = df.sort_values(by=["Action", "Market_Phase", "Close"], ascending=[True, True, False])

    print("\n==============================")
    print("📌 V4 SUMMARY (general)")
    print("==============================")
    print(df_sorted[cols_general].head(max_rows).to_string(index=False))

    print("\nAction counts:\n", df["Action"].value_counts(dropna=False))
    print("\nMarket_Phase counts:\n", df["Market_Phase"].value_counts(dropna=False))

    # -----------------------------
    # print PULLBACK levels
    # -----------------------------
    if present_pullback_cols:
        df_pb = df[df["Market_Phase"].astype(str).str.upper().str.strip() == "PULLBACK"].copy()
        if not df_pb.empty:
            cols_pb = ["Ticker", "Close", "Action", "Action_Reason", "Layer3_Warning"]
            cols_pb = with_name(cols_pb) + present_pullback_cols + present_ce_cols

            sort_cols = [c for c in ["Pullback_Entry_Note", "Action", "Close"] if c in df_pb.columns]
            if sort_cols:
                df_pb = df_pb.sort_values(by=sort_cols, ascending=[True] * len(sort_cols))

            print("\n==============================")
            print("🟠 PULLBACK (entry zone + stop)")
            print("==============================")
            print(df_pb[cols_pb].head(max_rows).to_string(index=False))
        else:
            print("\n🟠 PULLBACK: nessuna riga con Market_Phase=PULLBACK.")
    else:
        print("\n🟠 PULLBACK: colonne livelli non presenti nel file.")

    # -----------------------------
    # print UPTREND BUY/ADD stop
    # -----------------------------
    if present_trend_cols:
        df_ut = df[
            (df["Market_Phase"].astype(str).str.upper().str.strip() == "UPTREND") &
            (df["Action"].astype(str).str.upper().str.strip().isin(["BUY", "ADD"]))
        ].copy()

        if not df_ut.empty:
            cols_ut = ["Ticker", "Close", "Action", "Action_Reason", "Layer3_Warning"]
            cols_ut = with_name(cols_ut) + present_trend_cols + present_ce_cols

            if "Trend_Stop_Invalidation" in df_ut.columns:
                df_ut = df_ut.sort_values(
                    by=["Trend_Stop_Invalidation", "Action", "Close"],
                    ascending=[False, True, False]
                )

            print("\n==============================")
            print("🟢 UPTREND BUY/ADD (stop levels)")
            print("==============================")
            print(df_ut[cols_ut].head(max_rows).to_string(index=False))
        else:
            print("\n🟢 UPTREND BUY/ADD: nessuna riga con Market_Phase=UPTREND e Action in {BUY,ADD}.")
    else:
        print("\n🟢 UPTREND BUY/ADD: colonne Trend_Stop_* non presenti nel file.")

'''' ---- Spiegazione codice e parametri funzione ----
> Questa funzione viene chiamata sempre<
analyzer.calculate_TA_Indicators("ADX,ATR,MACD,VOL_PERC,RSI,SAR,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30,PCTV")

> Queste sono opzionali<
generateSignal   = Chiama queste funzioni per generare questi segnali 
            analyzer.generate_signal_SAR_MA()
            analyzer.calculate_alligator_signal6()
            analyzer.generate_stoch_reversal_signals()
generateScoring  = generateScoring,       # Genera colonna: TECH_SCORE (nome fuorviante) -> analyzer.calculate_technical_score(weights=custom_weights)
generateCategory = generateCategory       # Genera colonne: Category, EntryTrigger,StopHint,Notes -> add_summary_columns()
liq_keep=('OK','LOW','AVOID')             # Non salva titoli con liquidita` LOW or AVOID (molto bassa)
NOTA: viene sempre chiamata la funzione per generare Layer1,2,3 indicazioni: analyzer.add_trading_layers_state_v3
'''

SUPPORTED_ANALYSIS_MARKETS = ['MIB30', 'Preferite', 'DAX', 'ETC', 'ETF', 'US_Others']
_requested_markets = os.getenv("IFINANCE_ANALYSIS_MARKETS", "").strip()
if _requested_markets:
    markets_to_run = [
        market.strip()
        for market in _requested_markets.split(",")
        if market.strip() in SUPPORTED_ANALYSIS_MARKETS
    ]
    if not markets_to_run:
        raise ValueError(
            "IFINANCE_ANALYSIS_MARKETS non contiene mercati validi. "
            f"Valori ammessi: {', '.join(SUPPORTED_ANALYSIS_MARKETS)}"
        )
else:
    markets_to_run = ['MIB30', 'Preferite', 'DAX', 'ETC', 'ETF']

print(f"[ANALISI] Mercati selezionati: {', '.join(markets_to_run)}", flush=True)
#,'MIB30','ETC','ETF']
# ,'US_Others']

print("[ANALISI] Modalità realtime: download Yahoo Finance obbligatorio.", flush=True)

all_results = run_markets(
    markets_to_run,
    numItems=0,
    generateSignalSAR_MA_S6_SK=1,
    generateScoring=1,
    generateCategory=0,
    liq_keep=('OK','LOW','AVOID'),
    print_results=True
)

#print(v4_legenda())
#print_v4("MIB30")

'''
m = messaging()
m.send_uptrend_buyadd_summary(
    market="MIB30",
    base_folder=OUTPUT_FOLDER,
    telegramChannel=1,
    max_list=20,
    send_list=True
)
m.send_uptrend_buyadd_summary(
    market="Preferite",
    base_folder=OUTPUT_FOLDER,
    telegramChannel=2,
    max_list=20,
    send_list=True
)

m.send_uptrend_buyadd_summary(
    market="ETC",
    base_folder=OUTPUT_FOLDER,
    telegramChannel=3,
    max_list=20,
    send_list=True
)

m.send_uptrend_buyadd_summary(
    market="ETF",
    base_folder=OUTPUT_FOLDER,
    telegramChannel=4,
    max_list=20,
    send_list=True
)'''


# Alerts set via React GUI (alert_rules_<MARKET>.yaml)
run_gui_alerts(
    OUTPUT_FOLDER,
    telegram_channel=5,
    markets=markets_to_run,
    require_enabled_rules=True,
)
