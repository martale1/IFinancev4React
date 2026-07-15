from __future__ import annotations

import os
import re
import sys
import time
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import talib
import yfinance as yf

try:
    import vectorbt as vbt
    VECTORBT_AVAILABLE = True
except ImportError:
    vbt = None
    VECTORBT_AVAILABLE = False
    print("[WARNING] vectorbt non disponibile su questo sistema. Il backtest Multi-Pattern non sarà operativo.")

from app.config import PROJECT_ROOT, ANALYSES_DIR
from filehandling import fileHandling

CACHE_DIR = PROJECT_ROOT / "cache"

# ─── Cache in-memory degli Excel pre-calcolati ───────────────────────────────
# Evita di rileggere dal disco a ogni scansione. La cache viene caricata al
# primo accesso e invalidata esplicitamente quando main.py aggiorna i file.
_excel_cache: Dict[str, pd.DataFrame] = {}      # market -> DataFrame
_excel_cache_mtime: Dict[str, float] = {}        # market -> mtime al momento del caricamento

def _load_excel_cached(market: str) -> pd.DataFrame:
    """
    Carica l'Excel di analisi per il mercato dalla cache in-memory.
    Rilegge da disco solo se il file è stato modificato (mtime cambiato).
    """
    from app.services.watchlist_service import load_market_dataframe, prepare_dataframe, analysis_path_for_market
    try:
        fp = analysis_path_for_market(market)
        current_mtime = fp.stat().st_mtime
        # Se già in cache e non modificato, restituisce subito
        if market in _excel_cache and _excel_cache_mtime.get(market) == current_mtime:
            return _excel_cache[market]
        # Altrimenti rilegge e aggiorna la cache
        print(f"[SCANNER CACHE] Caricamento Excel per mercato '{market}' dal disco...")
        df = load_market_dataframe(market)
        df = prepare_dataframe(df)
        _excel_cache[market] = df
        _excel_cache_mtime[market] = current_mtime
        return df
    except Exception as exc:
        raise exc

def invalidate_excel_cache(market: str | None = None) -> None:
    """Invalida la cache per un mercato specifico (o tutti se market=None)."""
    global _excel_cache, _excel_cache_mtime
    if market:
        _excel_cache.pop(market, None)
        _excel_cache_mtime.pop(market, None)
    else:
        _excel_cache.clear()
        _excel_cache_mtime.clear()
    print(f"[SCANNER CACHE] Cache invalidata per: {market or 'tutti i mercati'}")

def ensure_cache_dir() -> None:
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_cache_path(ticker: str, period: str = "2y", interval: str = "1d") -> Path:
    """Ritorna il percorso del file di cache parquet per un ticker."""
    clean_ticker = str(ticker).strip().upper().replace("/", "_")
    base_part = clean_ticker.split(".")[0]
    if base_part in ["CON", "PRN", "AUX", "NUL"] or any(
        base_part.startswith(x) for x in ["COM", "LPT"] if len(base_part) == 4 and base_part[3].isdigit()
    ):
        clean_ticker = f"W_{clean_ticker}"
    if interval == "1d":
        return CACHE_DIR / f"{clean_ticker}_{period}_history.parquet"
    return CACHE_DIR / f"{clean_ticker}_{period}_{interval}.parquet"

def bulk_download_and_cache(tickers: List[str], period: str = "2y", interval: str = "1d", force_refresh: bool = False) -> None:
    """
    Scarica i dati storici per tutti i ticker in blocco (bulk) per massimizzare la velocità
    e popola la cache parquet locale.
    """
    ensure_cache_dir()
    
    tickers_to_download = []
    for ticker in tickers:
        if not ticker or not isinstance(ticker, str):
            continue
        cache_path = _get_cache_path(ticker, period, interval)
        use_cache = False
        if cache_path.exists() and not force_refresh:
            file_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
            if datetime.now() - file_mtime < timedelta(hours=4):
                use_cache = True
        if not use_cache:
            tickers_to_download.append(ticker)
            
    if not tickers_to_download:
        return
        
    print(f"[SCANNER BULK] Download in blocco di {len(tickers_to_download)} ticker da Yahoo Finance...")
    try:
        data = yf.download(tickers_to_download, period=period, interval=interval, group_by="ticker", progress=False, auto_adjust=False, threads=True)
        if data.empty:
            print("[SCANNER BULK] Risposta vuota dal download in blocco.")
            return
            
        if len(tickers_to_download) == 1:
            ticker = tickers_to_download[0]
            cache_path = _get_cache_path(ticker, period, interval)
            df = data.copy()
            if isinstance(df.columns, pd.MultiIndex):
                if ticker in df.columns.levels[0]:
                    df = df[ticker].copy()
            df.dropna(how="all").to_parquet(cache_path)
            return

        for ticker in tickers_to_download:
            cache_path = _get_cache_path(ticker, period, interval)
            try:
                if isinstance(data.columns, pd.MultiIndex) and ticker in data.columns.levels[0]:
                    df_ticker = data[ticker].dropna(how="all").copy()
                    if not df_ticker.empty:
                        if not isinstance(df_ticker.index, pd.DatetimeIndex):
                            df_ticker.index = pd.to_datetime(df_ticker.index)
                        df_ticker.to_parquet(cache_path)
            except Exception as e:
                print(f"[SCANNER BULK] Errore nel salvataggio della cache per {ticker}: {e}")
    except Exception as e:
        print(f"[SCANNER BULK] Errore durante il download in blocco: {e}")

def get_historical_data(ticker: str, period: str = "2y", interval: str = "1d", force_refresh: bool = False) -> pd.DataFrame:
    """
    Scarica i dati storici per un ticker da Yahoo Finance.
    Usa la cache locale parquet se disponibile e aggiornata (meno di 12 ore fa).
    """
    ensure_cache_dir()
    cache_path = _get_cache_path(ticker, period, interval)
    
    # Verifica validità cache (4 ore per allineamento intraday)
    use_cache = False
    if cache_path.exists() and not force_refresh:
        file_mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - file_mtime < timedelta(hours=4):
            use_cache = True
            
    if use_cache:
        try:
            df = pd.read_parquet(cache_path)
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            return df
        except Exception as e:
            print(f"Errore nel caricamento della cache per {ticker}: {e}. Scaricamento dati in corso...")
            
    # Scarica i dati storici
    try:
        yf_ticker = str(ticker).strip()
        data = yf.download(yf_ticker, period=period, interval=interval, progress=False, auto_adjust=False)
        
        if data.empty:
            raise ValueError("Dati scaricati vuoti da Yahoo Finance")
            
        # Pulisci le colonne MultiIndex
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        # Assicura colonne standard
        required_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        for col in required_cols:
            if col not in data.columns:
                alt_names = [col.lower(), col.replace(" ", "_"), col.replace(" ", "_").lower()]
                for alt in alt_names:
                    if alt in data.columns:
                        data.rename(columns={alt: col}, inplace=True)
                        break
                        
        if 'Adj Close' not in data.columns:
            if 'Close' in data.columns:
                data['Adj Close'] = data['Close']
                    
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
            
        data.to_parquet(cache_path)
        return data
    except Exception as e:
        print(f"Errore nello scaricamento dei dati per {ticker}: {e}. Tentativo di fallback alla cache esistente...")
        if cache_path.exists():
            try:
                df = pd.read_parquet(cache_path)
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)
                print(f"Fallback riuscito: usati dati di cache scaduti per {ticker}")
                return df
            except Exception as e_fallback:
                print(f"Impossibile leggere la cache di fallback per {ticker}: {e_fallback}")
        return pd.DataFrame()



def calculate_all_indicators(df: pd.DataFrame, use_adjusted: bool = True) -> pd.DataFrame:
    """
    Calcola gli indicatori tecnici e i relativi shift storici per scansione e backtesting.
    """
    if len(df) < 15:
        return df

    df = df.copy()

    if use_adjusted and 'Adj Close' in df.columns:
        ratio = (df['Adj Close'] / df['Close'].replace(0, np.nan)).fillna(1.0)
        df['Close'] = df['Adj Close']
        df['Open'] = (df['Open'] * ratio).fillna(df['Close'])
        df['High'] = (df['High'] * ratio).fillna(df['Close'])
        df['Low'] = (df['Low'] * ratio).fillna(df['Close'])

    close = df['Close'].values.flatten().astype(float)
    high = df['High'].values.flatten().astype(float)
    low = df['Low'].values.flatten().astype(float)

    # Indicatori
    df['SMA200'] = talib.SMA(close, timeperiod=200)
    df['RSI'] = talib.RSI(close, timeperiod=14)
    df['ADX'] = talib.ADX(high, low, close, timeperiod=14)
    df['PLUS_DI'] = talib.PLUS_DI(high, low, close, timeperiod=14)
    df['MINUS_DI'] = talib.MINUS_DI(high, low, close, timeperiod=14)
    
    macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    df['MACD'] = macd
    df['MACD_Signal'] = macdsignal
    df['MACD_Hist'] = macdhist
    
    # Stochastic (5, 3, 3) per coerenza
    slowk, slowd = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
    df['Stoch_K'] = np.clip(slowk, 0.0, 100.0)
    df['Stoch_D'] = np.clip(slowd, 0.0, 100.0)
    df['Stoch_K_shift1'] = df['Stoch_K'].shift(1)
    df['Stoch_D_shift1'] = df['Stoch_D'].shift(1)

    df['SAR'] = talib.SAR(high, low, acceleration=0.02, maximum=0.2)
    df['Williams_R'] = talib.WILLR(high, low, close, timeperiod=14)
    df['Williams_R_shift1'] = df['Williams_R'].shift(1)
    df['Williams_R_shift2'] = df['Williams_R'].shift(2)
    
    df['MACD_shift1'] = df['MACD'].shift(1)
    df['MACD_Signal_shift1'] = df['MACD_Signal'].shift(1)
    df['MACD_Hist_shift1'] = df['MACD_Hist'].shift(1)

    # Bande Chandelier / ATR per visualizzatore
    df['ATR'] = talib.ATR(high, low, close, timeperiod=14)

    # EMA9 e EMA21 per Pattern S4
    df['EMA_9']  = talib.EMA(close, timeperiod=9)
    df['EMA_21'] = talib.EMA(close, timeperiod=21)
    
    # EMA30 e EMA50 per custom patterns
    df['EMA_30'] = talib.EMA(close, timeperiod=30)
    df['EMA_50'] = talib.EMA(close, timeperiod=50)
    df['EMA_30_shift1'] = df['EMA_30'].shift(1)
    df['EMA_50_shift1'] = df['EMA_50'].shift(1)

    # Volume MA20 per Pattern S4
    volume = df['Volume'].values.flatten().astype(float)
    df['Volume_MA20'] = talib.SMA(volume, timeperiod=20)

    # RSI shift per condizione "crescente" di S4
    df['RSI_shift1'] = df['RSI'].shift(1)

    # Campo calcolato Sk vs Sd: positivo = Sk sopra Sd (crossover rialzista)
    # Analogo a MACD_vs_Signal: alert "Stoch_KvsD > 0" equivale a "Sk > Sd"
    df['Stoch_KvsD'] = df['Stoch_K'] - df['Stoch_D']

    # Campo calcolato DI+ vs DI-: positivo = DI+ sopra DI- (trend direzionale rialzista)
    # alert "DI_diff > 0" equivale a "DI+ > DI-"
    df['DI_diff'] = df['PLUS_DI'] - df['MINUS_DI']

    # Alligator lines (Jaw 13 shift 8, Teeth 8 shift 5, Lips 5 shift 3)
    df['Alligator_Jaw'] = pd.Series(talib.WMA(close, timeperiod=13), index=df.index).shift(8)
    df['Alligator_Teeth'] = pd.Series(talib.WMA(close, timeperiod=8), index=df.index).shift(5)
    df['Alligator_Lips'] = pd.Series(talib.WMA(close, timeperiod=5), index=df.index).shift(3)

    # Alligator Signal6 trend states
    df['Signal6'] = 'sleep1'
    lips = df['Alligator_Lips']
    teeth = df['Alligator_Teeth']
    jaw = df['Alligator_Jaw']
    close_s = df['Close']

    # Downtrend states
    down_mask = (lips > close_s) & (lips < teeth) & (teeth < jaw)
    df.loc[down_mask, 'Signal6'] = 'Downtrend'
    df.loc[(lips < close_s) & (lips < teeth) & (teeth < jaw), 'Signal6'] = 'Downtrend_revS3Sig+'
    df.loc[(teeth < close_s) & (lips < teeth) & (teeth < jaw), 'Signal6'] = 'Downtrend_revS3Sig++'
    df.loc[(jaw < close_s) & (lips < teeth) & (teeth < jaw), 'Signal6'] = 'Downtrend_revS3Sig+++'

    # Uptrend states
    up_struct = (jaw < teeth) & (teeth < lips)
    df.loc[(close_s <= jaw) & up_struct, 'Signal6'] = 'Uptrend---'
    df.loc[(jaw < close_s) & (close_s <= teeth) & up_struct, 'Signal6'] = 'Uptrend--'
    df.loc[(teeth < close_s) & (close_s <= lips) & up_struct, 'Signal6'] = 'Uptrend-'
    df.loc[(lips < close_s) & up_struct, 'Signal6'] = 'Uptrend'

    # Stato e trigger usati dal pattern S7. Il trigger è vero solo nella prima
    # seduta in cui Close > SAR e Signal6 entra in uno stato Uptrend.
    alligator_bull_state = (df['Close'] > df['SAR']) & df['Signal6'].astype(str).str.startswith('Uptrend')
    df['Alligator_Bull_State'] = alligator_bull_state
    df['Alligator_Bull_Trigger'] = alligator_bull_state & ~alligator_bull_state.shift(1, fill_value=False)

    return df

def get_pattern_rule(pattern: str) -> str | None:
    """
    Ritorna la regola del pattern (query string di pandas) cercandola prima
    nei pattern personalizzati di custom_patterns.yaml.
    """
    yaml_path = Path(PROJECT_ROOT) / "custom_patterns.yaml"
    if yaml_path.exists():
        try:
            import yaml
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                for p in data.get("patterns", []):
                    if p.get("id") == pattern:
                        return p.get("query")
        except Exception as e:
            print(f"[SCANNER] Errore lettura custom_patterns.yaml: {e}")
    return None


def get_pattern_label(pattern: str) -> str:
    """
    Ritorna la label descrittiva di un pattern personalizzato.
    """
    yaml_path = Path(PROJECT_ROOT) / "custom_patterns.yaml"
    if yaml_path.exists():
        try:
            import yaml
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                for p in data.get("patterns", []):
                    if p.get("id") == pattern:
                        return p.get("label", pattern)
        except Exception:
            pass
    return pattern


def scan_single_ticker(ticker: str, pattern: str, use_sar: bool, use_sma200: bool, lookback: int = 1) -> dict | None:
    """
    Esegue la scansione di un singolo ticker verificando i pattern S2, S3 o Combinato.
    Supporta la massima anzianità segnale (lookback).
    """
    try:
        df_hist = get_historical_data(ticker, period="2y")
        if df_hist.empty or len(df_hist) < 40:
            return None
        
        df_calc = calculate_all_indicators(df_hist, use_adjusted=False)
        if df_calc.empty or len(df_calc) < 15:
            return None
            
        # Calcola i segnali booleani per tutto lo storico
        # 1. Pattern S2 (Williams + Stocastico)
        w = df_calc['Williams_R']
        w_shift1 = df_calc['Williams_R_shift1']
        w_shift2 = df_calc['Williams_R_shift2']
        
        k = df_calc['Stoch_K']
        d = df_calc['Stoch_D']
        k_shift1 = df_calc['Stoch_K_shift1']
        d_shift1 = df_calc['Stoch_D_shift1']
        
        # S2 Pattern ottimizzato (cattura le ripartenze dai minimi con stocastico basso < 35)
        stoch_bullish = (k > d) & (k > 20)
        williams_bullish = (w > -80) & (w > w_shift1)
        stoch_trigger = ((k > 20) & (k_shift1 <= 20)) | ((k > d) & (k_shift1 <= d_shift1))
        williams_trigger = (w > -80) & (w_shift1 <= -80)
        stoch_low = k_shift1 < 35
        s2_active_series = stoch_bullish & williams_bullish & (stoch_trigger | williams_trigger) & stoch_low
        
        # 2. Pattern S3 (MACD)
        macd = df_calc['MACD']
        signal = df_calc['MACD_Signal']
        macd_shift1 = df_calc['MACD_shift1']
        signal_shift1 = df_calc['MACD_Signal_shift1']
        hist = df_calc['MACD_Hist']
        hist_shift1 = df_calc['MACD_Hist_shift1']
        
        macd_cross = (macd > signal) & (macd_shift1 <= signal_shift1)
        macd_rose = macd > macd_shift1
        hist_ok = (hist > 0) & (hist > hist_shift1)
        s3_active_series = macd_cross & macd_rose & hist_ok

        # 3. Pattern S4 (EMA Momentum Confermato con Volume)
        rsi      = df_calc['RSI']        if 'RSI'        in df_calc.columns else pd.Series(50.0, index=df_calc.index)
        rsi_sh1  = df_calc['RSI_shift1'] if 'RSI_shift1' in df_calc.columns else rsi.shift(1)
        ema9     = df_calc['EMA_9']      if 'EMA_9'      in df_calc.columns else pd.Series(0.0,  index=df_calc.index)
        ema21    = df_calc['EMA_21']     if 'EMA_21'     in df_calc.columns else pd.Series(0.0,  index=df_calc.index)
        vol      = df_calc['Volume']     if 'Volume'     in df_calc.columns else pd.Series(0.0,  index=df_calc.index)
        vol_ma20 = df_calc['Volume_MA20']if 'Volume_MA20'in df_calc.columns else pd.Series(1.0,  index=df_calc.index)

        s4_ema    = ema9 > ema21
        s4_rsi    = (rsi >= 55) & (rsi <= 70) & (rsi > rsi_sh1)
        s4_macd   = macd > signal
        s4_volume = vol > (vol_ma20 * 1.5)
        s4_active_series = s4_ema & s4_rsi & s4_macd & s4_volume

        # 4. Pattern S5 – RSI Oversold con evento di incrocio stocastico
        k_s5   = df_calc['Stoch_K'] if 'Stoch_K' in df_calc.columns else pd.Series(50.0, index=df_calc.index)
        d_s5   = df_calc['Stoch_D'] if 'Stoch_D' in df_calc.columns else pd.Series(50.0, index=df_calc.index)
        rsi_s5 = df_calc['RSI']     if 'RSI'     in df_calc.columns else pd.Series(50.0, index=df_calc.index)
        s5_active_series = (
            (rsi_s5 < 30)
            & (k_s5 > d_s5)
            & (k_s5.shift(1) <= d_s5.shift(1))
        )

        # 5. Pattern S6 – evento di incrocio EMA30 sopra EMA50 con ADX forte
        ema30_s6 = df_calc['EMA_30'] if 'EMA_30' in df_calc.columns else pd.Series(0.0, index=df_calc.index)
        ema50_s6 = df_calc['EMA_50'] if 'EMA_50' in df_calc.columns else pd.Series(0.0, index=df_calc.index)
        adx_s6   = df_calc['ADX']    if 'ADX'    in df_calc.columns else pd.Series(0.0, index=df_calc.index)
        s6_active_series = (
            (ema30_s6 > ema50_s6)
            & (ema30_s6.shift(1) <= ema50_s6.shift(1))
            & (adx_s6 > 25)
        )

        # 6. Pattern S7 – ingresso nello stato Alligator Bull
        sar_s7 = df_calc['SAR'] if 'SAR' in df_calc.columns else pd.Series(0.0, index=df_calc.index)
        if 'Signal6' in df_calc.columns:
            sig6_up = df_calc['Signal6'].astype(str).str.startswith('Uptrend')
        else:
            sig6_up = pd.Series(False, index=df_calc.index)
        s7_bull_state = (df_calc['Close'] > sar_s7) & sig6_up
        s7_active_series = s7_bull_state & ~s7_bull_state.shift(1, fill_value=False)

        # 7. Pattern S8 – Volume Breakout (candela rialzista + volume > MA20 × 1.5)
        open_s8     = df_calc['Open']        if 'Open'        in df_calc.columns else df_calc['Close']
        vol_ma20_s8 = df_calc['Volume_MA20'] if 'Volume_MA20' in df_calc.columns else pd.Series(1.0, index=df_calc.index)
        s8_active_series = (df_calc['Close'] > open_s8) & (df_calc['Volume'] > (vol_ma20_s8 * 1.5))

        custom_query = get_pattern_rule(pattern)
        if custom_query:
            try:
                # Usa engine='python' per supportare metodi str (es. Signal6.str.startswith)
                matched_indices = df_calc.query(custom_query, engine='python').index
                active_series = pd.Series(df_calc.index.isin(matched_indices), index=df_calc.index)
            except Exception as e:
                print(f"[SCANNER] Errore valutazione query '{custom_query}' per {ticker}: {e}")
                return None
        elif pattern == "S2":
            active_series = s2_active_series
        elif pattern == "S3":
            active_series = s3_active_series
        elif pattern == "S4":
            active_series = s4_active_series
        elif pattern == "S5":
            active_series = s5_active_series
        elif pattern == "S6":
            active_series = s6_active_series
        elif pattern == "S7":
            active_series = s7_active_series
        elif pattern == "S8":
            active_series = s8_active_series
        elif pattern == "Combined":
            active_series = s2_active_series & s3_active_series
        elif pattern == "S2_or_S3":
            active_series = s2_active_series | s3_active_series
        else:
            return None
            
        L = len(df_calc)
        found_idx = -1
        days_ago = 999
        
        # Scansiona all'indietro a partire dall'ultima riga (offset 0) fino a lookback-1
        for offset in range(lookback):
            idx = L - 1 - offset
            if idx < 0:
                break
            if bool(active_series.iloc[idx]):
                row_idx = df_calc.iloc[idx]
                
                # Applica i filtri di sicurezza sulla stessa riga in cui è avvenuto il segnale
                sar_ok = True
                if use_sar and 'SAR' in row_idx and not pd.isna(row_idx['SAR']):
                    sar_ok = float(row_idx['Close']) > float(row_idx['SAR'])
                    
                sma200_ok = True
                if use_sma200 and 'SMA200' in row_idx and not pd.isna(row_idx['SMA200']):
                    sma200_ok = float(row_idx['Close']) > float(row_idx['SMA200'])
                    
                if sar_ok and sma200_ok:
                    found_idx = idx
                    days_ago = offset
                    break
                    
        if found_idx != -1:
            row_t = df_calc.iloc[-1]  # Restituiamo comunque i valori correnti/ultimi del ticker
            p_current = float(row_t['Close'])

            # ── Trova l'inizio della striscia corrente ────────────────────────────
            # Per i pattern persistenti (es. Alligator Bull) la condizione è vera
            # per più giorni consecutivi. Vogliamo sapere QUANDO è iniziata la
            # striscia corrente, non solo se è vera oggi. Camminiamo all'indietro
            # finché la condizione rimane vera, così days_ago riflette il giorno
            # d'inizio della striscia (es. 55 per ALV.DE in Uptrend da 55 barre).
            streak_start_idx = found_idx
            for bi in range(found_idx - 1, -1, -1):
                if bool(active_series.iloc[bi]):
                    streak_start_idx = bi
                else:
                    break
            days_ago = (L - 1) - streak_start_idx

            p_signal = float(df_calc['Close'].iloc[streak_start_idx])

            p_yesterday = float(df_calc['Close'].iloc[-2]) if len(df_calc) >= 2 else p_current
            daily_var = ((p_current - p_yesterday) / p_yesterday) * 100.0 if p_yesterday != 0 else 0.0
            signal_var = ((p_current - p_signal) / p_signal) * 100.0 if p_signal != 0 else 0.0

            # Il tipo di pattern mostrato dipende dal pattern selezionato.
            # Solo per S2_or_S3 mostriamo la combinazione effettiva trovata nello stesso giorno.
            if pattern == "S2_or_S3":
                is_s2 = bool(s2_active_series.iloc[found_idx])
                is_s3 = bool(s3_active_series.iloc[found_idx])
                if is_s2 and is_s3:
                    pat_type = "S2 & S3"
                elif is_s2:
                    pat_type = "S2"
                elif is_s3:
                    pat_type = "S3"
                else:
                    pat_type = pattern
            else:
                # Standalone: il tipo corrisponde esattamente al pattern scelto (o la label del custom pattern)
                pat_type = get_pattern_label(pattern)


            # Calcolo PCTV storici per compatibilità WatchlistCard
            def get_pct_change(days):
                if len(df_calc) >= days + 1:
                    p_prev = float(df_calc['Close'].iloc[-1 - days])
                    return ((p_current - p_prev) / p_prev) * 100.0 if p_prev != 0 else 0.0
                return 0.0
                
            pctv_5d = get_pct_change(5)
            pctv_10d = get_pct_change(10)
            pctv_30d = get_pct_change(30)
            pctv_180d = get_pct_change(180)

            # ── Distanza dai massimi del periodo (1 anno) ─────────────────────────
            # Dist_From_High: quanto % il prezzo è sotto il massimo annuo.
            #   0%  = ai massimi (rischio alto)
            #   -20% = 20% sotto i massimi (potenziale upside)
            # Range_Pct: posizione percentuale (0–100) nell'intervallo min-max 1Y.
            #   100% = ai massimi · 0% = ai minimi
            has_high_col = 'High' in df_calc.columns
            has_low_col  = 'Low' in df_calc.columns
            if has_high_col and has_low_col:
                high_1y = float(df_calc['High'].max())
                low_1y  = float(df_calc['Low'].min())
            else:
                high_1y = float(df_calc['Close'].max())
                low_1y  = float(df_calc['Close'].min())
            dist_from_high = ((p_current - high_1y) / high_1y * 100.0) if high_1y != 0 else 0.0
            rng = high_1y - low_1y
            range_pct = ((p_current - low_1y) / rng * 100.0) if rng > 0 else 50.0

            # Calcolo segnale Alligator e Trend fittizi ma sensati
            has_sma200 = 'SMA200' in row_t and not pd.isna(row_t['SMA200'])
            above_sma = p_current > float(row_t['SMA200']) if has_sma200 else True
            alligator_sig = "Uptrend" if above_sma else "Downtrend"

            macd_val = float(row_t['MACD']) if 'MACD' in row_t and not pd.isna(row_t['MACD']) else 0.0
            macd_sig = float(df_calc['MACD_Signal'].iloc[-1]) if 'MACD_Signal' in df_calc.columns else 0.0
            macd_vs_sig = 1.0 if macd_val > macd_sig else -1.0

            sar_val = float(row_t['SAR']) if 'SAR' in row_t and not pd.isna(row_t['SAR']) else p_current
            sarma = 1.0 if p_current > sar_val else -1.0

            tech_score = 50.0
            if 'RSI' in row_t and not pd.isna(row_t['RSI']):
                tech_score = float(row_t['RSI'])
                
            return {
                "Ticker": ticker,
                "Close": p_current,
                "RSI": float(row_t['RSI']) if 'RSI' in row_t and not pd.isna(row_t['RSI']) else None,
                "Stoch_K": float(row_t['Stoch_K']) if 'Stoch_K' in row_t and not pd.isna(row_t['Stoch_K']) else None,
                "Stoch_D": float(row_t['Stoch_D']) if 'Stoch_D' in row_t and not pd.isna(row_t['Stoch_D']) else None,
                "Williams_R": float(row_t['Williams_R']) if 'Williams_R' in row_t and not pd.isna(row_t['Williams_R']) else None,
                "MACD": float(row_t['MACD']) if 'MACD' in row_t and not pd.isna(row_t['MACD']) else None,
                "ADX": float(row_t['ADX']) if 'ADX' in row_t and not pd.isna(row_t['ADX']) else None,
                "SAR": float(row_t['SAR']) if 'SAR' in row_t and not pd.isna(row_t['SAR']) else None,
                "SMA200": float(row_t['SMA200']) if 'SMA200' in row_t and not pd.isna(row_t['SMA200']) else None,
                "Pattern_Days_Ago": int(days_ago),
                "Signal_Var_Pct": float(signal_var),
                "Daily_Var_Pct": float(daily_var),
                "Is_Daily_Var": (days_ago == 0),
                "Pattern_Type": pat_type,
                
                # Campi per WatchlistCard
                "PCTV_1D": float(daily_var),
                "PCTV_5D": float(pctv_5d),
                "PCTV_10D": float(pctv_10d),
                "PCTV_30D": float(pctv_30d),
                "PCTV_180D": float(pctv_180d),
                "TECH_SCORE": tech_score,
                "SIG_MA_SAR": sarma,
                "Signal6": alligator_sig,
                "Signal6_Trend_Days": 2,
                "Liquidity": "OK",
                "Action": "BUY",
                "Market_Phase": "UPTREND" if above_sma else "PULLBACK",
                "Volume": float(row_t['Volume']) if 'Volume' in row_t and not pd.isna(row_t['Volume']) else 0.0,
                "PLUS_DI": float(row_t['PLUS_DI']) if 'PLUS_DI' in row_t and not pd.isna(row_t['PLUS_DI']) else 0.0,
                "MINUS_DI": float(row_t['MINUS_DI']) if 'MINUS_DI' in row_t and not pd.isna(row_t['MINUS_DI']) else 0.0,
                "MACD_Signal": macd_sig,
                "MACD_Hist": float(row_t['MACD_Hist']) if 'MACD_Hist' in row_t and not pd.isna(row_t['MACD_Hist']) else 0.0,
                "MACDH_Trend": "Up" if macd_vs_sig > 0 else "Down",
                "RSI_Trend": "Up" if tech_score > 50 else "Down",
                "EMA_30": float(row_t['SMA200']) if has_sma200 else p_current, # fallback simple
                "EMA_50": float(row_t['SMA200']) if has_sma200 else p_current,
                "SAR_Above_Price": not above_sma,
                "Trend_Stop_Level": sar_val,
                "CE_Long": sar_val,
                "Pullback_Stop_Level": None,
                "Pullback_Entry_Level": None,
                "Pullback_Entry_Zone_Low": None,
                "Pullback_Entry_Zone_High": None,
                "Pullback_Entry_Note": "",
                "Pullback_Invalidation": False,
                "Profit_Protect_Level": None,
                "SL1_RiskPct": 0.0,
                "SL2_RiskPct": 0.0,
                "MACD_vs_Signal": macd_vs_sig,
                # ── Posizione rispetto ai massimi del periodo 1Y ──────────────────
                "Dist_From_High": round(dist_from_high, 2),  # negativo: % sotto il massimo 1Y
                "Range_Pct": round(range_pct, 1),            # 0–100%: posizione nel range 1Y
                "High_1Y": round(high_1y, 4),
                "Low_1Y": round(low_1y, 4),
            }
    except Exception as e:
        print(f"Errore nella scansione di {ticker}: {e}")
        
    return None


def get_market_tickers(market: str) -> Tuple[List[str], List[str]]:
    """
    Ritorna la lista dei ticker e dei nomi per un determinato mercato.
    """
    fh = fileHandling(path=str(PROJECT_ROOT / "validTickersXLS") + "/")
    
    if market == "Preferite":
        return fh.PreferiteTickers, fh.PreferiteNames
    elif market == "US_Others":
        return fh.US_OthersTickers, fh.US_OthersNames
    elif market == "ETF":
        return fh.ETFTickers, fh.ETFNames
    elif market == "ETC":
        return fh.ETCTickers, fh.ETCNames
    elif market == "MIB30":
        return fh.MIB30Tickers, fh.MIB30Names
    elif market == "DAX":
        return fh.DAXTickers, fh.DAXNames
    
    # Prova a leggere da file Excel dinamici
    try:
        tickers, names = fh.getTickerList(market)
        if tickers:
            return tickers, names
    except Exception:
        pass
        
    return [], []


def scan_market_realtime(market: str, pattern: str = "S2", use_sar: bool = True, use_sma200: bool = False, lookback: int = 1) -> List[Dict[str, Any]]:
    """
    Scansiona l'intero mercato in parallelo scaricando i dati real-time con supporto lookback.
    """
    tickers, names = get_market_tickers(market)
    if not tickers:
        return []
        
    name_map = dict(zip(tickers, names))
    scanned_results = []
    
    # Esecuzione multithread
    max_workers = min(15, len(tickers))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(scan_single_ticker, t, pattern, use_sar, use_sma200, lookback): t 
            for t in tickers
        }
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                res = future.result()
                if res:
                    res["Name"] = name_map.get(ticker, ticker)
                    scanned_results.append(res)
            except Exception as exc:
                print(f"Il ticker {ticker} ha generato un'eccezione: {exc}")
                
    # Ordina i risultati per Ticker
    scanned_results.sort(key=lambda x: x["Ticker"])
    return scanned_results


def scan_market_realtime_streaming(
    markets_list: List[str],
    pattern: str = "S2",
    use_sar: bool = True,
    use_sma200: bool = False,
    lookback: int = 1,
):
    """
    Generator SSE: scansiona una lista di mercati emettendo eventi JSON man mano che i
    ticker vengono completati (compatible con StreamingResponse FastAPI).

    Ogni evento ha la forma:
      data: <json>\\n\\n

    Tipi di evento:
      {"type": "market_start", "market": str, "total": int}
      {"type": "result",   "data": dict, "done": int, "total": int, "market": str}
      {"type": "progress", "done": int, "total": int, "market": str}
      {"type": "done"}
    """
    import json as _json

    for mkt in markets_list:
        tickers, names = get_market_tickers(mkt)
        if not tickers:
            continue

        name_map = dict(zip(tickers, names))
        total = len(tickers)
        done = 0

        yield f"data: {_json.dumps({'type': 'market_start', 'market': mkt, 'total': total})}\n\n"

        max_workers = min(15, total)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(scan_single_ticker, t, pattern, use_sar, use_sma200, lookback): t
                for t in tickers
            }
            for future in concurrent.futures.as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                done += 1
                try:
                    res = future.result()
                    if res:
                        res["Name"] = name_map.get(ticker, ticker)
                        res["Market"] = mkt
                        yield f"data: {_json.dumps({'type': 'result', 'data': res, 'done': done, 'total': total, 'market': mkt})}\n\n"
                    else:
                        yield f"data: {_json.dumps({'type': 'progress', 'done': done, 'total': total, 'market': mkt})}\n\n"
                except Exception as exc:
                    print(f"[SSE SCANNER] {ticker} eccezione: {exc}")
                    yield f"data: {_json.dumps({'type': 'progress', 'done': done, 'total': total, 'market': mkt})}\n\n"

    yield f"data: {_json.dumps({'type': 'done'})}\n\n"


def scan_market(market: str, pattern: str = "S2", use_sar: bool = True, use_sma200: bool = False, lookback: int = 1) -> List[Dict[str, Any]]:
    """
    Scansiona il mercato caricando i dati pre-calcolati dall'Excel salvato ogni 20 minuti da main.py.
    Se l'Excel non è disponibile o mancano le colonne dei pattern, esegue il fallback in tempo reale.
    """
    pattern_mapping = {
        "custom_rsi_oversold": "S5",
        "custom_golden_cross": "S6",
        "custom_bullish_alligator": "S7",
        "custom_volume_breakout": "S8"
    }
    mapped_pattern = pattern_mapping.get(pattern, pattern)

    if mapped_pattern not in ["S2", "S3", "S4", "S5", "S6", "S7", "S8", "Combined", "S2_or_S3"]:
        # È un pattern personalizzato reale, esegui direttamente la scansione in tempo reale
        return scan_market_realtime(market, pattern, use_sar, use_sma200, lookback)

    from app.services.watchlist_service import load_market_dataframe, prepare_dataframe
    try:
        # Carica il DataFrame dall'Excel analyses/<MARKET>_TA_Analyses.xlsx
        df = load_market_dataframe(market)
        df = prepare_dataframe(df)
        
        # Verifica se le colonne precalcolate dei pattern sono presenti
        if mapped_pattern == "S2_or_S3":
            required = ['Pattern_S2_Days_Ago', 'Pattern_S3_Days_Ago', 'SAR_Filter_Ok', 'SMA200_Filter_Ok']
        else:
            days_ago_col = f"Pattern_{mapped_pattern}_Days_Ago"
            required = [days_ago_col, 'SAR_Filter_Ok', 'SMA200_Filter_Ok']
            
        if not all(col in df.columns for col in required):
            raise KeyError(f"Colonne pre-calcolate dei pattern sperimentali non trovate nell'Excel.")
            
    except Exception as exc:
        print(f"[SCANNER] Impossibile usare l'Excel precalcolato per {market} ({exc}). Eseguo scansione in tempo reale...")
        return scan_market_realtime(market, pattern, use_sar, use_sma200, lookback)

    # Filtra il DataFrame locale in base al pattern selezionato e al lookback
    if mapped_pattern == "S2_or_S3":
        df_filtered = df[(df['Pattern_S2_Days_Ago'] <= (lookback - 1)) | (df['Pattern_S3_Days_Ago'] <= (lookback - 1))]
    else:
        df_filtered = df[df[days_ago_col] <= (lookback - 1)]

    # Filtri Ausiliari
    if use_sar:
        df_filtered = df_filtered[df_filtered['SAR_Filter_Ok'] == 1]
    if use_sma200:
        df_filtered = df_filtered[df_filtered['SMA200_Filter_Ok'] == 1]

    # Prepara la lista dei risultati da restituire alla GUI in parallelo
    def _process_row(row):
        # Calcola o mappa i valori con pulizia float per serializzazione JSON sicura
        def _clean(val):
            if pd.isna(val):
                return None
            try:
                f = float(val)
                if np.isinf(f) or np.isnan(f):
                    return None
                return f
            except (ValueError, TypeError):
                return None

        def _clean_str(val):
            if pd.isna(val):
                return None
            return str(val)

        def _clean_bool(val):
            if pd.isna(val):
                return None
            try:
                return bool(val)
            except Exception:
                return None

        ticker = str(row.get("Ticker", ""))
        
        if mapped_pattern == "S2_or_S3":
            days_s2 = int(row.get("Pattern_S2_Days_Ago", 999)) if not pd.isna(row.get("Pattern_S2_Days_Ago")) else 999
            days_s3 = int(row.get("Pattern_S3_Days_Ago", 999)) if not pd.isna(row.get("Pattern_S3_Days_Ago")) else 999
            days_ago = min(days_s2, days_s3)
            
            matched_s2 = days_s2 <= (lookback - 1)
            matched_s3 = days_s3 <= (lookback - 1)
            if matched_s2 and matched_s3:
                pat_type = "S2 & S3"
            elif matched_s2:
                pat_type = "S2"
            elif matched_s3:
                pat_type = "S3"
            else:
                pat_type = "None"
        else:
            days_ago_col = f"Pattern_{mapped_pattern}_Days_Ago"
            days_ago = int(row.get(days_ago_col, 999)) if not pd.isna(row.get(days_ago_col)) else 999
            pat_type = get_pattern_label(pattern)
        
        # ── Fast path: usa i valori già presenti nell'Excel pre-calcolato da main.py ──
        # PCTV_1D = variazione % rispetto a ieri, già calcolata da main.py → nessuna
        # chiamata a Yahoo Finance necessaria.
        daily_var_pct = float(row.get("PCTV_1D") or 0.0)

        # Signal_Var_Pct: variazione dal giorno del segnale ad oggi.
        # Se days_ago combacia con una delle colonne PCTV già disponibili, la usiamo
        # direttamente; altrimenti approssimiamo con la più vicina.
        signal_var_pct = 0.0
        if days_ago not in (999, 0):
            pctv_map = {
                1:  float(row.get("PCTV_1D")  or 0.0),
                5:  float(row.get("PCTV_5D")  or 0.0),
                10: float(row.get("PCTV_10D") or 0.0),
                30: float(row.get("PCTV_30D") or 0.0),
            }
            if days_ago in pctv_map:
                signal_var_pct = pctv_map[days_ago]
            else:
                # Approssima con la colonna PCTV più vicina per giorni_ago
                nearest_key = min(pctv_map.keys(), key=lambda k: abs(k - days_ago))
                signal_var_pct = pctv_map[nearest_key]

        return {
            "Ticker": ticker,
            "Name": str(row.get("Name", "")),
            "Close": _clean(row.get("Close", 0.0)) or 0.0,
            "RSI": _clean(row.get("RSI")),
            "Stoch_K": _clean(row.get("Stoch_K")),
            "Stoch_D": _clean(row.get("Stoch_D")),
            "Williams_R": _clean(row.get("Williams_R")),
            "MACD": _clean(row.get("MACD")),
            "ADX": _clean(row.get("ADX")),
            "SAR": _clean(row.get("SAR")),
            "SMA200": _clean(row.get("SMA200")),
            "Pattern_Days_Ago": days_ago,
            "Signal_Var_Pct": float(signal_var_pct),
            "Daily_Var_Pct": float(daily_var_pct),
            "Is_Daily_Var": (days_ago == 0),
            "Pattern_Type": pat_type,
            
            # WatchlistCard additions
            "PCTV_1D": float(daily_var_pct), # keep it updated live
            "PCTV_5D": _clean(row.get("PCTV_5D")),
            "PCTV_10D": _clean(row.get("PCTV_10D")),
            "PCTV_30D": _clean(row.get("PCTV_30D")),
            "PCTV_180D": _clean(row.get("PCTV_180D")),
            "TECH_SCORE": _clean(row.get("TECH_SCORE")),
            "SIG_MA_SAR": _clean(row.get("SIG_MA_SAR")),
            "Signal6": _clean_str(row.get("Signal6")),
            "Signal6_Trend_Days": _clean(row.get("Signal6_Trend_Days")),
            "Liquidity": _clean_str(row.get("Liquidity")),
            "Action": _clean_str(row.get("Action")),
            "Market_Phase": _clean_str(row.get("Market_Phase")),
            "Trend_Phase_Detail": _clean_str(row.get("Trend_Phase_Detail")),
            "Volume": _clean(row.get("Volume")),
            "PLUS_DI": _clean(row.get("PLUS_DI")),
            "MINUS_DI": _clean(row.get("MINUS_DI")),
            "MACD_Signal": _clean(row.get("MACD_Signal")),
            "MACD_Hist": _clean(row.get("MACD_Hist")),
            "MACDH_Trend": _clean_str(row.get("MACDH_Trend")),
            "RSI_Trend": _clean_str(row.get("RSI_Trend")),
            "EMA_30": _clean(row.get("EMA_30")),
            "EMA_50": _clean(row.get("EMA_50")),
            "SAR_Above_Price": _clean_bool(row.get("SAR_Above_Price")),
            "Trend_Stop_Level": _clean(row.get("Trend_Stop_Level")),
            "CE_Long": _clean(row.get("CE_Long")),
            "Pullback_Stop_Level": _clean(row.get("Pullback_Stop_Level")),
            "Pullback_Entry_Level": _clean(row.get("Pullback_Entry_Level")),
            "Pullback_Entry_Zone_Low": _clean(row.get("Pullback_Entry_Zone_Low")),
            "Pullback_Entry_Zone_High": _clean(row.get("Pullback_Entry_Zone_High")),
            "Pullback_Entry_Note": _clean_str(row.get("Pullback_Entry_Note")),
            "Pullback_Invalidation": _clean_bool(row.get("Pullback_Invalidation")),
            "Profit_Protect_Level": _clean(row.get("Profit_Protect_Level")),
            "SL1_RiskPct": _clean(row.get("SL1_RiskPct")),
            "SL2_RiskPct": _clean(row.get("SL2_RiskPct")),
            "MACD_vs_Signal": _clean(row.get("MACD_vs_Signal")),
        }

    scanned_results = [_process_row(row) for _, row in df_filtered.iterrows()]

    # Ordina i risultati per Ticker
    scanned_results.sort(key=lambda x: x["Ticker"])
    return scanned_results


def run_vectorbt_backtest(
    ticker: str,
    pattern: str,
    use_sar: bool = True,
    use_sma200: bool = False,
    init_cash: float = 10000.0,
    fees: float = 0.001
) -> Dict[str, Any]:
    """
    Esegue la simulazione storica vectorbt a 2 anni sul ticker e genera metriche e report locale.
    """
    df_hist = get_historical_data(ticker, period="2y")
    if df_hist.empty or len(df_hist) < 50:
        raise ValueError("Dati storici insufficienti per il backtesting.")
        
    df_calc = calculate_all_indicators(df_hist, use_adjusted=False)
    df_clean = df_calc.dropna(subset=['Close', 'SAR']).copy()
    if len(df_clean) < 10:
        raise ValueError("Indicatori calcolati insufficienti per il backtesting.")
        
    # Costruisci espressioni logiche dei segnali
    custom_query = get_pattern_rule(pattern)
    if custom_query:
        pattern_rule = custom_query
    else:
        pattern_conditions = []
        if pattern in ["S2", "Combined", "S2_or_S3"]:
            pattern_conditions.append(
                "(Stoch_K > Stoch_D) & (Stoch_K > 20) & "
                "(Williams_R > -80) & (Williams_R > Williams_R_shift1) & "
                "(((Stoch_K > 20) & (Stoch_K_shift1 <= 20)) | "
                "((Stoch_K > Stoch_D) & (Stoch_K_shift1 <= Stoch_D_shift1)) | "
                "((Williams_R > -80) & (Williams_R_shift1 <= -80))) & "
                "(Stoch_K_shift1 < 35)"
            )
        if pattern in ["S3", "Combined", "S2_or_S3"]:
            pattern_conditions.append(
                "(MACD > MACD_Signal) & (MACD_shift1 <= MACD_Signal_shift1) & (MACD > MACD_shift1) & "
                "(MACD_Hist > 0) & (MACD_Hist > MACD_Hist_shift1)"
            )
        if pattern == "S4":
            pattern_conditions.append(
                "(EMA_9 > EMA_21) & "
                "(RSI >= 55) & (RSI <= 70) & (RSI > RSI_shift1) & "
                "(MACD > MACD_Signal) & "
                "(Volume > Volume_MA20 * 1.5)"
            )
        if pattern == "S5":
            pattern_conditions.append(
                "(RSI < 30) & (Stoch_K > Stoch_D) & (Stoch_K_shift1 <= Stoch_D_shift1)"
            )
        if pattern == "S6":
            pattern_conditions.append(
                "(EMA_30 > EMA_50) & (EMA_30_shift1 <= EMA_50_shift1) & (ADX > 25)"
            )
        if pattern == "S7":
            pattern_conditions.append("(Alligator_Bull_Trigger == True)")
        if pattern == "S8":
            pattern_conditions.append("(Close > Open) & (Volume > Volume_MA20 * 1.5)")
            
        if not pattern_conditions:
            pattern_rule = "(Close > 0)"
        elif pattern == "Combined":
            pattern_rule = " & ".join(pattern_conditions)
        elif pattern == "S2_or_S3":
            pattern_rule = " | ".join(f"({c})" for c in pattern_conditions)
        else:
            pattern_rule = pattern_conditions[0]
        
    buy_conditions = [f"({pattern_rule})"]
    if use_sar:
        buy_conditions.append("(Close > SAR)")
    if use_sma200 and 'SMA200' in df_clean.columns:
        buy_conditions.append("(Close > SMA200)")
        
    buy_rule = " & ".join(buy_conditions)
    sell_rule = "(Close < SAR)"  # standard exit su inversione Parabolic SAR
    
    # Valuta espressioni
    try:
        buy_mask = df_clean.eval(buy_rule).astype(bool)
    except Exception as e:
        raise ValueError(f"Errore nella valutazione delle regole di BUY: {e}")
        
    try:
        sell_mask = df_clean.eval(sell_rule).astype(bool)
    except Exception as e:
        raise ValueError(f"Errore nella valutazione delle regole di SELL: {e}")
        
    # VectorBT
    if not VECTORBT_AVAILABLE:
        raise ImportError(
            "vectorbt non è installato su questo sistema (es. Raspberry Pi ARM). "
            "Il backtest quantitativo non è disponibile su questo dispositivo."
        )
    pf = vbt.Portfolio.from_signals(
        close=df_clean['Close'],
        entries=buy_mask,
        exits=sell_mask,
        init_cash=init_cash,
        fees=fees,
        freq="1d"
    )
    
    stats = pf.stats()
    
    start_date = stats.get("Start", "N/A")
    start_str = start_date.strftime('%Y-%m-%d') if hasattr(start_date, "strftime") else str(start_date)
    end_date = stats.get("End", "N/A")
    end_str = end_date.strftime('%Y-%m-%d') if hasattr(end_date, "strftime") else str(end_date)
    
    period_val = stats.get("Period", 0)
    duration_days = int(period_val.days) if hasattr(period_val, "days") else 0
    
    def _clean_val(v: Any) -> float:
        if pd.isna(v):
            return 0.0
        try:
            f = float(v)
            if np.isnan(f) or np.isinf(f):
                return 0.0
            return f
        except (ValueError, TypeError):
            return 0.0

    metrics = {
        "Start Date": start_str,
        "End Date": end_str,
        "Duration (days)": duration_days,
        "Initial Capital": _clean_val(stats.get("Start Value", init_cash)),
        "End Value": _clean_val(stats.get("End Value", init_cash)),
        "Total Return (%)": _clean_val(stats.get("Total Return [%]", 0.0)),
        "Benchmark Return (%)": _clean_val(stats.get("Benchmark Return [%]", 0.0)),
        "Max Drawdown (%)": _clean_val(stats.get("Max Drawdown [%]", 0.0)),
        "Total Trades": int(stats.get("Total Trades", 0)) if not pd.isna(stats.get("Total Trades")) else 0,
        "Win Rate (%)": _clean_val(stats.get("Win Rate [%]", 0.0)),
        "Sharpe Ratio": _clean_val(stats.get("Sharpe Ratio", 0.0)),
        "Sortino Ratio": _clean_val(stats.get("Sortino Ratio", 0.0)),
        "Profit Factor": _clean_val(stats.get("Profit Factor", 0.0)),
        "Expectancy": _clean_val(stats.get("Expectancy", 0.0)),
        "Signal Today": "🟢 ACQUISTO (BUY)" if bool(buy_mask.iloc[-1]) else ("🔴 VENDITA (SELL)" if bool(sell_mask.iloc[-1]) else "NEUTRALE (Attesa)"),
        "Ticker": ticker,
        "Pattern": pattern
    }
    
    commentary = generate_financial_commentary(metrics, pattern, buy_rule, sell_rule)
    
    return {
        "metrics": metrics,
        "commentary": commentary,
        "buy_rule": buy_rule,
        "sell_rule": sell_rule
    }


def generate_financial_commentary(metrics: Dict[str, Any], pattern: str, buy_rule: str, sell_rule: str) -> str:
    """
    Genera un report finanziario analitico in italiano ad altissima fedeltà.
    """
    ticker = metrics.get("Ticker", "N/A")
    total_return = metrics.get("Total Return (%)", 0.0)
    bench_return = metrics.get("Benchmark Return (%)", 0.0)
    sharpe = metrics.get("Sharpe Ratio", 0.0)
    drawdown = metrics.get("Max Drawdown (%)", 0.0)
    trades = metrics.get("Total Trades", 0)
    win_rate = metrics.get("Win Rate (%)", 0.0)
    profit_factor = metrics.get("Profit Factor", 0.0)
    
    lines = [
        f"### 🔬 Analisi Quantitativa - Pattern **{pattern}** su **{ticker}**",
        "",
        "#### 📊 Sintesi delle Performance Storiche (Orizzonte 2 Anni)",
        f"- **Rendimento Strategia Sperimentale**: **{total_return:+.2f}%** (Capitale Finale: €{metrics.get('End Value', 10000.0):,.2f})",
        f"- **Rendimento Benchmark (Buy & Hold)**: {bench_return:+.2f}%",
        f"- **Operazioni Concluse**: {trades} trade totali con un **Win Rate** del **{win_rate:.2f}%**",
        f"- **Profit Factor (Fattore Profitto)**: {profit_factor:.2f}" if trades > 0 else "- **Profit Factor**: N.D. (nessuna operazione conclusa)",
        "",
        "#### ⚠️ Profilo del Rischio e Drawdown",
        f"- **Sharpe Ratio (Indice di Efficienza)**: **{sharpe:.2f}**",
        f"- **Massimo Drawdown Storico**: **{drawdown:+.2f}%**",
        "",
        "#### 🔍 Considerazioni Tecnico-Analitiche",
    ]
    
    if total_return > bench_return:
        lines.append(f"- **Outperformance**: La strategia ha generato **alfa positivo**, battendo il mercato (Buy & Hold) con un guadagno differenziale di **{(total_return - bench_return):+.2f}%**.")
    else:
        lines.append(f"- **Underperformance**: Il trading attivo non ha generato benefici rispetto a una strategia passiva di Buy & Hold (differenza di **{(total_return - bench_return):+.2f}%**).")
        
    if sharpe > 1.0:
        lines.append("- **Efficienza Elevata**: L'indice di Sharpe superiore a 1.0 riflette un'eccellente ottimizzazione tra rendimenti generati e volatilità sopportata storicamente.")
    elif 0.5 <= sharpe <= 1.0:
        lines.append("- **Efficienza Moderata**: Il profilo rischio/rendimento è accettabile, ma sono possibili miglioramenti regolando le soglie dello Stocastico o del Williams %R.")
    else:
        lines.append("- **Efficienza Insufficiente**: L'efficienza del rischio è bassa (Sharpe < 0.5). Il trade-off non giustifica l'assunzione del rischio operativo.")
        
    if drawdown < -20.0 or drawdown > 20.0:
        lines.append(f"- **Esposizione al Rischio Elevata**: Il drawdown massimo di {drawdown:.2f}% è severo. Si suggerisce di testare uno stop loss dinamico basato sull'ATR invece del solo stop su SAR.")
    else:
        lines.append(f"- **Rischio Contenuto**: La perdita massima tollerata del {drawdown:.2f}% è controllata e rientra nei parametri standard.")

    lines.append("\n#### 💡 Verdetto Finale dell'Agente AI")
    if total_return > 0 and sharpe >= 0.7:
        lines.append("🟢 **CONSIGLIATA**: Il pattern sperimentale mostra un timing solido e redditizio. Strategia pronta per essere considerata all'interno del paniere principale.")
    elif total_return > 0:
        lines.append("实时 **MONITORARE**: Guadagno totale positivo, ma profilo di rischio (Sharpe) o drawdown migliorabili. Consigliabile tarare i lookback degli oscillatori.")
    else:
        lines.append("🔴 **NON CONSIGLIATA**: La strategia quantitativa soffre di rumore nei segnali o di stop loss prematuri. Si consiglia una profonda revisione del pattern di ingresso.")
        
    return "\n".join(lines)
