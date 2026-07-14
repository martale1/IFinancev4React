
import talib
import yfinance as yf
import numpy as np
import re
import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional, Dict
from typing import Optional

#import vectorbt as vbt
from utils import (
    build_conditions,
    create_conditions_from_json
)

OUTPUT_FILENAME = "TA_Analyses.xlsx"


class TechnicalAnalyzer:

    def __init__(self, ticker, period="2y", cache_hours: float = 0.25, use_cache: bool = True):
        """
        Inizializza l'analizzatore tecnico con un ticker e un periodo storico

        Args:
            ticker (str): Simbolo del ticker (es. "AAPL")
            period (str): Periodo storico (formato yfinance, es. "1y", "6mo", "max")
            cache_hours (float): Tempo di validità della cache in ore. Default 0.25 (15 minuti).
            use_cache (bool): Se True, abilita il salvataggio e caricamento della cache su disco.
        """
        self.ticker = ticker
        self.tickerName=None
        self.period = period
        self.cache_hours = cache_hours
        self.use_cache = use_cache
        self.dataframe = None
        self.macd_params = {'fastperiod': 12, 'slowperiod': 26, 'signalperiod': 9}
        self.ma_params = {'timeperiod': 20, 'matype': 0}
        self.rsi_period = 14
        self.williams_period = 14  # Aggiunto qui per essere sicuri
        self.stoch_params = {'fastk_period': 14, 'slowk_period': 3, 'slowd_period': 3}
        self.alligator_params = {'jaw_period': 13, 'teeth_period': 8, 'lips_period': 5,
                                 'shift_jaw': 8, 'shift_teeth': 5, 'shift_lips': 3}
        self.pctv_periods = {
            'PCTV_1D': 1,
            'PCTV_5D': 5,
            'PCTV_10D': 10,
            'PCTV_30D': 30,
            'PCTV_180D': 180
        }
        self.sar_params = {'acceleration': 0.02, 'maximum': 0.2}

        self.adx_period = 14
        self.atr_period = 14
        self.atr_multiplier = 3.0  # per bande ATR / Chandelier
        self.atr_lookback = 22  # lookback per Chandelier Exit
        # --- Liquidity params (filtri volumi) ---
        self.liq_params = getattr(self, "liq_params", {
            "ma_period": 20,  # MA dei volumi
            "window": 30,  # finestra diagnostica
            "low_vol_cut": 200,  # “very low” (giorni sotto questa soglia)
            "warn_threshold": 8_000,  # sotto → LOW
            "low_threshold": 2_000,  # sotto → candidato AVOID (se altri segnali concordano)
            "spike_ratio_max": 15.0  # max/mean nella finestra: sopra → spike anomali
        })


        self.download_data()

    def add_trading_layers_statev3(
            self,
            *,
            inplace: bool = True,

            # -------- Layer1 --------
            macd_buy_max_days: int = 2,
            adx_min: int = 20,
            rsi_buy_min: int = 50,
            rsi_sell_max: int = 50,
            tech_score_buy_min: int = 65,
            tech_score_sell_max: int = 35,

            # -------- Layer2 --------
            layer2_adx_strong_min: int = 25,
            layer2_adx_weak_max: int = 20,
            layer2_rsi_bull_min: int = 55,
            layer2_rsi_bear_max: int = 45,
            layer2_vol_bull_min: float = 0,
            layer2_vol_bear_max: float = -40,
            stoch_overbought: float = 80,
            stoch_oversold: float = 20,
            layer2_strong_bull_min_score: int = 5,
            layer2_bull_min_score: int = 3,
            layer2_strong_bear_max_score: int = -5,
            layer2_bear_max_score: int = -3,

            # -------- Layer3 --------
            atr_high_vol_threshold: float = 3,
            fresh_signal_max_days: int = 2,
            mature_momentum_min_days: int = 5,
    ):
        """
        Replica 1:1 del tuo compute_layers_on_df (stesse regole e parametri):
          - Layer1_Action
          - Layer2_Score
          - Layer2_Label
          - Trading_State
          - Layer3_Warning
        """
        import pandas as pd

        df = self.dataframe
        if df is None or df.empty:
            return df

        out = df if inplace else df.copy()

        # ---- helper stoch compatibile con nomi diversi ----
        def _get_stoch_values(row: pd.Series):
            candidates_k = ["STOCH_K", "Stoch_K", "stoch_k", "STOCHk", "stochK", "Stochastic_K"]
            candidates_d = ["STOCH_D", "Stoch_D", "stoch_d", "STOCHd", "stochD", "Stochastic_D"]
            k = next((row.get(c) for c in candidates_k if c in row.index), None)
            d = next((row.get(c) for c in candidates_d if c in row.index), None)
            try:
                k = float(k) if k is not None else None
                d = float(d) if d is not None else None
            except Exception:
                return None, None
            return k, d

        # COSTANTI (uguali al tuo script)
        LIQ_OK = "OK"
        ADX_BULL = "Bullish"
        ADX_BEAR = "Bearish"

        DI_PLUS = "PLUS_DI"
        DI_MINUS = "MINUS_DI"

        MACD_VS_SIGNAL = "MACD_vs_Signal"
        MACD_SELL_VALUE = -1

        MACDH_TREND = "MACDH_Trend"
        MACDH_UP = "Up"
        MACDH_DOWN = "Down"

        RSI = "RSI"
        RSI_TREND = "RSI_Trend"
        RSI_UP = "Up"
        RSI_DOWN = "Down"

        CLOSE = "Close"
        EMA_FAST = "EMA_30"
        EMA_SLOW = "EMA_50"

        SAR_ABOVE = "SAR_Above_Price"
        TECH_SCORE = "TECH_SCORE"

        VOL_VS_MA20 = "Vol_Perc_vs_MA20"

        ATR_PCT = "ATR_PCT"
        MACDH_TREND_DAYS = "MACDH_Trend_Days"
        RSI_TREND_DAYS = "RSI_Trend_Days"

        # -------------------------
        # LAYER 1 (IDENTICO)
        # -------------------------
        def compute_layer1(row: pd.Series) -> str:
            try:
                if row.get("Liquidity") != LIQ_OK:
                    return "WAIT"

                plus_di = row.get(DI_PLUS, 0)
                minus_di = row.get(DI_MINUS, 0)
                macd_vs_signal = row.get(MACD_VS_SIGNAL, 0)

                close = row.get(CLOSE, 0)
                ema_fast = row.get(EMA_FAST, 0)
                ema_slow = row.get(EMA_SLOW, 0)

                sar_above = row.get(SAR_ABOVE, None)
                tech = row.get(TECH_SCORE, 0)
                adx = row.get("ADX", 0)
                rsi = row.get(RSI, 50)

                # BUY
                if (
                        adx >= adx_min and
                        row.get("ADX_Trend") == ADX_BULL and
                        plus_di > minus_di and
                        0 < macd_vs_signal < macd_buy_max_days and
                        row.get(MACDH_TREND) == MACDH_UP and
                        rsi >= rsi_buy_min and
                        row.get(RSI_TREND) == RSI_UP and
                        close > ema_fast and close > ema_slow and
                        sar_above is False and
                        tech >= tech_score_buy_min
                ):
                    return "BUY"

                # SELL
                if (
                        adx >= adx_min and
                        row.get("ADX_Trend") == ADX_BEAR and
                        minus_di > plus_di and
                        macd_vs_signal == MACD_SELL_VALUE and
                        row.get(MACDH_TREND) == MACDH_DOWN and
                        rsi <= rsi_sell_max and
                        row.get(RSI_TREND) == RSI_DOWN and
                        close < ema_fast and close < ema_slow and
                        sar_above is True and
                        tech <= tech_score_sell_max
                ):
                    return "SELL"

                return "HOLD"
            except Exception:
                return "HOLD"

        out["Layer1_Action"] = out.apply(compute_layer1, axis=1)

        # -------------------------
        # LAYER 2 (IDENTICO)
        # -------------------------
        def compute_layer2_score(row: pd.Series) -> int:
            score = 0

            adx = row.get("ADX", 0)
            score += 1 if adx >= layer2_adx_strong_min else -1 if adx < layer2_adx_weak_max else 0

            plus_di = row.get(DI_PLUS, 0)
            minus_di = row.get(DI_MINUS, 0)
            score += 1 if plus_di > minus_di else -1

            score += 1 if row.get(MACDH_TREND) == MACDH_UP else -1

            rsi = row.get(RSI, 50)
            score += 1 if rsi > layer2_rsi_bull_min else -1 if rsi < layer2_rsi_bear_max else 0

            v = row.get(VOL_VS_MA20, 0)
            score += 1 if v > layer2_vol_bull_min else -1 if v < layer2_vol_bear_max else 0

            close = row.get(CLOSE, 0)
            ema_fast = row.get(EMA_FAST, 0)
            ema_slow = row.get(EMA_SLOW, 0)
            score += 1 if (close > ema_fast and close > ema_slow) else -1

            k, d = _get_stoch_values(row)
            if k is None or d is None:
                stoch_component = 0
            else:
                if k > d and k < stoch_overbought:
                    stoch_component = +1
                elif k < d and k > stoch_oversold:
                    stoch_component = -1
                else:
                    stoch_component = 0

            score += stoch_component
            return int(score)

        def label_layer2(score: int) -> str:
            if score >= layer2_strong_bull_min_score:
                return "Strong Bull"
            if score >= layer2_bull_min_score:
                return "Bull"
            if score <= layer2_strong_bear_max_score:
                return "Strong Bear"
            if score <= layer2_bear_max_score:
                return "Bear"
            return "Neutral"

        out["Layer2_Score"] = out.apply(compute_layer2_score, axis=1)
        out["Layer2_Label"] = out["Layer2_Score"].apply(label_layer2)

        # -------------------------
        # TRADING STATE (IDENTICO)
        # -------------------------
        def compute_trading_state(row: pd.Series) -> str:
            if row["Layer1_Action"] in ["BUY", "SELL"]:
                return "ENTER"
            if row["Layer1_Action"] == "WAIT":
                return "WAIT"
            if row["Layer1_Action"] == "HOLD" and row["Layer2_Label"] in ["Bull", "Strong Bull"]:
                return "PREPARE"
            return "HOLD"

        out["Trading_State"] = out.apply(compute_trading_state, axis=1)

        # -------------------------
        # LAYER 3 (IDENTICO)
        # -------------------------
        def compute_layer3_warning(row: pd.Series) -> str:
            warnings = []

            if row.get(ATR_PCT, 0) > atr_high_vol_threshold:
                warnings.append("High Volatility")

            if row.get(MACDH_TREND_DAYS, 99) <= fresh_signal_max_days:
                warnings.append("Fresh Signal")

            if row.get(RSI_TREND_DAYS, 0) > mature_momentum_min_days:
                warnings.append("Mature Momentum")

            k, d = _get_stoch_values(row)
            if k is not None and d is not None:
                if k < stoch_oversold:
                    warnings.append("Stoch Oversold")
                if k > stoch_overbought:
                    warnings.append("Stoch Overbought")
                if k < stoch_oversold and k > d:
                    warnings.append("Stoch Rebound (Oversold)")
                if k > stoch_overbought and k < d:
                    warnings.append("Stoch Reversal (Overbought)")

            return ", ".join(warnings) if warnings else "OK"

        out["Layer3_Warning"] = out.apply(compute_layer3_warning, axis=1)

        if not inplace:
            self.dataframe = out
        return out

    def add_trading_statev4_v1(
            self,
            *,
            inplace: bool = True,

            # -------- Action (clear) --------
            macd_buy_max_days: int = 10,  # freshness window for BUY
            adx_min: int = 20,
            rsi_buy_min: int = 45,
            rsi_sell_max: int = 50,
            tech_score_buy_min: int = 65,
            tech_score_sell_max: int = 35,

            # -------- Phase thresholds --------
            adx_strong_min: int = 25,
            adx_weak_max: int = 20,
            rsi_range_low: int = 45,
            rsi_range_high: int = 55,
            stoch_overbought: float = 80,
            stoch_oversold: float = 20,

            # -------- BREAKOUT (STRICT) --------
            breakout_lookback: int = 20,  # recent-high window
            breakout_buffer_pct: float = 0.003,  # 0.3% above recent high
            breakout_adx_min: float = 25,  # must be strong
            breakout_require_adx_slope_pos: bool = True,
            breakout_require_macd_hist_rising: bool = True,
            breakout_vol_bull_min: float = 0,  # Vol_Perc_vs_MA20 > 0 preferred
            breakout_require_not_overbought: bool = True,
            breakout_use_signal6: bool = True,

            # -------- Layer3 (same as v3) --------
            atr_high_vol_threshold: float = 3,
            fresh_signal_max_days: int = 2,
            mature_momentum_min_days: int = 5,

            # -------- NEW Action categories tuning --------
            action_add_requires_adx: int = 25,  # stronger than normal
            action_reduce_on_overbought: bool = True,
            action_exit_on_structure_break: bool = True,

            # -------- NEW: Pullback entry/stop levels --------
            pullback_zone_atr_low: float = 0.50,  # EMA30 - 0.50*ATR
            pullback_zone_atr_high: float = 0.25,  # EMA30 + 0.25*ATR
            pullback_stop_atr_buffer: float = 0.00,  # EMA50 - buffer*ATR
            pullback_require_above_ema50: bool = True,

            # -------- NEW: Trend stop (BUY+ADD in UPTREND) --------
            trend_stop_atr_buffer: float = 0.00,  # EMA50 - buffer*ATR
            # -------- NEW: Profit protect (REDUCE in UPTREND) --------
            profit_protect_atr_buffer: float = 0.25,  # EMA30 - 0.25*ATR (più stretto)
            profit_protect_use_sar: bool = True,  # se True usa max(EMA30-buffer*ATR, SAR) per trailing

    ):
        """
        v4 (updated): Clear output model with MORE action categories
        + v2/v3: adds operational levels:
          - Pullback levels (entry zone + stop ref)
          - Trend stop levels for BUY/ADD in UPTREND

        Outputs:
          - Action: WAIT / AVOID / BUY / SELL / ADD / REDUCE / EXIT / HOLD
          - Market_Phase: BREAKOUT / UPTREND / PULLBACK / RANGE / DOWNTREND / REVERSAL_RISK
          - Layer3_Warning
          - Action_Reason

        Added columns:
          Pullback_* (only meaningful when Market_Phase=PULLBACK):
            - Pullback_Entry_Level
            - Pullback_Entry_Zone_Low
            - Pullback_Entry_Zone_High
            - Pullback_Stop_Level
            - Pullback_Invalidation
            - Pullback_Entry_Note

          Trend_Stop_* (only when Market_Phase=UPTREND and Action in {BUY,ADD}):
            - Trend_Stop_Level
            - Trend_Stop_Invalidation
            - Trend_Stop_Type
        """
        import pandas as pd
        import numpy as np

        df = self.dataframe
        if df is None or df.empty:
            return df

        out = df if inplace else df.copy()

        # -------------------------
        # helpers
        # -------------------------
        def _txt(row: pd.Series, col: str, default: str = "") -> str:
            v = row.get(col, default)
            return "" if v is None else str(v)

        def _boolish(x):
            if isinstance(x, (bool, np.bool_)):
                return bool(x)
            if x is None:
                return None
            s = str(x).strip().lower()
            if s in ("true", "1", "yes", "y"):
                return True
            if s in ("false", "0", "no", "n"):
                return False
            return None

        def _num(row: pd.Series, col: str, default: float = 0.0) -> float:
            v = row.get(col, default)
            try:
                v = pd.to_numeric(v, errors="coerce")
                if pd.isna(v):
                    return float(default)
                return float(v)
            except Exception:
                return float(default)

        # ---- helper stoch compatible with different names ----
        def _get_stoch_values(row: pd.Series):
            candidates_k = ["STOCH_K", "Stoch_K", "stoch_k", "STOCHk", "stochK", "Stochastic_K"]
            candidates_d = ["STOCH_D", "Stoch_D", "stoch_d", "STOCHd", "stochD", "Stochastic_D"]
            k = next((row.get(c) for c in candidates_k if c in row.index), None)
            d = next((row.get(c) for c in candidates_d if c in row.index), None)
            try:
                k = float(k) if k is not None else None
                d = float(d) if d is not None else None
            except Exception:
                return None, None
            return k, d

        # -------------------------
        # column names / constants
        # -------------------------
        LIQ_OK = "OK"
        LIQ_AVOID = "AVOID"
        ADX_BULL = "Bullish"
        ADX_BEAR = "Bearish"

        DI_PLUS = "PLUS_DI"
        DI_MINUS = "MINUS_DI"

        MACD_VS_SIGNAL = "MACD_vs_Signal"
        MACD_SELL_VALUE = -1

        MACDH_TREND = "MACDH_Trend"
        MACDH_UP = "Up"
        MACDH_DOWN = "Down"

        RSI = "RSI"
        RSI_TREND = "RSI_Trend"
        RSI_UP = "Up"
        RSI_DOWN = "Down"

        CLOSE = "Close"
        EMA_FAST = "EMA_30"
        EMA_SLOW = "EMA_50"
        HIGH = "High"

        SAR_ABOVE = "SAR_Above_Price"
        TECH_SCORE = "TECH_SCORE"

        VOL_VS_MA20 = "Vol_Perc_vs_MA20"

        ATR = "ATR"
        ATR_PCT = "ATR_PCT"
        MACDH_TREND_DAYS = "MACDH_Trend_Days"
        RSI_TREND_DAYS = "RSI_Trend_Days"

        # -------------------------
        # PRECOMPUTATIONS (vectorized) for STRICT BREAKOUT
        # -------------------------
        if HIGH in out.columns:
            recent_high = (
                pd.to_numeric(out[HIGH], errors="coerce")
                    .rolling(breakout_lookback, min_periods=max(3, breakout_lookback // 3))
                    .max()
                    .shift(1)
            )
        else:
            recent_high = (
                pd.to_numeric(out[CLOSE], errors="coerce")
                    .rolling(breakout_lookback, min_periods=max(3, breakout_lookback // 3))
                    .max()
                    .shift(1)
            )
        out["__recent_high"] = recent_high

        if "ADX" in out.columns:
            adx_series = pd.to_numeric(out["ADX"], errors="coerce")
            out["__adx_slope"] = adx_series.diff()
        else:
            out["__adx_slope"] = np.nan

        if "MACD_Hist" in out.columns:
            mh = pd.to_numeric(out["MACD_Hist"], errors="coerce")
            out["__macd_hist_rising"] = mh.diff() > 0
        else:
            out["__macd_hist_rising"] = False

        if VOL_VS_MA20 in out.columns:
            out["__vol_vs_ma20"] = pd.to_numeric(out[VOL_VS_MA20], errors="coerce").fillna(0.0)
        else:
            out["__vol_vs_ma20"] = 0.0

        # -------------------------
        # Market Phase (strict breakout + your rules)
        # -------------------------
        def compute_market_phase(row: pd.Series) -> str:
            close = _num(row, CLOSE, 0)
            ema30 = _num(row, EMA_FAST, 0)
            ema50 = _num(row, EMA_SLOW, 0)

            adx = _num(row, "ADX", 0)
            plus_di = _num(row, DI_PLUS, 0)
            minus_di = _num(row, DI_MINUS, 0)

            macdh_trend = _txt(row, MACDH_TREND, "").strip()
            sar_above = _boolish(row.get(SAR_ABOVE, None))
            sar_bull = (sar_above is False)
            sar_bear = (sar_above is True)

            rsi = _num(row, RSI, 50)
            rsi_trend = _txt(row, RSI_TREND, "").strip()

            macd_vs_signal = _num(row, MACD_VS_SIGNAL, 0)
            vol_vs_ma20 = _num(row, "__vol_vs_ma20", 0)
            recent_high_val = pd.to_numeric(row.get("__recent_high", np.nan), errors="coerce")
            adx_slope = _num(row, "__adx_slope", 0)
            macd_hist_rising = bool(row.get("__macd_hist_rising", False))

            k, d = _get_stoch_values(row)

            trend_up = (close > ema30) and (ema30 > ema50)
            trend_down = (close < ema30) and (ema30 < ema50)

            di_up = plus_di > minus_di
            di_down = minus_di > plus_di

            adx_strong = adx >= adx_strong_min
            adx_weak = adx < adx_weak_max

            macd_up = (macdh_trend == MACDH_UP)
            macd_down = (macdh_trend == MACDH_DOWN)

            fresh_momentum = (macd_vs_signal > 0) and (macd_vs_signal <= macd_buy_max_days)

            # -------- 1) BREAKOUT (STRICT) --------
            breaks_recent_high = False
            if pd.notna(recent_high_val) and recent_high_val > 0:
                breaks_recent_high = close > (float(recent_high_val) * (1.0 + breakout_buffer_pct))

            not_overbought = True
            if breakout_require_not_overbought and (k is not None):
                not_overbought = k < stoch_overbought

            s6_ok = True
            if breakout_use_signal6 and ("Signal6" in row.index):
                s6 = _txt(row, "Signal6", "").lower()
                s6_ok = ("wakeup" in s6) or (s6 in ("uptrend", "uptrend*")) or ("uptrend*" in s6)

            adx_ok = adx >= breakout_adx_min
            adx_slope_ok = (adx_slope > 0) if breakout_require_adx_slope_pos else True
            macd_hist_ok = (macd_hist_rising is True) if breakout_require_macd_hist_rising else True
            vol_ok = vol_vs_ma20 > breakout_vol_bull_min

            if (breaks_recent_high and fresh_momentum and adx_ok and adx_slope_ok and macd_hist_ok
                    and vol_ok and not_overbought and s6_ok and (not trend_down)):
                return "BREAKOUT"

            # -------- 2) REVERSAL_RISK --------
            rev_risk = False
            if trend_up and di_down:
                rev_risk = True
            if trend_down and di_up:
                rev_risk = True
            if trend_up and (close < ema50):
                rev_risk = True
            if trend_down and (close > ema50):
                rev_risk = True
            if "Signal6" in row.index:
                s6 = _txt(row, "Signal6", "").lower()
                if "rev" in s6 or "reversal" in s6:
                    rev_risk = True
            if rev_risk:
                return "REVERSAL_RISK"

            # -------- 3) UPTREND --------
            if trend_up and di_up and (adx_strong or macd_up) and sar_bull:
                return "UPTREND"

            # -------- 4) DOWNTREND --------
            if trend_down and di_down and (adx_strong or macd_down) and sar_bear:
                return "DOWNTREND"

            # -------- 5) PULLBACK --------
            #if (ema30 > ema50) and (close > ema50) and (adx >= adx_min) and (plus_di >= minus_di):

            if (ema30 > ema50) and (close > ema50):
                pullback_votes = 0
                if (rsi < 50) or (rsi_trend == RSI_DOWN):
                    pullback_votes += 1
                if k is not None and d is not None:
                    if (k < d) or (k < 40):
                        pullback_votes += 1
                if macd_down:
                    pullback_votes += 1
                if (close < ema30):
                    pullback_votes += 1
                if pullback_votes >= 2:
                    return "PULLBACK"

            # -------- 6) RANGE --------
            if adx_weak and (rsi_range_low <= rsi <= rsi_range_high) and (not trend_up) and (not trend_down):
                return "RANGE"

            return "RANGE"

        out["Market_Phase"] = out.apply(compute_market_phase, axis=1)
        ###QUI
        # ============================================================
        # Trend Phase Detail - maggiore granularità per UPTREND / BUY
        # ============================================================

        def compute_trend_phase_detail(row: pd.Series) -> str:
            """
            Classifica meglio la fase del trend, soprattutto quando Market_Phase=UPTREND.

            Output possibili:
            - EARLY_TREND
            - EXPANSION
            - MATURE_TREND
            - OVEREXTENDED
            - UPTREDING_COOLING
            - PULLBACK_HEALTHY
            - PULLBACK_RISKY
            - BREAKOUT_FRESH
            - RANGE
            - DOWNTREND
            - REVERSAL_RISK
            """

            phase = _txt(row, "Market_Phase", "RANGE").strip().upper()

            close = _num(row, CLOSE, 0)
            ema30 = _num(row, EMA_FAST, 0)
            ema50 = _num(row, EMA_SLOW, 0)

            adx = _num(row, "ADX", 0)
            plus_di = _num(row, DI_PLUS, 0)
            minus_di = _num(row, DI_MINUS, 0)

            macd_vs_signal = _num(row, MACD_VS_SIGNAL, 999)
            macdh_trend = _txt(row, MACDH_TREND, "").strip()
            macdh_days = _num(row, MACDH_TREND_DAYS, 999)

            rsi = _num(row, RSI, 50)
            rsi_trend = _txt(row, RSI_TREND, "").strip()
            rsi_days = _num(row, RSI_TREND_DAYS, 0)

            atr_pct = _num(row, ATR_PCT, 0)

            k, d = _get_stoch_values(row)

            dist_ema30_pct = 0
            if ema30 > 0:
                dist_ema30_pct = ((close - ema30) / ema30) * 100

            dist_ema50_pct = 0
            if ema50 > 0:
                dist_ema50_pct = ((close - ema50) / ema50) * 100

            stoch_overbought_flag = k is not None and k >= stoch_overbought
            stoch_oversold_flag = k is not None and k <= stoch_oversold
            stoch_turning_down = k is not None and d is not None and k < d
            stoch_rebound = k is not None and d is not None and k > d and k < 40

            bullish_structure = close > ema30 > ema50
            bullish_di = plus_di > minus_di
            bearish_di = minus_di > plus_di

            # -------------------------
            # Non bullish phases
            # -------------------------
            if phase == "BREAKOUT":
                if macd_vs_signal <= 3 and macdh_days <= 3:
                    return "BREAKOUT_FRESH"
                return "BREAKOUT_EXTENDED"

            if phase == "DOWNTREND":
                return "DOWNTREND"

            if phase == "REVERSAL_RISK":
                return "REVERSAL_RISK"

            if phase == "RANGE":
                return "RANGE"

            # -------------------------
            # Pullback details
            # -------------------------
            if phase == "PULLBACK":
                if close > ema50 and plus_di >= minus_di:
                    if stoch_oversold_flag or stoch_rebound:
                        return "PULLBACK_HEALTHY"
                    return "PULLBACK_NORMAL"
                return "PULLBACK_RISKY"

            # -------------------------
            # Uptrend details
            # -------------------------
            if phase == "UPTREND":

                # 1) UPTREDING_COOLING / weakening
                if (
                        bearish_di
                        or macdh_trend == MACDH_DOWN
                        or (stoch_overbought_flag and stoch_turning_down)
                ):
                    return "UPTREDING_COOLING"

                # 2) OVEREXTENDED
                if (
                        stoch_overbought_flag
                        or atr_pct > atr_high_vol_threshold
                        or dist_ema30_pct > 6
                        or dist_ema50_pct > 12
                ):
                    return "OVEREXTENDED"

                # 3) EARLY TREND
                if (
                        bullish_structure
                        and bullish_di
                        and macdh_trend == MACDH_UP
                        and macd_vs_signal <= 3
                        and macdh_days <= 3
                        and rsi_trend == RSI_UP
                        and rsi_days <= 4
                        and dist_ema30_pct <= 4
                ):
                    return "EARLY_TREND"

                # 4) EXPANSION
                if (
                        bullish_structure
                        and bullish_di
                        and macdh_trend == MACDH_UP
                        and macd_vs_signal <= 10
                        and macdh_days <= 10
                        and rsi_days <= 10
                        and atr_pct <= atr_high_vol_threshold
                ):
                    return "EXPANSION"

                # 5) MATURE TREND
                if (
                        bullish_structure
                        and bullish_di
                        and (
                        macdh_days > 10
                        or rsi_days > 10
                        or macd_vs_signal > 10
                )
                ):
                    return "MATURE_TREND"

                return "UPTREND_GENERIC"

            return "UNKNOWN"

        out["Trend_Phase_Detail"] = out.apply(compute_trend_phase_detail, axis=1)
        # ============================================================
        # Pullback entry zone + stop reference (vectorized)
        # ============================================================
        close_s = pd.to_numeric(out.get(CLOSE, np.nan), errors="coerce")
        ema30_s = pd.to_numeric(out.get(EMA_FAST, np.nan), errors="coerce")
        ema50_s = pd.to_numeric(out.get(EMA_SLOW, np.nan), errors="coerce")

        atr_s = pd.to_numeric(out.get(ATR, np.nan), errors="coerce")
        if atr_s.isna().all():
            atr_pct_s = pd.to_numeric(out.get(ATR_PCT, np.nan), errors="coerce")
            atr_s = (atr_pct_s / 100.0) * close_s



        phase_s = out["Market_Phase"].astype(str).str.upper()
        is_pullback = phase_s.eq("PULLBACK")
        if pullback_require_above_ema50:
            is_pullback = is_pullback & (close_s > ema50_s)

        # =====================================================
        # Pullback entry zone (EMA30 vs CE_Long -> use MAX)
        # =====================================================
        ce_long_s = pd.to_numeric(out.get("CE_Long", np.nan), errors="coerce")

        # entry = max(EMA30, CE_Long)
        entry_level = np.fmax(ema30_s, ce_long_s)

        zone_low = entry_level - (pullback_zone_atr_low * atr_s)
        zone_high = entry_level + (pullback_zone_atr_high * atr_s)

        stop_level_pb = ema50_s - (pullback_stop_atr_buffer * atr_s)
        invalidation_pb = is_pullback & (close_s < stop_level_pb)

        out["Pullback_Entry_Level"] = np.where(is_pullback, entry_level, np.nan)
        out["Pullback_Entry_Zone_Low"] = np.where(is_pullback, zone_low, np.nan)
        out["Pullback_Entry_Zone_High"] = np.where(is_pullback, zone_high, np.nan)
        out["Pullback_Stop_Level"] = np.where(is_pullback, stop_level_pb, np.nan)
        out["Pullback_Invalidation"] = np.where(is_pullback, invalidation_pb, np.nan)

        note = np.full(len(out), "", dtype=object)
        in_zone = is_pullback & (close_s >= zone_low) & (close_s <= zone_high)
        above_zone = is_pullback & (close_s > zone_high)
        below_zone = is_pullback & (close_s < zone_low)

        note[in_zone] = "IN_ZONE (limit-friendly)"
        note[above_zone] = "ABOVE_ZONE (wait/confirm)"
        note[below_zone] = "BELOW_ZONE (too deep / caution)"
        note[invalidation_pb.values] = "INVALIDATED (below stop)"

        out["Pullback_Entry_Note"] = note

        # -------------------------
        # Action (your logic)
        # -------------------------
        def compute_action_and_reason(row: pd.Series):
            liq = _txt(row, "Liquidity", "").strip().upper()

            # explicit avoid
            if liq == LIQ_AVOID:
                return "AVOID", "Liquidity=AVOID"

            # wait for anything not OK (includes LOW, missing, etc.)
            if liq != LIQ_OK:
                return "WAIT", f"Liquidity={liq or 'N/A'}"

            phase = _txt(row, "Market_Phase", "RANGE").strip().upper()

            close = _num(row, CLOSE, 0)
            ema30 = _num(row, EMA_FAST, 0)
            ema50 = _num(row, EMA_SLOW, 0)

            adx = _num(row, "ADX", 0)
            plus_di = _num(row, DI_PLUS, 0)
            minus_di = _num(row, DI_MINUS, 0)

            macd_vs_signal = _num(row, MACD_VS_SIGNAL, 0)
            macdh_trend = _txt(row, MACDH_TREND, "").strip()
            rsi = _num(row, RSI, 50)
            rsi_trend = _txt(row, RSI_TREND, "").strip()
            adx_trend = _txt(row, "ADX_Trend", "").strip()

            sar_above = _boolish(row.get(SAR_ABOVE, None))
            tech = _num(row, TECH_SCORE, 0)

            # risk flags used for REDUCE/EXIT decisions
            atr_pct = _num(row, ATR_PCT, 0)
            k, d = _get_stoch_values(row)
            stoch_overb = (k is not None and k >= stoch_overbought)
            stoch_overs = (k is not None and k <= stoch_oversold)

            structure_break_bull = (ema30 > ema50) and (close < ema50)  # bullish structure broken

            # -------- STRICT triggers --------
            # SELL first (protective)
            if phase in ["DOWNTREND", "REVERSAL_RISK"]:
                if (
                        adx >= adx_min and
                        adx_trend == ADX_BEAR and
                        minus_di > plus_di and
                        macd_vs_signal == MACD_SELL_VALUE and
                        macdh_trend == MACDH_DOWN and
                        rsi <= rsi_sell_max and
                        rsi_trend == RSI_DOWN and
                        close < ema30 and close < ema50 and
                        (sar_above is True) and
                        tech <= tech_score_sell_max
                ):
                    return "SELL", "Strict SELL trigger"

            # BUY
            if phase in ["BREAKOUT", "UPTREND", "PULLBACK"]:
                if (
                        adx >= adx_min and
                        adx_trend == ADX_BULL and
                        plus_di > minus_di and
                        0 < macd_vs_signal <= macd_buy_max_days and
                        macdh_trend == MACDH_UP and
                        rsi >= rsi_buy_min and
                        rsi_trend == RSI_UP and
                        close > ema30 and close > ema50 and
                        (sar_above is False) and
                        tech >= tech_score_buy_min
                ):
                    return "BUY", "Strict BUY trigger"

            # -------- NEW categories --------
            if phase == "DOWNTREND":
                return "EXIT", "Phase=DOWNTREND"

            if phase == "REVERSAL_RISK":
                if close > ema50:
                    return "REDUCE", "Phase=REVERSAL_RISK (still above EMA50)"
                return "EXIT", "Phase=REVERSAL_RISK (below EMA50)"

            if action_exit_on_structure_break and structure_break_bull:
                return "EXIT", "Bull structure broken (Close < EMA50)"

            # REDUCE: bullish structure but risk flags
            if phase in ["UPTREND", "BREAKOUT", "PULLBACK"] and (close > ema50):
                if action_reduce_on_overbought and stoch_overb:
                    return "REDUCE", "Overbought (Stoch >= 80)"
                if atr_pct > atr_high_vol_threshold:
                    return "REDUCE", f"High volatility (ATR_PCT>{atr_high_vol_threshold})"

            # ADD: good bullish structure but not strict BUY
            bullish_quality = (
                    (phase in ["BREAKOUT", "UPTREND"]) and
                    (plus_di > minus_di) and
                    (adx >= action_add_requires_adx) and
                    (close > ema50)
            )
            if bullish_quality:
                return "ADD", "Bullish quality (phase+DI+ADX) but not strict BUY"

            # ADD on pullback: bullish structure + oversold/rebound hints
            if phase == "PULLBACK" and (ema30 > ema50) and (close > ema50) and (plus_di >= minus_di):
                if stoch_overs or (k is not None and d is not None and k > d and k < 40):
                    return "ADD", "Pullback add (bull structure + stoch rebound)"

            return "HOLD", "No trigger"

        action_reason = out.apply(compute_action_and_reason, axis=1, result_type="expand")
        out["Action"] = action_reason[0]
        out["Action_Reason"] = action_reason[1]

        # =====================================================
        # Trend Stop (AFTER Action to avoid KeyError)
        # =====================================================
        action_s = out["Action"].astype(str).str.upper()
        phase_s2 = out["Market_Phase"].astype(str).str.upper()

        is_trend_trade = (phase_s2.eq("UPTREND")) & (action_s.isin(["BUY", "ADD"]))

        stop_level_trend = ema50_s - (trend_stop_atr_buffer * atr_s)

        out["Trend_Stop_Level"] = np.where(is_trend_trade, stop_level_trend, np.nan)
        out["Trend_Stop_Invalidation"] = np.where(is_trend_trade, close_s < stop_level_trend, np.nan)
        out["Trend_Stop_Type"] = np.where(is_trend_trade, "STRUCTURE_EMA50", "")
        # =====================================================
        # Profit Protect (ONLY for REDUCE in UPTREND)
        # =====================================================
        is_reduce_trade = (phase_s2.eq("UPTREND")) & (action_s.eq("REDUCE"))

        # base: EMA30 - buffer*ATR (tight)
        protect_level = ema30_s - (profit_protect_atr_buffer * atr_s)

        # opzionale: trailing più aggressivo usando SAR (se disponibile)
        if profit_protect_use_sar and ("SAR" in out.columns):
            sar_s = pd.to_numeric(out["SAR"], errors="coerce")
            # per un long: stop “protettivo” = max(EMA30-buffer*ATR, SAR)
            protect_level = np.fmax(protect_level, sar_s)

        out["Profit_Protect_Level"] = np.where(is_reduce_trade, protect_level, np.nan)
        out["Profit_Protect_Invalidation"] = np.where(is_reduce_trade, close_s < protect_level, np.nan)
        out["Profit_Protect_Type"] = np.where(
            is_reduce_trade,
            "TIGHT_EMA30_ATR" + ("_PLUS_SAR" if (profit_protect_use_sar and ("SAR" in out.columns)) else ""),
            ""
        )


        # -------------------------
        # Layer3 Warnings (same as v3)
        # -------------------------
        def compute_layer3_warning(row: pd.Series) -> str:
            warnings = []

            if _num(row, ATR_PCT, 0) > atr_high_vol_threshold:
                warnings.append("High Volatility")

            if _num(row, MACDH_TREND_DAYS, 99) <= fresh_signal_max_days:
                warnings.append("Fresh Signal")

            if _num(row, RSI_TREND_DAYS, 0) > mature_momentum_min_days:
                warnings.append("Mature Momentum")

            k, d = _get_stoch_values(row)
            if k is not None and d is not None:
                if k < stoch_oversold:
                    warnings.append("Stoch Oversold")
                if k > stoch_overbought:
                    warnings.append("Stoch Overbought")
                if k < stoch_oversold and k > d:
                    warnings.append("Stoch Rebound (Oversold)")
                if k > stoch_overbought and k < d:
                    warnings.append("Stoch Reversal (Overbought)")

            return ", ".join(warnings) if warnings else "OK"

        out["Layer3_Warning"] = out.apply(compute_layer3_warning, axis=1)

        # cleanup temp cols
        for c in ["__recent_high", "__adx_slope", "__macd_hist_rising", "__vol_vs_ma20"]:
            if c in out.columns:
                out.drop(columns=[c], inplace=True)

        if not inplace:
            self.dataframe = out
        return out

    def add_trading_statev4_v11(
            #era version v1 senza entry price per pullback
            self,
            *,
            inplace: bool = True,

            # -------- Action (clear) --------
            macd_buy_max_days: int = 10,  # freshness window for BUY
            adx_min: int = 20,
            rsi_buy_min: int = 45,
            rsi_sell_max: int = 50,
            tech_score_buy_min: int = 65,
            tech_score_sell_max: int = 35,

            # -------- Phase thresholds --------
            adx_strong_min: int = 25,
            adx_weak_max: int = 20,
            rsi_range_low: int = 45,
            rsi_range_high: int = 55,
            stoch_overbought: float = 80,
            stoch_oversold: float = 20,

            # -------- BREAKOUT (STRICT) --------
            breakout_lookback: int = 20,  # recent-high window
            breakout_buffer_pct: float = 0.003,  # 0.3% above recent high
            breakout_adx_min: float = 25,  # must be strong
            breakout_require_adx_slope_pos: bool = True,
            breakout_require_macd_hist_rising: bool = True,
            breakout_vol_bull_min: float = 0,  # Vol_Perc_vs_MA20 > 0 preferred
            breakout_require_not_overbought: bool = True,
            breakout_use_signal6: bool = True,

            # -------- Layer3 (same as v3) --------
            atr_high_vol_threshold: float = 3,
            fresh_signal_max_days: int = 2,
            mature_momentum_min_days: int = 5,

            # -------- NEW Action categories tuning --------
            action_add_requires_adx: int = 25,  # stronger than normal
            action_reduce_on_overbought: bool = True,
            action_exit_on_structure_break: bool = True,
    ):
        """
        v4 (updated): Clear output model with MORE action categories

        Outputs:
          - Action: WAIT / AVOID / BUY / SELL / ADD / REDUCE / EXIT / HOLD
          - Market_Phase: BREAKOUT / UPTREND / PULLBACK / RANGE / DOWNTREND / REVERSAL_RISK
          - Layer3_Warning: unchanged
          - Action_Reason: short explain string (helps debugging)

        Notes on NEW actions (position-aware semantics, but computed statelessly):
          - ADD    : bullish environment but not strict BUY trigger (good for scaling-in)
          - REDUCE : bullish structure but risk flags (overbought / reversal risk / high vol)
          - EXIT   : structure breaks / bearish phase when not a strict SELL trigger
          - AVOID  : Liquidity == "AVOID" (explicit)
        """
        import pandas as pd
        import numpy as np

        df = self.dataframe
        if df is None or df.empty:
            return df

        out = df if inplace else df.copy()

        # -------------------------
        # helpers
        # -------------------------
        def _txt(row: pd.Series, col: str, default: str = "") -> str:
            v = row.get(col, default)
            return "" if v is None else str(v)

        def _boolish(x):
            if isinstance(x, (bool, np.bool_)):
                return bool(x)
            if x is None:
                return None
            s = str(x).strip().lower()
            if s in ("true", "1", "yes", "y"):
                return True
            if s in ("false", "0", "no", "n"):
                return False
            return None

        def _num(row: pd.Series, col: str, default: float = 0.0) -> float:
            v = row.get(col, default)
            try:
                v = pd.to_numeric(v, errors="coerce")
                if pd.isna(v):
                    return float(default)
                return float(v)
            except Exception:
                return float(default)

        # ---- helper stoch compatible with different names ----
        def _get_stoch_values(row: pd.Series):
            candidates_k = ["STOCH_K", "Stoch_K", "stoch_k", "STOCHk", "stochK", "Stochastic_K"]
            candidates_d = ["STOCH_D", "Stoch_D", "stoch_d", "STOCHd", "stochD", "Stochastic_D"]
            k = next((row.get(c) for c in candidates_k if c in row.index), None)
            d = next((row.get(c) for c in candidates_d if c in row.index), None)
            try:
                k = float(k) if k is not None else None
                d = float(d) if d is not None else None
            except Exception:
                return None, None
            return k, d

        # -------------------------
        # column names / constants
        # -------------------------
        LIQ_OK = "OK"
        LIQ_AVOID = "AVOID"
        ADX_BULL = "Bullish"
        ADX_BEAR = "Bearish"

        DI_PLUS = "PLUS_DI"
        DI_MINUS = "MINUS_DI"

        MACD_VS_SIGNAL = "MACD_vs_Signal"
        MACD_SELL_VALUE = -1

        MACDH_TREND = "MACDH_Trend"
        MACDH_UP = "Up"
        MACDH_DOWN = "Down"

        RSI = "RSI"
        RSI_TREND = "RSI_Trend"
        RSI_UP = "Up"
        RSI_DOWN = "Down"

        CLOSE = "Close"
        EMA_FAST = "EMA_30"
        EMA_SLOW = "EMA_50"
        HIGH = "High"

        SAR_ABOVE = "SAR_Above_Price"
        TECH_SCORE = "TECH_SCORE"

        VOL_VS_MA20 = "Vol_Perc_vs_MA20"

        ATR_PCT = "ATR_PCT"
        MACDH_TREND_DAYS = "MACDH_Trend_Days"
        RSI_TREND_DAYS = "RSI_Trend_Days"

        # -------------------------
        # PRECOMPUTATIONS (vectorized) for STRICT BREAKOUT
        # -------------------------
        if HIGH in out.columns:
            recent_high = (
                pd.to_numeric(out[HIGH], errors="coerce")
                    .rolling(breakout_lookback, min_periods=max(3, breakout_lookback // 3))
                    .max()
                    .shift(1)
            )
        else:
            recent_high = (
                pd.to_numeric(out[CLOSE], errors="coerce")
                    .rolling(breakout_lookback, min_periods=max(3, breakout_lookback // 3))
                    .max()
                    .shift(1)
            )
        out["__recent_high"] = recent_high

        if "ADX" in out.columns:
            adx_series = pd.to_numeric(out["ADX"], errors="coerce")
            out["__adx_slope"] = adx_series.diff()
        else:
            out["__adx_slope"] = np.nan

        if "MACD_Hist" in out.columns:
            mh = pd.to_numeric(out["MACD_Hist"], errors="coerce")
            out["__macd_hist_rising"] = mh.diff() > 0
        else:
            out["__macd_hist_rising"] = False

        if VOL_VS_MA20 in out.columns:
            out["__vol_vs_ma20"] = pd.to_numeric(out[VOL_VS_MA20], errors="coerce").fillna(0.0)
        else:
            out["__vol_vs_ma20"] = 0.0

        # -------------------------
        # Market Phase (same logic you provided, strict breakout)
        # -------------------------
        def compute_market_phase(row: pd.Series) -> str:
            close = _num(row, CLOSE, 0)
            ema30 = _num(row, EMA_FAST, 0)
            ema50 = _num(row, EMA_SLOW, 0)

            adx = _num(row, "ADX", 0)
            plus_di = _num(row, DI_PLUS, 0)
            minus_di = _num(row, DI_MINUS, 0)

            macdh_trend = _txt(row, MACDH_TREND, "").strip()
            sar_above = _boolish(row.get(SAR_ABOVE, None))
            sar_bull = (sar_above is False)
            sar_bear = (sar_above is True)

            rsi = _num(row, RSI, 50)
            rsi_trend = _txt(row, RSI_TREND, "").strip()

            macd_vs_signal = _num(row, MACD_VS_SIGNAL, 0)
            vol_vs_ma20 = _num(row, "__vol_vs_ma20", 0)
            recent_high_val = pd.to_numeric(row.get("__recent_high", np.nan), errors="coerce")
            adx_slope = _num(row, "__adx_slope", 0)
            macd_hist_rising = bool(row.get("__macd_hist_rising", False))

            k, d = _get_stoch_values(row)

            trend_up = (close > ema30) and (ema30 > ema50)
            trend_down = (close < ema30) and (ema30 < ema50)

            di_up = plus_di > minus_di
            di_down = minus_di > plus_di

            adx_strong = adx >= adx_strong_min
            adx_weak = adx < adx_weak_max

            macd_up = (macdh_trend == MACDH_UP)
            macd_down = (macdh_trend == MACDH_DOWN)

            fresh_momentum = (macd_vs_signal > 0) and (macd_vs_signal <= macd_buy_max_days)

            # -------- 1) BREAKOUT (STRICT) --------
            breaks_recent_high = False
            if pd.notna(recent_high_val) and recent_high_val > 0:
                breaks_recent_high = close > (float(recent_high_val) * (1.0 + breakout_buffer_pct))

            not_overbought = True
            if breakout_require_not_overbought and (k is not None):
                not_overbought = k < stoch_overbought

            s6_ok = True
            if breakout_use_signal6 and ("Signal6" in row.index):
                s6 = _txt(row, "Signal6", "").lower()
                s6_ok = ("wakeup" in s6) or (s6 in ("uptrend", "uptrend*")) or ("uptrend*" in s6)

            adx_ok = adx >= breakout_adx_min
            adx_slope_ok = (adx_slope > 0) if breakout_require_adx_slope_pos else True
            macd_hist_ok = (macd_hist_rising is True) if breakout_require_macd_hist_rising else True
            vol_ok = vol_vs_ma20 > breakout_vol_bull_min

            if (
                    breaks_recent_high and fresh_momentum and adx_ok and adx_slope_ok and macd_hist_ok
                    and vol_ok and not_overbought and s6_ok and (not trend_down)
            ):
                return "BREAKOUT"

            # -------- 2) REVERSAL_RISK --------
            rev_risk = False
            if trend_up and di_down:
                rev_risk = True
            if trend_down and di_up:
                rev_risk = True
            if trend_up and (close < ema50):
                rev_risk = True
            if trend_down and (close > ema50):
                rev_risk = True
            if "Signal6" in row.index:
                s6 = _txt(row, "Signal6", "").lower()
                if "rev" in s6 or "reversal" in s6:
                    rev_risk = True
            if rev_risk:
                return "REVERSAL_RISK"

            # -------- 3) UPTREND --------
            if trend_up and di_up and (adx_strong or macd_up) and sar_bull:
                return "UPTREND"

            # -------- 4) DOWNTREND --------
            if trend_down and di_down and (adx_strong or macd_down) and sar_bear:
                return "DOWNTREND"

            # -------- 5) PULLBACK --------
            if (ema30 > ema50) and (close > ema50):
                pullback_votes = 0
                if (rsi < 50) or (rsi_trend == RSI_DOWN):
                    pullback_votes += 1
                if k is not None and d is not None:
                    if (k < d) or (k < 40):
                        pullback_votes += 1
                if macd_down:
                    pullback_votes += 1
                if (close < ema30):
                    pullback_votes += 1
                if pullback_votes >= 2:
                    return "PULLBACK"

            # -------- 6) RANGE --------
            if adx_weak and (rsi_range_low <= rsi <= rsi_range_high) and (not trend_up) and (not trend_down):
                return "RANGE"

            return "RANGE"

        out["Market_Phase"] = out.apply(compute_market_phase, axis=1)

        # ============================================================
        # Trend Phase Detail - maggiore granularità per UPTREND / BUY
        # ============================================================

        def compute_trend_phase_detail(row: pd.Series) -> str:
            """
            Classifica meglio la fase del trend, soprattutto quando Market_Phase=UPTREND.

            Output possibili:
            - EARLY_TREND
            - EXPANSION
            - MATURE_TREND
            - OVEREXTENDED
            - UPTREDING_COOLING
            - PULLBACK_HEALTHY
            - PULLBACK_RISKY
            - BREAKOUT_FRESH
            - RANGE
            - DOWNTREND
            - REVERSAL_RISK
            """

            phase = _txt(row, "Market_Phase", "RANGE").strip().upper()

            close = _num(row, CLOSE, 0)
            ema30 = _num(row, EMA_FAST, 0)
            ema50 = _num(row, EMA_SLOW, 0)

            adx = _num(row, "ADX", 0)
            plus_di = _num(row, DI_PLUS, 0)
            minus_di = _num(row, DI_MINUS, 0)

            macd_vs_signal = _num(row, MACD_VS_SIGNAL, 999)
            macdh_trend = _txt(row, MACDH_TREND, "").strip()
            macdh_days = _num(row, MACDH_TREND_DAYS, 999)

            rsi = _num(row, RSI, 50)
            rsi_trend = _txt(row, RSI_TREND, "").strip()
            rsi_days = _num(row, RSI_TREND_DAYS, 0)

            atr_pct = _num(row, ATR_PCT, 0)

            k, d = _get_stoch_values(row)

            dist_ema30_pct = 0
            if ema30 > 0:
                dist_ema30_pct = ((close - ema30) / ema30) * 100

            dist_ema50_pct = 0
            if ema50 > 0:
                dist_ema50_pct = ((close - ema50) / ema50) * 100

            stoch_overbought_flag = k is not None and k >= stoch_overbought
            stoch_oversold_flag = k is not None and k <= stoch_oversold
            stoch_turning_down = k is not None and d is not None and k < d
            stoch_rebound = k is not None and d is not None and k > d and k < 40

            bullish_structure = close > ema30 > ema50
            bullish_di = plus_di > minus_di
            bearish_di = minus_di > plus_di

            # -------------------------
            # Non bullish phases
            # -------------------------
            if phase == "BREAKOUT":
                if macd_vs_signal <= 3 and macdh_days <= 3:
                    return "BREAKOUT_FRESH"
                return "BREAKOUT_EXTENDED"

            if phase == "DOWNTREND":
                return "DOWNTREND"

            if phase == "REVERSAL_RISK":
                return "REVERSAL_RISK"

            if phase == "RANGE":
                return "RANGE"

            # -------------------------
            # Pullback details
            # -------------------------
            if phase == "PULLBACK":
                if close > ema50 and plus_di >= minus_di:
                    if stoch_oversold_flag or stoch_rebound:
                        return "PULLBACK_HEALTHY"
                    return "PULLBACK_NORMAL"
                return "PULLBACK_RISKY"

            # -------------------------
            # Uptrend details
            # -------------------------
            if phase == "UPTREND":

                # 1) UPTREDING_COOLING / weakening
                if (
                        bearish_di
                        or macdh_trend == MACDH_DOWN
                        or (stoch_overbought_flag and stoch_turning_down)
                ):
                    return "UPTREDING_COOLING"

                # 2) OVEREXTENDED
                if (
                        stoch_overbought_flag
                        or atr_pct > atr_high_vol_threshold
                        or dist_ema30_pct > 6
                        or dist_ema50_pct > 12
                ):
                    return "OVEREXTENDED"

                # 3) EARLY TREND
                if (
                        bullish_structure
                        and bullish_di
                        and macdh_trend == MACDH_UP
                        and macd_vs_signal <= 3
                        and macdh_days <= 3
                        and rsi_trend == RSI_UP
                        and rsi_days <= 4
                        and dist_ema30_pct <= 4
                ):
                    return "EARLY_TREND"

                # 4) EXPANSION
                if (
                        bullish_structure
                        and bullish_di
                        and macdh_trend == MACDH_UP
                        and macd_vs_signal <= 10
                        and macdh_days <= 10
                        and rsi_days <= 10
                        and atr_pct <= atr_high_vol_threshold
                ):
                    return "EXPANSION"

                # 5) MATURE TREND
                if (
                        bullish_structure
                        and bullish_di
                        and (
                        macdh_days > 10
                        or rsi_days > 10
                        or macd_vs_signal > 10
                )
                ):
                    return "MATURE_TREND"

                return "UPTREND_GENERIC"

            return "UNKNOWN"

        out["Trend_Phase_Detail"] = out.apply(compute_trend_phase_detail, axis=1)
        # -------------------------
        # Action (UPDATED: adds ADD / REDUCE / EXIT / AVOID)
        # -------------------------
        def compute_action_and_reason(row: pd.Series):
            liq = _txt(row, "Liquidity", "").strip().upper()

            # explicit avoid
            if liq == LIQ_AVOID:
                return "AVOID", "Liquidity=AVOID"

            # wait for anything not OK (includes LOW, missing, etc.)
            if liq != LIQ_OK:
                return "WAIT", f"Liquidity={liq or 'N/A'}"

            phase = _txt(row, "Market_Phase", "RANGE").strip().upper()

            close = _num(row, CLOSE, 0)
            ema30 = _num(row, EMA_FAST, 0)
            ema50 = _num(row, EMA_SLOW, 0)

            adx = _num(row, "ADX", 0)
            plus_di = _num(row, DI_PLUS, 0)
            minus_di = _num(row, DI_MINUS, 0)

            macd_vs_signal = _num(row, MACD_VS_SIGNAL, 0)
            macdh_trend = _txt(row, MACDH_TREND, "").strip()
            rsi = _num(row, RSI, 50)
            rsi_trend = _txt(row, RSI_TREND, "").strip()
            adx_trend = _txt(row, "ADX_Trend", "").strip()

            sar_above = _boolish(row.get(SAR_ABOVE, None))
            tech = _num(row, TECH_SCORE, 0)

            # risk flags used for REDUCE/EXIT decisions
            atr_pct = _num(row, ATR_PCT, 0)
            k, d = _get_stoch_values(row)
            stoch_overb = (k is not None and k >= stoch_overbought)
            stoch_overs = (k is not None and k <= stoch_oversold)

            trend_up = (close > ema30) and (ema30 > ema50)
            trend_down = (close < ema30) and (ema30 < ema50)
            structure_break_bull = (ema30 > ema50) and (close < ema50)  # bullish structure broken
            structure_break_bear = (ema30 < ema50) and (close > ema50)

            # -------- STRICT triggers (same as your v3 logic, but phase-gated) --------
            # SELL first (protective)
            if phase in ["DOWNTREND", "REVERSAL_RISK"]:
                if (
                        adx >= adx_min and
                        adx_trend == ADX_BEAR and
                        minus_di > plus_di and
                        macd_vs_signal == MACD_SELL_VALUE and
                        macdh_trend == MACDH_DOWN and
                        rsi <= rsi_sell_max and
                        rsi_trend == RSI_DOWN and
                        close < ema30 and close < ema50 and
                        (sar_above is True) and
                        tech <= tech_score_sell_max
                ):
                    return "SELL", "Strict SELL trigger"

            # BUY
            if phase in ["BREAKOUT", "UPTREND", "PULLBACK"]:
                if (
                        adx >= adx_min and
                        adx_trend == ADX_BULL and
                        plus_di > minus_di and
                        0 < macd_vs_signal <= macd_buy_max_days and
                        macdh_trend == MACDH_UP and
                        rsi >= rsi_buy_min and
                        rsi_trend == RSI_UP and
                        close > ema30 and close > ema50 and
                        (sar_above is False) and
                        tech >= tech_score_buy_min
                ):
                    return "BUY", "Strict BUY trigger"

            # -------- NEW categories (stateless but useful) --------
            # EXIT: bearish phase or structure breaks (when not strict SELL)
            if phase == "DOWNTREND":
                return "EXIT", "Phase=DOWNTREND"

            if phase == "REVERSAL_RISK":
                # if still above EMA50 -> reduce, else exit
                if close > ema50:
                    return "REDUCE", "Phase=REVERSAL_RISK (still above EMA50)"
                return "EXIT", "Phase=REVERSAL_RISK (below EMA50)"

            if action_exit_on_structure_break and structure_break_bull:
                return "EXIT", "Bull structure broken (Close < EMA50)"

            # REDUCE: bullish structure but risk flags
            if phase in ["UPTREND", "BREAKOUT", "PULLBACK"] and (close > ema50):
                if action_reduce_on_overbought and stoch_overb:
                    return "REDUCE", "Overbought (Stoch >= 80)"
                if atr_pct > atr_high_vol_threshold:
                    return "REDUCE", f"High volatility (ATR_PCT>{atr_high_vol_threshold})"

            # ADD: good bullish structure but not strict BUY
            # Typical: already in position and you want to scale in.
            bullish_quality = (
                    (phase in ["BREAKOUT", "UPTREND"]) and
                    (plus_di > minus_di) and
                    (adx >= action_add_requires_adx) and
                    (close > ema50)
            )
            if bullish_quality:
                return "ADD", "Bullish quality (phase+DI+ADX) but not strict BUY"

            # ADD on pullback: bullish structure + oversold/rebound hints
            if phase == "PULLBACK" and (ema30 > ema50) and (close > ema50) and (plus_di >= minus_di):
                if stoch_overs or (k is not None and d is not None and k > d and k < 40):
                    return "ADD", "Pullback add (bull structure + stoch rebound)"

            # RANGE default
            return "HOLD", "No trigger"

        action_reason = out.apply(compute_action_and_reason, axis=1, result_type="expand")
        out["Action"] = action_reason[0]
        out["Action_Reason"] = action_reason[1]

        # -------------------------
        # Layer3 Warnings (same as v3)
        # -------------------------
        def compute_layer3_warning(row: pd.Series) -> str:
            warnings = []

            if _num(row, ATR_PCT, 0) > atr_high_vol_threshold:
                warnings.append("High Volatility")

            if _num(row, MACDH_TREND_DAYS, 99) <= fresh_signal_max_days:
                warnings.append("Fresh Signal")

            if _num(row, RSI_TREND_DAYS, 0) > mature_momentum_min_days:
                warnings.append("Mature Momentum")

            k, d = _get_stoch_values(row)
            if k is not None and d is not None:
                if k < stoch_oversold:
                    warnings.append("Stoch Oversold")
                if k > stoch_overbought:
                    warnings.append("Stoch Overbought")
                if k < stoch_oversold and k > d:
                    warnings.append("Stoch Rebound (Oversold)")
                if k > stoch_overbought and k < d:
                    warnings.append("Stoch Reversal (Overbought)")

            return ", ".join(warnings) if warnings else "OK"

        out["Layer3_Warning"] = out.apply(compute_layer3_warning, axis=1)

        # cleanup temp cols
        for c in ["__recent_high", "__adx_slope", "__macd_hist_rising", "__vol_vs_ma20"]:
            if c in out.columns:
                out.drop(columns=[c], inplace=True)

        if not inplace:
            self.dataframe = out
        return out

    def add_trading_statev4_v0(
            self,
            *,
            inplace: bool = True,

            # -------- Action (clear) --------
            macd_buy_max_days: int = 10,  # freshness window for BUY
            adx_min: int = 20,
            rsi_buy_min: int = 45,
            rsi_sell_max: int = 50,
            tech_score_buy_min: int = 65,
            tech_score_sell_max: int = 35,

            # -------- Phase thresholds --------
            adx_strong_min: int = 25,
            adx_weak_max: int = 20,
            rsi_range_low: int = 45,
            rsi_range_high: int = 55,
            stoch_overbought: float = 80,
            stoch_oversold: float = 20,

            # -------- BREAKOUT (STRICT) --------
            breakout_lookback: int = 20,  # recent-high window
            breakout_buffer_pct: float = 0.003,  # 0.3% above recent high
            breakout_adx_min: float = 25,  # must be strong (fixes false breakouts)
            breakout_require_adx_slope_pos: bool = True,
            breakout_require_macd_hist_rising: bool = True,
            breakout_vol_bull_min: float = 0,  # Vol_Perc_vs_MA20 > 0 preferred
            breakout_require_not_overbought: bool = True,
            breakout_use_signal6: bool = True,

            # -------- Layer3 (same as v3) --------
            atr_high_vol_threshold: float = 3,
            fresh_signal_max_days: int = 2,
            mature_momentum_min_days: int = 5,
    ):
        """
        v4 (updated): Clear output model
          - Action: WAIT / BUY / SELL / HOLD
          - Market_Phase: BREAKOUT / UPTREND / PULLBACK / RANGE / DOWNTREND / REVERSAL_RISK
          - Layer3_Warning: unchanged

        Key fix:
          BREAKOUT is now STRICT and requires:
            - Close > rolling recent high (lookback) with buffer
            - ADX >= breakout_adx_min (+ optional positive slope)
            - MACD_Hist rising (optional)
            - Volume confirmation (Vol_Perc_vs_MA20)
            - NOT overbought (optional)
            - fresh momentum (MACD_vs_Signal window)
        """
        import pandas as pd
        import numpy as np

        df = self.dataframe
        if df is None or df.empty:
            return df

        out = df if inplace else df.copy()

        # -------------------------
        # helpers
        # -------------------------
        def _txt(row: pd.Series, col: str, default: str = "") -> str:
            v = row.get(col, default)
            return "" if v is None else str(v)

        def _boolish(x):
            if isinstance(x, (bool, np.bool_)):
                return bool(x)
            if x is None:
                return None
            s = str(x).strip().lower()
            if s in ("true", "1", "yes", "y"):
                return True
            if s in ("false", "0", "no", "n"):
                return False
            return None

        # ---- helper stoch compatible with different names ----
        def _get_stoch_values(row: pd.Series):
            candidates_k = ["STOCH_K", "Stoch_K", "stoch_k", "STOCHk", "stochK", "Stochastic_K"]
            candidates_d = ["STOCH_D", "Stoch_D", "stoch_d", "STOCHd", "stochD", "Stochastic_D"]
            k = next((row.get(c) for c in candidates_k if c in row.index), None)
            d = next((row.get(c) for c in candidates_d if c in row.index), None)
            try:
                k = float(k) if k is not None else None
                d = float(d) if d is not None else None
            except Exception:
                return None, None
            return k, d

        # -------------------------
        # column names / constants
        # -------------------------
        LIQ_OK = "OK"
        ADX_BULL = "Bullish"
        ADX_BEAR = "Bearish"

        DI_PLUS = "PLUS_DI"
        DI_MINUS = "MINUS_DI"

        MACD_VS_SIGNAL = "MACD_vs_Signal"
        MACD_SELL_VALUE = -1

        MACDH_TREND = "MACDH_Trend"
        MACDH_UP = "Up"
        MACDH_DOWN = "Down"

        RSI = "RSI"
        RSI_TREND = "RSI_Trend"
        RSI_UP = "Up"
        RSI_DOWN = "Down"

        CLOSE = "Close"
        EMA_FAST = "EMA_30"
        EMA_SLOW = "EMA_50"
        HIGH = "High"

        SAR_ABOVE = "SAR_Above_Price"
        TECH_SCORE = "TECH_SCORE"

        VOL_VS_MA20 = "Vol_Perc_vs_MA20"

        ATR_PCT = "ATR_PCT"
        MACDH_TREND_DAYS = "MACDH_Trend_Days"
        RSI_TREND_DAYS = "RSI_Trend_Days"

        # -------------------------
        # PRECOMPUTATIONS (vectorized) for STRICT BREAKOUT
        # -------------------------
        # Recent high (exclude current bar)
        if HIGH in out.columns:
            recent_high = (
                pd.to_numeric(out[HIGH], errors="coerce")
                    .rolling(breakout_lookback, min_periods=max(3, breakout_lookback // 3))
                    .max()
                    .shift(1)
            )
        else:
            # fallback: use Close as proxy (less ideal)
            recent_high = (
                pd.to_numeric(out[CLOSE], errors="coerce")
                    .rolling(breakout_lookback, min_periods=max(3, breakout_lookback // 3))
                    .max()
                    .shift(1)
            )

        out["__recent_high"] = recent_high

        # ADX slope (simple diff)
        if "ADX" in out.columns:
            adx_series = pd.to_numeric(out["ADX"], errors="coerce")
            out["__adx_slope"] = adx_series.diff()
        else:
            out["__adx_slope"] = np.nan

        # MACD hist rising?
        if "MACD_Hist" in out.columns:
            mh = pd.to_numeric(out["MACD_Hist"], errors="coerce")
            out["__macd_hist_rising"] = mh.diff() > 0
        else:
            out["__macd_hist_rising"] = False

        # ensure Vol_Perc_vs_MA20 numeric
        if VOL_VS_MA20 in out.columns:
            out["__vol_vs_ma20"] = pd.to_numeric(out[VOL_VS_MA20], errors="coerce").fillna(0.0)
        else:
            out["__vol_vs_ma20"] = 0.0

        # -------------------------
        # Phase detection (updated)
        # -------------------------
        def compute_market_phase(row: pd.Series) -> str:
            # numeric core
            close = float(pd.to_numeric(row.get(CLOSE, 0), errors="coerce") or 0)
            ema30 = float(pd.to_numeric(row.get(EMA_FAST, 0), errors="coerce") or 0)
            ema50 = float(pd.to_numeric(row.get(EMA_SLOW, 0), errors="coerce") or 0)

            adx = float(pd.to_numeric(row.get("ADX", 0), errors="coerce") or 0)
            plus_di = float(pd.to_numeric(row.get(DI_PLUS, 0), errors="coerce") or 0)
            minus_di = float(pd.to_numeric(row.get(DI_MINUS, 0), errors="coerce") or 0)

            macdh_trend = _txt(row, MACDH_TREND, "").strip()
            adx_trend = _txt(row, "ADX_Trend", "").strip()

            sar_above_raw = row.get(SAR_ABOVE, None)
            sar_above = _boolish(sar_above_raw)
            sar_bull = (sar_above is False)
            sar_bear = (sar_above is True)

            rsi = float(pd.to_numeric(row.get(RSI, 50), errors="coerce") or 50)
            rsi_trend = _txt(row, RSI_TREND, "").strip()

            macd_vs_signal = float(pd.to_numeric(row.get(MACD_VS_SIGNAL, 0), errors="coerce") or 0)

            vol_vs_ma20 = float(pd.to_numeric(row.get("__vol_vs_ma20", 0), errors="coerce") or 0)
            recent_high_val = pd.to_numeric(row.get("__recent_high", np.nan), errors="coerce")
            adx_slope = float(pd.to_numeric(row.get("__adx_slope", 0), errors="coerce") or 0)
            macd_hist_rising = bool(row.get("__macd_hist_rising", False))

            k, d = _get_stoch_values(row)

            # structure flags
            trend_up = (close > ema30) and (ema30 > ema50)
            trend_down = (close < ema30) and (ema30 < ema50)

            di_up = plus_di > minus_di
            di_down = minus_di > plus_di

            adx_strong = adx >= adx_strong_min
            adx_weak = adx < adx_weak_max

            macd_up = (macdh_trend == MACDH_UP)
            macd_down = (macdh_trend == MACDH_DOWN)

            fresh_momentum = (macd_vs_signal > 0) and (macd_vs_signal <= macd_buy_max_days)

            # -------- 1) BREAKOUT (STRICT) --------
            # must break above recent high with buffer
            breaks_recent_high = False
            if pd.notna(recent_high_val) and recent_high_val > 0:
                breaks_recent_high = close > (float(recent_high_val) * (1.0 + breakout_buffer_pct))

            not_overbought = True
            if breakout_require_not_overbought and (k is not None):
                not_overbought = k < stoch_overbought

            s6_ok = True
            if breakout_use_signal6 and ("Signal6" in row.index):
                s6 = _txt(row, "Signal6", "").lower()
                # allow early bullish states only
                s6_ok = ("wakeup" in s6) or (s6 in ("uptrend", "uptrend*")) or ("uptrend*" in s6)

            adx_ok = adx >= breakout_adx_min
            adx_slope_ok = (adx_slope > 0) if breakout_require_adx_slope_pos else True
            macd_hist_ok = (macd_hist_rising is True) if breakout_require_macd_hist_rising else True
            vol_ok = vol_vs_ma20 > breakout_vol_bull_min

            breakout_ok = (
                    breaks_recent_high and
                    fresh_momentum and
                    adx_ok and
                    adx_slope_ok and
                    macd_hist_ok and
                    vol_ok and
                    not_overbought and
                    s6_ok and
                    (not trend_down)
            )
            if breakout_ok:
                return "BREAKOUT"

            # -------- 2) REVERSAL_RISK --------
            rev_risk = False
            if trend_up and di_down:
                rev_risk = True
            if trend_down and di_up:
                rev_risk = True

            # EMA50 break against structure
            if trend_up and (close < ema50):
                rev_risk = True
            if trend_down and (close > ema50):
                rev_risk = True

            if "Signal6" in row.index:
                s6 = _txt(row, "Signal6", "").lower()
                if "rev" in s6 or "reversal" in s6:
                    rev_risk = True

            if rev_risk:
                return "REVERSAL_RISK"

            # -------- 3) UPTREND --------
            if trend_up and di_up and (adx_strong or macd_up) and sar_bull:
                return "UPTREND"

            # -------- 4) DOWNTREND --------
            if trend_down and di_down and (adx_strong or macd_down) and sar_bear:
                return "DOWNTREND"

            # -------- 5) PULLBACK --------
            # bullish structure but retracement / cooling signals
            # IMPORTANT: allow pullback even if close dips under EMA30 but stays above EMA50
            if (ema30 > ema50) and (close > ema50):
                pullback_votes = 0

                if (rsi < 50) or (rsi_trend == RSI_DOWN):
                    pullback_votes += 1

                if k is not None and d is not None:
                    if (k < d) or (k < 40):
                        pullback_votes += 1

                if macd_down:
                    pullback_votes += 1

                if (close < ema30):
                    pullback_votes += 1

                if pullback_votes >= 2:
                    return "PULLBACK"

            # -------- 6) RANGE --------
            if adx_weak and (rsi_range_low <= rsi <= rsi_range_high) and (not trend_up) and (not trend_down):
                return "RANGE"

            return "RANGE"

        out["Market_Phase"] = out.apply(compute_market_phase, axis=1)
        # -------------------------
        # Action (clear, uses phase)
        # -------------------------
        def compute_action(row: pd.Series) -> str:
            if row.get("Liquidity") != LIQ_OK:
                return "WAIT"

            phase = _txt(row, "Market_Phase", "RANGE")

            plus_di = float(pd.to_numeric(row.get(DI_PLUS, 0), errors="coerce") or 0)
            minus_di = float(pd.to_numeric(row.get(DI_MINUS, 0), errors="coerce") or 0)
            adx = float(pd.to_numeric(row.get("ADX", 0), errors="coerce") or 0)

            macd_vs_signal = float(pd.to_numeric(row.get(MACD_VS_SIGNAL, 0), errors="coerce") or 0)
            close = float(pd.to_numeric(row.get(CLOSE, 0), errors="coerce") or 0)
            ema30 = float(pd.to_numeric(row.get(EMA_FAST, 0), errors="coerce") or 0)
            ema50 = float(pd.to_numeric(row.get(EMA_SLOW, 0), errors="coerce") or 0)

            sar_above = _boolish(row.get(SAR_ABOVE, None))
            tech = float(pd.to_numeric(row.get(TECH_SCORE, 0), errors="coerce") or 0)
            rsi = float(pd.to_numeric(row.get(RSI, 50), errors="coerce") or 50)

            macdh_trend = _txt(row, MACDH_TREND, "").strip()
            rsi_trend = _txt(row, RSI_TREND, "").strip()
            adx_trend = _txt(row, "ADX_Trend", "").strip()

            # BUY trigger (only in bullish phases)
            if phase in ["BREAKOUT", "UPTREND", "PULLBACK"]:
                if (
                        adx >= adx_min and
                        adx_trend == ADX_BULL and
                        plus_di > minus_di and
                        0 < macd_vs_signal <= macd_buy_max_days and
                        macdh_trend == MACDH_UP and
                        rsi >= rsi_buy_min and
                        rsi_trend == RSI_UP and
                        close > ema30 and close > ema50 and
                        (sar_above is False) and
                        tech >= tech_score_buy_min
                ):
                    return "BUY"

            # SELL trigger (bearish phases)
            if phase in ["DOWNTREND", "REVERSAL_RISK"]:
                if (
                        adx >= adx_min and
                        adx_trend == ADX_BEAR and
                        minus_di > plus_di and
                        macd_vs_signal == MACD_SELL_VALUE and
                        macdh_trend == MACDH_DOWN and
                        rsi <= rsi_sell_max and
                        rsi_trend == RSI_DOWN and
                        close < ema30 and close < ema50 and
                        (sar_above is True) and
                        tech <= tech_score_sell_max
                ):
                    return "SELL"

            return "HOLD"

        out["Action"] = out.apply(compute_action, axis=1)

        # -------------------------
        # Layer3 Warnings (same as v3)
        # -------------------------
        def compute_layer3_warning(row: pd.Series) -> str:
            warnings = []

            def _n(col, default=0.0):
                return float(pd.to_numeric(row.get(col, default), errors="coerce") or default)

            if _n(ATR_PCT, 0) > atr_high_vol_threshold:
                warnings.append("High Volatility")

            if _n(MACDH_TREND_DAYS, 99) <= fresh_signal_max_days:
                warnings.append("Fresh Signal")

            if _n(RSI_TREND_DAYS, 0) > mature_momentum_min_days:
                warnings.append("Mature Momentum")

            k, d = _get_stoch_values(row)
            if k is not None and d is not None:
                if k < stoch_oversold:
                    warnings.append("Stoch Oversold")
                if k > stoch_overbought:
                    warnings.append("Stoch Overbought")
                if k < stoch_oversold and k > d:
                    warnings.append("Stoch Rebound (Oversold)")
                if k > stoch_overbought and k < d:
                    warnings.append("Stoch Reversal (Overbought)")

            return ", ".join(warnings) if warnings else "OK"

        out["Layer3_Warning"] = out.apply(compute_layer3_warning, axis=1)

        # cleanup temp cols
        for c in ["__recent_high", "__adx_slope", "__macd_hist_rising", "__vol_vs_ma20"]:
            if c in out.columns:
                out.drop(columns=[c], inplace=True)

        if not inplace:
            self.dataframe = out
        return out

    def add_prev_true_range(self):
        df = self.dataframe

        df["Prev_Close"] = df["Close"].shift(1)

        # True Range
        tr1 = df["High"] - df["Low"]
        tr2 = (df["High"] - df["Prev_Close"]).abs()
        tr3 = (df["Low"] - df["Prev_Close"]).abs()

        df["TrueRange"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # True Range precedente
        df["Prev_TrueRange"] = df["TrueRange"].shift(1)

        # Livello di uscita: Close_precedente - 1/2 TrueRange_precedente
        df["Stop_Level"] = df["Prev_Close"] - 0.5 * df["Prev_TrueRange"]

    def add_dynamic_exit_levels(self):
        df = self.dataframe

        df["Prev_Close"] = df["Close"].shift(1)
        df["Prev_High"] = df["High"].shift(1)
        df["Prev_Low"] = df["Low"].shift(1)

        df["Prev_Range"] = df["Prev_High"] - df["Prev_Low"]

        # Livello di uscita: close precedente - metà range precedente
        df["Stop_Level"] = df["Prev_Close"] - 0.5 * df["Prev_Range"]

    def _add_liquidity_columns(self):
        """
        Colonne diagnostiche + classificazione Liquidity:
          - Vol_MA20               : media mobile dei volumi (periodo ma_period)
          - Vol_ZeroDays_30        : # giorni con volume == 0 negli ultimi 'window'
          - Vol_LowDays_30         : # giorni con volume < low_vol_cut negli ultimi 'window'
          - Vol_SpikeRatio_30      : max(vol)/mean(vol) ultimi 'window' (spike detector)
          - Liquidity              : 'OK' | 'LOW' | 'AVOID'
        """
        df = self.dataframe
        if df is None or df.empty or 'Volume' not in df.columns:
            return

        p = self.liq_params
        vol = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)

        # --- MA volumi
        df['Vol_MA20'] = vol.rolling(p['ma_period'], min_periods=1).mean()

        # --- diagnostiche su finestra mobile
        win = int(p['window'])
        df['Vol_ZeroDays_30'] = (
            vol.rolling(win, min_periods=1)
                .apply(lambda x: int((x == 0).sum()))
                .astype('Int64')
        )
        df['Vol_LowDays_30'] = (
            vol.rolling(win, min_periods=1)
                .apply(lambda x: int((x < p['low_vol_cut']).sum()))
                .astype('Int64')
        )

        vmax = vol.rolling(win, min_periods=1).max()
        vmean = vol.rolling(win, min_periods=1).mean()
        # evita divisioni per 0 / inf
        vmean_safe = vmean.replace(0, np.nan)
        spike = (vmax / vmean_safe)
        spike = spike.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        df['Vol_SpikeRatio_30'] = spike

        # --- regole di classificazione (riga per riga)
        ma20 = df['Vol_MA20']
        zeros = df['Vol_ZeroDays_30'].fillna(0)
        lows = df['Vol_LowDays_30'].fillna(0)
        ratio = df['Vol_SpikeRatio_30']

        # condizioni “gravi” → AVOID
        avoid_hard = (
                             (ma20 < p['low_threshold']) & ((lows >= 5) | (zeros >= 2))
                     ) | (
                         # spike estremi *su base povera*
                             (ratio >= p['spike_ratio_max']) & (ma20 < p['warn_threshold'])
                     )

        # condizioni “moderate” → LOW
        low_flag = (
                (ma20 < p['warn_threshold']) |
                (lows >= 2)
        )

        liq = np.where(avoid_hard, 'AVOID', np.where(low_flag, 'LOW', 'OK'))
        df['Liquidity'] = pd.Categorical(liq, categories=['OK', 'LOW', 'AVOID'], ordered=True)

    def fetch_ticker_name(self, prefer_long: bool = True) -> str:
        """
        Ricava e salva in self.tickerName il nome del ticker da Yahoo Finance.
        Prova longName, poi shortName, poi displayName, infine il simbolo.
        """
        try:
            tk = yf.Ticker(self.ticker)
            info = tk.get_info() or {}
            name = None
            if prefer_long:
                name = info.get("longName") or info.get("shortName")
            else:
                name = info.get("shortName") or info.get("longName")
            name = name or info.get("displayName") or info.get("symbol") or str(self.ticker)
            self.tickerName = name
            return name
        except Exception:
            # Fallback sicuro
            self.tickerName = str(self.ticker)
            return self.tickerName

    @property
    def display_name(self) -> str:
        """Ritorna un nome pronto per i grafici, usando cache se già presente."""
        return self.tickerName or self.fetch_ticker_name()

    def download_data(self):
        """
        Scarica i dati OHLC dal servizio Yahoo Finance escludendo dividendi e split,
        utilizzando una cache locale parquet per evitare scaricamenti ripetuti.
        """
        import os
        from pathlib import Path
        from datetime import datetime, timedelta

        # Determina la cartella cache
        project_root = Path(__file__).resolve().parent
        cache_dir = project_root / "cache"
        if not cache_dir.exists():
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"[TechnicalAnalyzer] Errore creazione cartella cache: {e}")

        # Sanitizzazione del ticker per Windows
        clean_ticker = str(self.ticker).strip().upper().replace("/", "_")
        base_part = clean_ticker.split(".")[0]
        if base_part in ["CON", "PRN", "AUX", "NUL"] or any(
            base_part.startswith(x) for x in ["COM", "LPT"] if len(base_part) == 4 and base_part[3].isdigit()
        ):
            clean_ticker = f"W_{clean_ticker}"

        cache_file = cache_dir / f"{clean_ticker}_{self.period}_history.parquet"

        # Controlla validità cache (usando self.cache_hours)
        use_cache = False
        if self.use_cache and cache_file.exists() and self.cache_hours > 0:
            try:
                file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if datetime.now() - file_mtime < timedelta(hours=self.cache_hours):
                    use_cache = True
            except Exception as e:
                print(f"[TechnicalAnalyzer] Errore lettura mtime cache per {self.ticker}: {e}")

        if use_cache:
            try:
                df = pd.read_parquet(cache_file)
                if df is not None and not df.empty:
                    if not isinstance(df.index, pd.DatetimeIndex):
                        df.index = pd.to_datetime(df.index)
                    self.dataframe = df
                    print(f"[TechnicalAnalyzer] Dati storici caricati da cache per {self.ticker} ({len(df)} righe)")
                    return
            except Exception as e:
                print(f"[TechnicalAnalyzer] Errore caricamento cache per {self.ticker}: {e}. Scaricamento in corso...")

        # Scarica i dati storici
        try:
            print(f"[TechnicalAnalyzer] Scaricamento dati da Yahoo Finance per {self.ticker}...")
            df = yf.Ticker(self.ticker).history(
                period=self.period,
                actions=False,
                auto_adjust=False  # evita warning e mantiene i prezzi non aggiustati
            )
            df.dropna(inplace=True)
            if df is not None and not df.empty:
                self.dataframe = df
                if self.use_cache:
                    try:
                        df.to_parquet(cache_file)
                        print(f"[TechnicalAnalyzer] Salvata cache dati storici per {self.ticker}")
                    except Exception as e:
                        print(f"[TechnicalAnalyzer] Errore scrittura cache per {self.ticker}: {e}")
            else:
                raise ValueError("DataFrame scaricato vuoto")
        except Exception as e:
            print(f"[TechnicalAnalyzer] Errore nello scaricamento dei dati per {self.ticker}: {e}.")
            if self.use_cache and cache_file.exists():
                try:
                    print(f"[TechnicalAnalyzer] Fallback: caricamento cache scaduta per {self.ticker}...")
                    df = pd.read_parquet(cache_file)
                    if df is not None and not df.empty:
                        if not isinstance(df.index, pd.DatetimeIndex):
                            df.index = pd.to_datetime(df.index)
                        self.dataframe = df
                        return
                except Exception as e_fallback:
                    print(f"[TechnicalAnalyzer] Errore fallback cache per {self.ticker}: {e_fallback}")
            self.dataframe = pd.DataFrame()

    ### Funzione per calcolare category: BUY, BUY ON PULLBACK etc CHIAMATA da WEBGUI soltanto!
    def add_category(
            self,
            use_signal6_score: bool = True,
            thresholds: Optional[Dict[str, float]] = None,
            write_columns: bool = True):

        """
        Crea la colonna 'Category' (e, opzionalmente, 'EntryTrigger', 'StopHint', 'Notes')
        in base a Signal6, score, MCS e altre condizioni.

        Prerequisiti (già calcolati prima di chiamare questa funzione):
          - Signal6 (+ opzionale Signal6_Trend_Days)
          - TECH_SCORE (o TECH_SCORE se use_signal6_score=False)
          - MCS_Smoothed, MCS_Conf
          - SAR_Above_Price, EMA_30, EMA_50
          - RSI (opzionale), Volume (opzionale)

        Args:
            use_signal6_score: se True usa TECH_SCORE, altrimenti TECH_SCORE.
            thresholds: dict per override delle soglie (chiavi uguali a quelle di default).
            write_columns: se True scrive le colonne su self.dataframe, altrimenti ritorna solo la Series.

        Returns:
            pandas.DataFrame se write_columns=True, altrimenti pandas.Series con la sola Category.
        """
        #print("--- Sono entrato in add_category ---")
        df = self.dataframe
        if df is None or df.empty:
            raise ValueError("DataFrame vuoto. Calcola prima gli indicatori.")

        # ---- Soglie di default
        TH = dict(
            BUY_NOW_MIN=70,
            BUY_PB_MIN=60,
            WATCH_MIN=55,
            BEARISH_MAX=45,
            MCS_CONF_OK=0.50,
            MCS_CONF_WEAK=0.50,
            RSI_OB=75,
            RSI_OS=30,
            LOOKBACK_BREAKOUT=5,
            VOL_ROLL=20,
            MCS_SLOPE_LOOKBACK=2
        )
        if thresholds:
            TH.update(thresholds)

        # ---- Set famiglie Signal6
        BULL_STRONG   = {'Uptrend', 'Uptrend*', 'wakeup2', 'wakeup2*'}
        BULL_MODERATE = {'Uptrend-', 'Uptrend--', 'Uptrend---', 'wakeup1', 'wakeup2-'}
        SLEEP         = {'sleep1', 'sleep2'}
        BEAR          = {'Downtrend', 'Downtrend*', 'Downtrend_revS3Sig+',
                         'Downtrend_revS3Sig++', 'Downtrend_revS3Sig+++'}
        REVERSAL_SET  = {'Downtrend_revS3Sig+', 'Downtrend_revS3Sig++', 'Downtrend_revS3Sig+++'}

        # ---- Colonne richieste
        score_col = 'TECH_SCORE' if use_signal6_score and 'TECH_SCORE' in df.columns else 'TECH_SCORE'
        required = ['Signal6', score_col, 'MCS_Smoothed', 'MCS_Conf', 'SAR_Above_Price', 'EMA_30', 'EMA_50']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Mancano colonne richieste: {missing} – calcola prima indicatori/score/Signal6.")

        # ---- Alias series
        s6   = df['Signal6'].astype(str)
        sc   = df[score_col]
        mcs  = df['MCS_Smoothed']
        conf = df['MCS_Conf']

        # ---- Trend OK
        trend_ok = (~df['SAR_Above_Price'].astype(bool)) & (df['EMA_30'] >= df['EMA_50'])

        # ---- Momentum MCS (vectorized)
        slope1 = mcs.diff() > 0
        slope2 = (mcs - mcs.shift(TH['MCS_SLOPE_LOOKBACK'])) > 0

        # ---- Categoria primaria (ordine di priorità come nel summary originale)
        cat = pd.Series('HOLD / NEUTRAL', index=df.index, dtype='object')

        # 1) AVOID / BEARISH
        bear_mask = s6.isin(BEAR) | (sc < TH['BEARISH_MAX'])
        cat.loc[bear_mask] = 'AVOID / BEARISH'

        # 2) REVERSAL CANDIDATE
        rev_mask = s6.isin(REVERSAL_SET) & (mcs > 0) & (conf >= TH['MCS_CONF_OK'])
        cat.loc[rev_mask] = 'REVERSAL CANDIDATE'

        # 3) BUY NOW / BUY ON PULLBACK / WATCHLIST (solo se bull)
        bull_mask = s6.isin(BULL_STRONG.union(BULL_MODERATE))
        bull_strong = s6.isin(BULL_STRONG)

        buy_now_mask = bull_strong & (sc >= TH['BUY_NOW_MIN']) & (mcs > 0) & (conf >= TH['MCS_CONF_OK'])
        cat.loc[buy_now_mask] = 'BUY NOW'

        buy_pb_mask = bull_mask & (sc >= TH['BUY_PB_MIN']) & (sc < TH['BUY_NOW_MIN']) & (mcs >= 0)
        cat.loc[buy_pb_mask] = 'BUY ON PULLBACK'

        watch_mask = bull_mask & (sc >= TH['WATCH_MIN']) & (sc < TH['BUY_PB_MIN']) & (conf >= TH['MCS_CONF_OK'])
        cat.loc[watch_mask] = 'WATCHLIST'

        # 4) SLEEP -> HOLD / NEUTRAL (già default)

        # ---- Aggiustamenti dinamici (upgrade/downgrade)
        # BUY NOW -> BUY ON PULLBACK se momentum raffredda
        dn1 = (cat == 'BUY NOW') & (~slope2) & (mcs <= mcs.shift(1))
        cat.loc[dn1] = 'BUY ON PULLBACK'

        # BUY ON PULLBACK -> WATCHLIST se trend fragile
        dn2 = (cat == 'BUY ON PULLBACK') & (~trend_ok)
        cat.loc[dn2] = 'WATCHLIST'

        # WATCHLIST -> BUY ON PULLBACK se momentum migliora e trend ok
        up1 = (cat == 'WATCHLIST') & trend_ok & slope1
        cat.loc[up1] = 'BUY ON PULLBACK'

        # ---- Reduce / Take Profit
        red = cat.isin(['BUY NOW', 'BUY ON PULLBACK']) & (sc >= TH['BUY_NOW_MIN']) & ((mcs <= 0) | (conf < TH['MCS_CONF_WEAK']))
        cat.loc[red] = 'REDUCE / TAKE PROFIT'

        # ---- Ordina categorie
        ordered_cats = [
            'BUY NOW','BUY ON PULLBACK','WATCHLIST','REDUCE / TAKE PROFIT',
            'REVERSAL CANDIDATE','HOLD / NEUTRAL','AVOID / BEARISH'
        ]
        cat = pd.Categorical(cat, categories=ordered_cats, ordered=True)

        if not write_columns:
            return cat

        # ================== Note / Entry / Stop (vector-like) ==================
        notes_parts = []

        # RSI note
        if 'RSI' in df.columns:
            rsi = df['RSI']
            rsi_note = np.where(rsi > TH['RSI_OB'], 'RSI overbought',
                        np.where(rsi < TH['RSI_OS'], 'RSI oversold', ''))
            notes_parts.append(pd.Series(rsi_note, index=df.index, dtype='object'))

        # Trend note
        notes_parts.append(pd.Series(np.where(trend_ok, 'Trend OK', 'Trend fragile'),
                                     index=df.index, dtype='object'))

        # Volume note
        if 'Volume' in df.columns:
            vol20 = df['Volume'].rolling(TH['VOL_ROLL']).mean()
            vol_note = np.where((~vol20.isna()) & (df['Volume'] < vol20), 'Bassa liquidità', '')
            notes_parts.append(pd.Series(vol_note, index=df.index, dtype='object'))

        # MCS arrow
        mcs_down = (~slope1) & mcs.notna() & mcs.shift(1).notna()
        mcs_note = np.where(slope1, 'MCS↑', np.where(mcs_down, 'MCS↓', ''))
        notes_parts.append(pd.Series(mcs_note, index=df.index, dtype='object'))

        # Adjustment notes
        adj = pd.Series('', index=df.index, dtype='object')
        adj.loc[dn1] = 'Momentum in raffreddamento (downgrade)'
        adj.loc[dn2] = 'Trend fragile (downgrade)'
        adj.loc[up1] = 'Miglioramento momentum (upgrade)'
        adj.loc[red] = 'Momentum stanco / conf bassa'
        notes_parts.append(adj)

        # Compose notes
        notes_df = pd.concat(notes_parts, axis=1)
        # unisci i pezzi non vuoti con '; '
        notes = notes_df.apply(lambda row: '; '.join([p for p in row.tolist() if isinstance(p, str) and p.strip()]), axis=1)

        # Entry/Stop suggeriti
        entry = pd.Series('n/a', index=df.index, dtype='object')
        stop  = pd.Series('n/a', index=df.index, dtype='object')
        entry.loc[(cat == 'BUY NOW')] = f"Breakout > High({TH['LOOKBACK_BREAKOUT']})"
        stop.loc[(cat == 'BUY NOW')]  = "Sotto Alligator_Teeth / SAR"

        entry.loc[(cat == 'BUY ON PULLBACK')] = "Rebound su EMA30/Lips con close > high prev."
        stop.loc[(cat == 'BUY ON PULLBACK')]  = "Sotto EMA30 / Alligator_Teeth"

        entry.loc[(cat == 'WATCHLIST')] = "Attendi: score ≥60 e close > EMA30"
        # stop rimane 'n/a'

        entry.loc[(cat == 'REDUCE / TAKE PROFIT')] = "n/a"
        stop.loc[(cat == 'REDUCE / TAKE PROFIT')]  = "Trailing con SAR / sotto Lips"

        entry.loc[(cat == 'AVOID / BEARISH')] = "Evita; attendi reversal"
        # stop rimane 'n/a'

        entry.loc[(cat == 'REVERSAL CANDIDATE')] = "Conferme: RSI>50 e close>EMA30"
        stop.loc[(cat == 'REVERSAL CANDIDATE')]  = "Sotto minimo recente"

        # Scrivi colonne
        self.dataframe['Category']     = cat
        self.dataframe['EntryTrigger'] = entry
        self.dataframe['StopHint']     = stop
        self.dataframe['Notes']        = notes

        return self.dataframe

    ####### Funzioni Util per cacolare direzione trend e numero di giorni in trend
    def _calculate_trend(self, dato):
        """Determina la direzione dell'istogramma MACD"""
        trends = []
        prev = None

        for val in dato:
            if np.isnan(val):
                trends.append(np.nan)
                continue

            if prev is None:
                trends.append('Flat')
            elif val > prev:
                trends.append('Up')
            elif val < prev:
                trends.append('Down')
            else:
                trends.append('Flat')

            prev = val

        return trends

    def _calculate_trend_duration(self, trends):
        """Calcola la durata in giorni del trend corrente"""
        durations = []
        current_duration = 0
        current_trend = None

        for trend in trends:
            if trend != current_trend:
                current_duration = 1
                current_trend = trend
            else:
                current_duration += 1

            durations.append(current_duration)

        return durations

    def _calculate_price_changes(self):
        """Calcola le variazioni percentuali di prezzo per diversi periodi basati sui giorni di trading"""
        close_prices = self.dataframe['Close']

        for col_name, days in self.pctv_periods.items():
            # Shift sui giorni di trading (non di calendario)
            shifted = close_prices.shift(days)

            # Calcola la variazione percentuale
            self.dataframe[col_name] = ((close_prices - shifted) / shifted) * 100

            # Arrotonda a 2 decimali
            self.dataframe[col_name] = self.dataframe[col_name].round(2)



    ############# RSI ############################################

    def _add_rsi_analysis(self, df):
        # 1. Trend istogramma
        df['RSI_Trend'] = self._calculate_trend(df['RSI'])
        # 2. Durata trend corrente
        df['RSI_Trend_Days'] = self._calculate_trend_duration(df['RSI_Trend'])
        return df

    def _calculate_rsi(self):
        close = self.dataframe['Close'].values
        return talib.RSI(close, timeperiod=self.rsi_period)

    ############# WILLIAMS %R ############################################

    def set_williams_parameters(self, period=14):
        """Configura il periodo per il calcolo del Williams %R"""
        self.williams_period = period

    def _calculate_williams(self):
        """Calcola il Williams %R"""
        try:
            high = self.dataframe['High'].values
            low = self.dataframe['Low'].values
            close = self.dataframe['Close'].values

            # Verifica che ci siano abbastanza dati
            if len(high) < self.williams_period:
                print(f"Dati insufficienti per Williams %R: {len(high)} < {self.williams_period}")
                return np.full(len(high), np.nan)

            result = talib.WILLR(high, low, close, timeperiod=self.williams_period)
            return result
        except Exception as e:
            print(f"Errore nel calcolo Williams %R: {e}")
            return np.full(len(self.dataframe), np.nan)

    def _add_williams_analysis(self, df):
        """Aggiunge l'analisi del Williams %R al DataFrame"""
        try:
            # 1. Trend Williams %R
            df['WILLR_Trend'] = self._calculate_trend(df['Williams_R'])
            # 2. Durata trend corrente
            df['WILLR_Trend_Days'] = self._calculate_trend_duration(df['WILLR_Trend'])
            # 3. Zone di ipercomprato/ipervenduto
            df['WILLR_Overbought'] = df['Williams_R'] > -20  # Ipercomprato
            df['WILLR_Oversold'] = df['Williams_R'] < -80  # Ipervenduto
            df['WILLR_Neutral'] = (df['Williams_R'] >= -80) & (df['Williams_R'] <= -20)  # Zona neutrale
        except Exception as e:
            print(f"Errore nell'analisi Williams %R: {e}")
            # Crea colonne di default
            df['WILLR_Trend'] = 'Flat'
            df['WILLR_Trend_Days'] = 0
            df['WILLR_Overbought'] = False
            df['WILLR_Oversold'] = False
            df['WILLR_Neutral'] = True
        return df

    ############# STOCHASTIC, ALLIGATOR ############################################

    def _add_stochastic_analysis(self, df):
        # 1. Trend istogramma
        df['SK_Trend'] = self._calculate_trend(df['Stoch_K'])
        # 2. Durata trend corrente
        df['SK_Trend_Days'] = self._calculate_trend_duration(df['SK_Trend'])
        return df

    def _calculate_stochastic(self):
        high = self.dataframe['High'].values
        low = self.dataframe['Low'].values
        close = self.dataframe['Close'].values
        slowk, slowd = talib.STOCH(
            high, low, close,
            fastk_period=self.stoch_params['fastk_period'],
            slowk_period=self.stoch_params['slowk_period'],
            slowk_matype=0,
            slowd_period=self.stoch_params['slowd_period'],
            slowd_matype=0
        )
        # Bounding tra 0 e 100 per prevenire errori da dati anomali di Yahoo Finance
        slowk = np.clip(slowk, 0.0, 100.0)
        slowd = np.clip(slowd, 0.0, 100.0)
        return slowk, slowd

    def _calculate_alligator(self):
        close = self.dataframe['Close']
        jaw = pd.Series(talib.WMA(close, timeperiod=self.alligator_params['jaw_period']), index=close.index).shift(self.alligator_params['shift_jaw'])
        teeth = pd.Series(talib.WMA(close, timeperiod=self.alligator_params['teeth_period']), index=close.index).shift(
            self.alligator_params['shift_teeth'])
        lips = pd.Series(talib.WMA(close, timeperiod=self.alligator_params['lips_period']), index=close.index).shift(
            self.alligator_params['shift_lips'])
        return jaw, teeth, lips

    ############# MOVING AVERAGE CALCULATION ############################################

    def set_moving_average_parameters(self, timeperiod=20, matype=0):
        """Configura i parametri per il calcolo della Media Mobile"""
        self.ma_params = {
            'timeperiod': timeperiod,
            'matype': matype
        }

    def _calculate_ma(self):
        """Calcolo interno della Media Mobile"""
        close_prices = self.dataframe['Close'].values
        if self.ma_params['matype'] == 0:
            return talib.SMA(close_prices, timeperiod=self.ma_params['timeperiod'])
        elif self.ma_params['matype'] == 1:
            return talib.EMA(close_prices, timeperiod=self.ma_params['timeperiod'])
        else:
            return talib.MA(close_prices,
                            timeperiod=self.ma_params['timeperiod'],
                            matype=self.ma_params['matype'])

    ######################## PARABOLIC SAR CALCULATION
    def set_sar_parameters(self, acceleration=0.02, maximum=0.2):
        """Configura i parametri per il calcolo del Parabolic SAR"""
        self.sar_params = {
            'acceleration': acceleration,
            'maximum': maximum
        }

    def _calculate_sar(self):
        """Calcola il Parabolic SAR"""
        high = self.dataframe['High'].values
        low = self.dataframe['Low'].values
        return talib.SAR(high, low,
                         acceleration=self.sar_params['acceleration'],
                         maximum=self.sar_params['maximum'])

    def _add_sar_analysis(self, df):
        """Aggiunge l'analisi base del SAR al DataFrame"""
        # Solo la posizione relativa rispetto al prezzo
        df['SAR_Above_Price'] = df['SAR'] > df['Close']
        return df

    ############# MACD CALCULATION AND ANALYSIS ############################################
    def _add_macd_vs_signal_streak(
            self,
            macd_col: str = "MACD",
            signal_col: str = "MACD_Signal",
            out_col: str = "MACD_vs_Signal",
    ):
        """
        Colonna unica:
          +n  → MACD > MACD_Signal da n giorni
          -n  → MACD < MACD_Signal da n giorni
           0  → MACD == MACD_Signal o NaN
        """
        df = self.dataframe
        if df is None or df.empty:
            raise ValueError("DataFrame vuoto.")
        if macd_col not in df.columns or signal_col not in df.columns:
            raise ValueError("MACD o MACD_Signal mancanti.")

        macd = pd.to_numeric(df[macd_col], errors="coerce")
        sig = pd.to_numeric(df[signal_col], errors="coerce")

        # differenza
        diff = macd - sig

        # segno robusto: NaN → 0
        sign = np.sign(diff).fillna(0).astype("int64")

        # run-length
        grp = sign.ne(sign.shift()).cumsum()
        cnt = sign.groupby(grp).cumcount() + 1

        # applica segno (0 resta 0)
        df[out_col] = (cnt * sign).where(sign != 0, 0).astype("int64")

    def _add_macd_streaks(self,
                          macd_col: str = "MACD",
                          out_pos_col: str = "MACD_Positive_Days",
                          out_neg_col: str = "MACD_Negative_Days",
                          out_signed_col: str = "MACD_Sign_Streak"):
        """
        Aggiunge:
          - MACD_Positive_Days: giorni consecutivi con MACD > 0 (0 se MACD <= 0)
          - MACD_Negative_Days: giorni consecutivi con MACD < 0 (0 se MACD >= 0)
          - MACD_Sign_Streak: stessa logica ma con segno (>=0 conta +1,+2,... ; <0 conta -1,-2,...)
        Tutto vettorizzato (niente loop).
        """
        df = self.dataframe
        if df is None or df.empty:
            raise ValueError("DataFrame vuoto. Calcola prima gli indicatori.")
        if macd_col not in df.columns:
            raise ValueError(f"Colonna '{macd_col}' non trovata. Assicurati di aver calcolato il MACD.")

        s = pd.to_numeric(df[macd_col], errors="coerce")

        # --- Streak MACD > 0 ---
        pos_mask = s > 0
        pos_groups = (~pos_mask).cumsum()
        pos_streak = pos_mask.groupby(pos_groups).cumsum()
        df[out_pos_col] = pos_streak.where(pos_mask, 0).astype("int64")

        # --- Streak MACD < 0 ---
        neg_mask = s < 0
        neg_groups = (~neg_mask).cumsum()
        neg_streak = neg_mask.groupby(neg_groups).cumsum()
        df[out_neg_col] = neg_streak.where(neg_mask, 0).astype("int64")

        # --- Streak con segno (positiva se >0, negativa se <0, 0 se ==0) ---
        # Conta giorni consecutivi del "segno" di MACD
        sign = s.where(s == 0, s.where(s > 0, -1).where(s < 0, 1)).apply(
            lambda x: 0 if x == 0 else (1 if x > 0 else -1))
        sign = sign.astype("int64")
        grp = sign.ne(sign.shift()).cumsum()

        # conteggio assoluto per gruppo (parte da 1) poi applico segno
        cnt = sign.groupby(grp).cumcount() + 1
        signed = cnt * sign
        # se MACD == 0 → 0
        df[out_signed_col] = signed.where(sign != 0, 0).astype("int64")

    def _calculate_macd(self):
        """Versione semplificata che restituisce sempre i valori"""
        close = self.dataframe['Close'].values
        return talib.MACD(
            close,
            fastperiod=self.macd_params['fastperiod'],
            slowperiod=self.macd_params['slowperiod'],
            signalperiod=self.macd_params['signalperiod']
        )

    def set_macd_parameters(self, fastperiod=12, slowperiod=26, signalperiod=9):
        """Configura i parametri per il calcolo del MACD"""
        self.macd_params = {
            'fastperiod': fastperiod,
            'slowperiod': slowperiod,
            'signalperiod': signalperiod
        }


    def set_adx_parameters(self, period: int = 14):
        """Configura il periodo per ADX/+DI/-DI."""
        self.adx_period = int(period)

    def _calculate_adx(self):
        """Restituisce ADX, +DI e -DI."""
        high = self.dataframe['High'].values
        low = self.dataframe['Low'].values
        close = self.dataframe['Close'].values

        adx = talib.ADX(high, low, close, timeperiod=self.adx_period)
        plus_di = talib.PLUS_DI(high, low, close, timeperiod=self.adx_period)
        minus_di = talib.MINUS_DI(high, low, close, timeperiod=self.adx_period)
        return adx, plus_di, minus_di

    def _add_adx_analysis(self, df: pd.DataFrame):
        """
        Aggiunge analisi ADX:
          - ADX_Strong (True se ADX >= 25)
          - ADX_Trend ('Bullish' se +DI > -DI, altrimenti 'Bearish')
          - ADX_Cross ('BullCross' quando +DI incrocia sopra -DI, 'BearCross' viceversa, altrimenti 'None')
          - ADX_Slope ('Up'/'Down'/'Flat' sulla serie ADX)
          - ADX_Slope_Days (giorni consecutivi nello stesso slope)
          - ADX_Trend_Days (giorni consecutivi in Bullish/Bearish)
          - ADX_Bullish_Days / ADX_Bearish_Days (run-length separati)
          - ADX_Strong_Days (giorni consecutivi con ADX_Strong == True)
        """
        # --- 1) Forza del trend ---
        adx = pd.to_numeric(df['ADX'], errors='coerce')
        df['ADX_Strong'] = (adx >= 25)

        # --- 2) Direzione attuale via +DI/-DI ---
        plus_di = pd.to_numeric(df['PLUS_DI'], errors='coerce')
        minus_di = pd.to_numeric(df['MINUS_DI'], errors='coerce')

        plus_gt = (plus_di > minus_di)
        df['ADX_Trend'] = np.where(plus_gt, 'Bullish', 'Bearish')

        # --- 3) Cross tra +DI e -DI ---
        plus_gt_prev = plus_gt.shift(1).fillna(False)
        bull_cross = plus_gt & (~plus_gt_prev)  # False -> True
        bear_cross = (~plus_gt) & plus_gt_prev  # True  -> False
        df['ADX_Cross'] = np.where(bull_cross, 'BullCross',
                                   np.where(bear_cross, 'BearCross', 'None'))

        # --- 4) Slope ADX (forza in aumento/diminuzione) + durata ---
        # Riutilizza i tuoi helper generici
        df['ADX_Slope'] = self._calculate_trend(adx.values)  # 'Up'/'Down'/'Flat'
        df['ADX_Slope_Days'] = self._calculate_trend_duration(df['ADX_Slope'])

        # --- 5) Giorni consecutivi per direzione Bullish/Bearish ---
        # (a) ADX_Trend_Days via run-length generico già usato per Signal6
        df['ADX_Trend_Days'] = self._calculate_state_runlength(df['ADX_Trend']).astype('Int64')

        # (b) Contatori separati come per MACD_Positive/Negative
        bull_mask = plus_gt.fillna(False)
        bear_mask = (~plus_gt).fillna(False)

        bull_groups = (~bull_mask).cumsum()
        bear_groups = (~bear_mask).cumsum()

        bull_streak = bull_mask.groupby(bull_groups).cumsum()
        bear_streak = bear_mask.groupby(bear_groups).cumsum()

        df['ADX_Bullish_Days'] = bull_streak.where(bull_mask, 0).astype('int64')
        df['ADX_Bearish_Days'] = bear_streak.where(bear_mask, 0).astype('int64')

        # --- 6) Giorni consecutivi con ADX forte ---
        strong = df['ADX_Strong'].fillna(False)
        strong_groups = (~strong).cumsum()
        strong_streak = strong.groupby(strong_groups).cumsum()
        df['ADX_Strong_Days'] = strong_streak.where(strong, 0).astype('int64')

        return df


    def set_atr_parameters(self, period: int = 14, multiplier: float = 2.0, lookback: int = 22):
        """Configura ATR e derivati (bande/Chandelier)."""
        self.atr_period = int(period)
        self.atr_multiplier = float(multiplier)
        self.atr_lookback = int(lookback)

    def _calculate_atr(self):
        """Restituisce ATR."""
        high = self.dataframe['High'].values
        low = self.dataframe['Low'].values
        close = self.dataframe['Close'].values
        atr = talib.ATR(high, low, close, timeperiod=self.atr_period)
        return atr


    def _add_atr_derivatives(self, df: pd.DataFrame):
        """
        Aggiunge:
          - ATR_PCT (ATR in % del Close)
          - ATR_Upper / ATR_Lower (bande basate su ATR)
          - CE_Long / CE_Short (Chandelier Exit classico)
        """
        k = self.atr_multiplier
        n = self.atr_lookback

        # ATR % sul prezzo
        df['ATR_PCT'] = (df['ATR'] / df['Close']) * 100.0

        # Bande ATR “semplici”
        df['ATR_Upper'] = df['Close'] + k * df['ATR']
        df['ATR_Lower'] = df['Close'] - k * df['ATR']

        # Chandelier Exit
        highest_high = df['High'].rolling(n, min_periods=1).max()
        lowest_low = df['Low'].rolling(n, min_periods=1).min()

        df['CE_Long'] = highest_high - k * df['ATR']
        df['CE_Short'] = lowest_low + k * df['ATR']

        # (opzionale) Hint booleano: in trend long sopra CE_Long
        df['ATR_Long_OK'] = df['Close'] > df['CE_Long']
        df['ATR_Short_OK'] = df['Close'] < df['CE_Short']
        return df

    def _generate_macd_signals(self, df):
        """Genera segnali di trading basati sul MACD"""
        signals = ['Neutral'] * len(df)
        for i in range(1, len(df)):
            # Segnale di acquisto: MACD incrocia al rialzo la Signal line
            if (df['MACD'].iloc[i - 1] < df['MACD_Signal'].iloc[i - 1] and
                    df['MACD'].iloc[i] > df['MACD_Signal'].iloc[i]):
                signals[i] = 'Buy'

            # Segnale di vendita: MACD incrocia al ribasso la Signal line
            elif (df['MACD'].iloc[i - 1] > df['MACD_Signal'].iloc[i - 1] and
                  df['MACD'].iloc[i] < df['MACD_Signal'].iloc[i]):
                signals[i] = 'Sell'

        return signals

    def _add_macd_analysis(self, df):
        """Aggiunge l'analisi avanzata del MACD al DataFrame"""
        # 2. Trend istogramma
        df['MACDH_Trend'] = self._calculate_trend(df['MACD_Hist'])
        # 3. Durata trend corrente
        df['MACDH_Trend_Days'] = self._calculate_trend_duration(df['MACDH_Trend'])
        return df

    ## Funzione che calcola unico indicatore MACD
    # ---------- MCS helpers ----------
    def _tanh(self, x):
        return np.tanh(x)

    def _ema_pd(self, s, span: int):
        """
        EMA corretta con pandas.
        - Se s è ndarray/Lista, lo converte in Series indicizzata come self.dataframe.index
        - Se s è Series ma con indice diverso, lo riallinea.
        """
        if not isinstance(s, pd.Series):
            s = pd.Series(s, index=self.dataframe.index)
        else:
            # riallinea se necessario
            if not s.index.equals(self.dataframe.index):
                s = s.reindex(self.dataframe.index)
        return s.ewm(span=span, adjust=False).mean()

    def _calculate_mcs(self, L: int = 26, k: float = 1.8, beta: float = 0.2, smooth: int = 5):
        """
        Calcola il MACD Composite Score (MCS) su scala [-100, +100] e la confidenza [0..1].
        Richiede: colonne 'MACD', 'MACD_Signal', 'MACD_Hist' già presenti.
        """
        df = self.dataframe

        # Precondizione
        req = ['MACD', 'MACD_Signal', 'MACD_Hist']
        if any(col not in df.columns for col in req):
            raise ValueError("Per MCS servono 'MACD', 'MACD_Signal', 'MACD_Hist'. "
                             "Esegui prima calculate_TA_Indicators('MACD').")

        macd = df['MACD']
        signal = df['MACD_Signal']
        hist = df['MACD_Hist']
        dhist = hist.diff().fillna(0.0)

        # Scale adattive (EMA delle ampiezze)
        scale_hist  = self._ema_pd(hist.abs(),  L).replace(0, 1e-12)
        scale_macd  = self._ema_pd(macd.abs(),  L).replace(0, 1e-12)
        scale_dhist = self._ema_pd(dhist.abs(), L).replace(0, 1e-12)

        # Componenti normalizzate in [-1, +1]
        z_hist  = self._tanh(hist  / (k * scale_hist))
        z_macd0 = self._tanh(macd  / (k * scale_macd))
        z_slope = self._tanh(dhist / (k * scale_dhist))

        # Streak di pendenza costante (persistenza)
        sign_d = np.sign(dhist.values)
        streak = np.zeros_like(sign_d, dtype=float)
        for i in range(1, len(sign_d)):
            if sign_d[i] == 0:
                streak[i] = 0
            elif sign_d[i] == sign_d[i-1]:
                streak[i] = streak[i-1] + 1
            else:
                streak[i] = 1
        z_streak = self._tanh(beta * streak * np.sign(dhist))

        # Pesi (puoi esporli come parametri, qui default bilanciati)
        MCS_raw = 0.40*z_hist + 0.25*z_slope + 0.20*z_macd0 + 0.15*z_streak
        MCS = 100.0 * MCS_raw

        # Smooth leggero per uso operativo
        MCS_smoothed = self._ema_pd(MCS, smooth)

        # Confidenza 0..1
        conf = (0.5*abs(z_hist) + 0.3*abs(z_slope) + 0.2*abs(z_streak)).clip(upper=1.0)

        # Salva colonne
        df['MCS'] = MCS.round(2)
        df['MCS_Smoothed'] = MCS_smoothed.round(2)
        df['MCS_Conf'] = conf.round(3)

        # (Facoltativo: esponi anche le componenti utili al debug)
        df['MCS_z_hist'] = z_hist.round(3)
        df['MCS_z_slope'] = z_slope.round(3)
        df['MCS_z_macd0'] = z_macd0.round(3)
        df['MCS_z_streak'] = z_streak.round(3)

    def _calculate_volume_percentage(self, period: int, min_periods: Optional[int] = None):

        """
        Calcola la variazione percentuale del volume rispetto alla media mobile dei volumi.
        :param period: periodo della media mobile (es. 20 o 5)
        :param min_periods: numero minimo di valori per calcolare la media
        :return: Serie Pandas con le variazioni percentuali
        """
        if min_periods is None:
            min_periods = period
        vol_ma = self.dataframe['Volume'].rolling(window=period, min_periods=min_periods).mean()
        return ((self.dataframe['Volume'] - vol_ma) / vol_ma) * 100


    ################ ORCHESTRATION CALCOLO INDICATORI IN BASE A STRINGA

    def calculate_TA_Indicators(self, indicators='MACD'):
        """
        Calcola gli indicatori specificati e aggiorna il DataFrame principale
        """
        indicators = [ind.strip().upper() for ind in indicators.split(',')]

        #Variazione percentuale Volumi rispetto a media mobile

        # ADX (+DI / -DI)
        if 'ADX' in indicators:
            adx, pdi, mdi = self._calculate_adx()
            self.dataframe['ADX'] = adx
            self.dataframe['PLUS_DI'] = pdi
            self.dataframe['MINUS_DI'] = mdi
            self._add_adx_analysis(self.dataframe)

        # ATR (+ derivati)
        if 'ATR' in indicators:
            atr = self._calculate_atr()
            self.dataframe['ATR'] = atr
            self._add_atr_derivatives(self.dataframe)

        if 'VOL_PERC' in indicators or 'VOLUME' in indicators:
            self.dataframe['Vol_Perc_vs_MA20'] = self._calculate_volume_percentage(20)
            self.dataframe['Vol_Perc_vs_MA5'] = self._calculate_volume_percentage(5)
            # Crea anche le metriche di liquidità + flag finale
            self._add_liquidity_columns()


        # MACD Calculation
        if 'MACD' in indicators:
            macd, signal, hist = self._calculate_macd()
            self.dataframe['MACD'] = macd
            self.dataframe['MACD_Signal'] = signal
            self.dataframe['MACD_Hist'] = hist
            self._add_macd_analysis(self.dataframe)
            self._calculate_mcs(L=26, k=1.8, beta=0.2, smooth=5)
            self._add_macd_streaks()
            self._add_macd_vs_signal_streak()

        # MA and EMA Calculation
        for key in indicators:
            match = re.search(r'^(MA|EMA)_(\d+)$', key)
            if match:
                ma_label = match.group(1)  # 'MA' o 'EMA'
                period = int(match.group(2))  # es. 30
                ma_type = 0 if ma_label == 'MA' else 1
                self.set_moving_average_parameters(period, ma_type)
                ma = self._calculate_ma()
                self.dataframe[f'{ma_label}_{period}'] = ma

        if 'RSI' in indicators:
            self.dataframe['RSI'] = self._calculate_rsi()
            self._add_rsi_analysis(self.dataframe)

        # Williams %R - Correzione qui
        if 'WILLR' in indicators or 'WILLIAMS' in indicators:
            try:
                williams_values = self._calculate_williams()
                if williams_values is not None:
                    self.dataframe['Williams_R'] = williams_values
                    self._add_williams_analysis(self.dataframe)
            except Exception as e:
                print(f"Errore nel calcolo Williams %R per {self.ticker}: {e}")
                # Crea colonne vuote per evitare errori
                self.dataframe['Williams_R'] = np.nan
                self.dataframe['WILLR_Trend'] = 'Flat'
                self.dataframe['WILLR_Trend_Days'] = 0
                self.dataframe['WILLR_Overbought'] = False
                self.dataframe['WILLR_Oversold'] = False
                self.dataframe['WILLR_Neutral'] = True

        if 'STOCH' in indicators:
            slowk, slowd = self._calculate_stochastic()
            self.dataframe['Stoch_K'] = slowk
            self.dataframe['Stoch_D'] = slowd
            self._add_stochastic_analysis(self.dataframe)

        if 'ALLIGATOR' in indicators:
            jaw, teeth, lips = self._calculate_alligator()
            self.dataframe['Alligator_Jaw'] = jaw
            self.dataframe['Alligator_Teeth'] = teeth
            self.dataframe['Alligator_Lips'] = lips

        if 'PCTV' in indicators:
            self._calculate_price_changes()

        if 'SAR' in indicators:
            self.dataframe['SAR'] = self._calculate_sar()
            self._add_sar_analysis(self.dataframe)

        # Restituisci il DataFrame aggiornato
        self.dataframe = self.dataframe.round(3)



    def generate_signal_SAR_MA(
            self,
            *,
            cond: Optional[pd.Series] = None,
            use_ema30: int = 1,
            use_ema50: int = 0,
            use_sar: int = 1,
            column: str = "Cond_Streak",
            zero_when_false: bool = True,  # se False mette NaN quando la cond è falsa
            cap_at: Optional[int] = None,  # opzionale: limita il massimo (es. 10)
            reset_column: bool = True,
            flip_col: str = "SAR_Flip_RunDown"  # nuovo: conta i giorni consecutivi con SAR_Above_Price == False
    ) -> pd.Series:
        """
        - Se `cond` è None, la condizione è: (Close > EMA_30) AND/OR (Close > EMA_50) AND/OR (SAR < Close)
          con AND su tutte le condizioni attivate (flag = 1).
        - Scrive la lunghezza delle sequenze vere in `column` (es. 0,0,1,2,3,0,...) e la ritorna.
        - In più crea `flip_col` con il numero di giorni consecutivi da quando `SAR_Above_Price` è False:
          0 quando `SAR_Above_Price` è True; 1,2,3... finché resta False.
        """
        import numpy as np
        import pandas as pd

        df = self.dataframe
        if df is None or df.empty:
            raise ValueError("DataFrame vuoto.")

        # ---------- Costruzione condizione se non fornita ----------
        if cond is None:
            needed = ['Close']
            if use_ema30: needed.append('EMA_30')
            if use_ema50: needed.append('EMA_50')
            if use_sar:   needed.append('SAR')

            missing = [c for c in needed if c not in df.columns]
            if missing:
                raise ValueError(f"Mancano colonne: {missing}. Calcola prima gli indicatori richiesti.")

            if (use_ema30 + use_ema50 + use_sar) == 0:
                raise ValueError("Nessuna condizione attivata.")

            cond = pd.Series(True, index=df.index)
            if use_ema30:
                cond &= (df['Close'] > df['EMA_30'])
            if use_ema50:
                cond &= (df['Close'] > df['EMA_50'])
            if use_sar:
                cond &= (df['SAR'] < df['Close'])
        else:
            cond = cond.reindex(df.index).fillna(False).astype(bool)

        # ---------- Streak (run-length) dei True ----------
        grp = cond.ne(cond.shift()).cumsum()
        streak = cond.groupby(grp).cumcount() + 1
        streak = streak.where(cond, 0 if zero_when_false else np.nan)

        if cap_at is not None:
            streak = streak.clip(upper=int(cap_at))

        if reset_column or (column not in df.columns):
            df[column] = 0 if zero_when_false else np.nan
        df[column] = streak

        # ---------- Contatore giorni con SAR_Above_Price == False ----------
        # Se non presente, derivala da SAR e Close
        if 'SAR_Above_Price' not in df.columns:
            if ('SAR' in df.columns) and ('Close' in df.columns):
                df['SAR_Above_Price'] = df['SAR'] > df['Close']
            else:
                raise ValueError("Per il conteggio giorni flip SAR servono 'SAR_Above_Price' oppure ('SAR' e 'Close').")

        sar_above = df['SAR_Above_Price'].astype(bool)
        sar_below = ~sar_above  # True quando SAR è sotto al prezzo

        # run-length sui tratti con SAR sotto (False per SAR_Above_Price)
        grp_below = sar_below.ne(sar_below.shift()).cumsum()
        run_below = sar_below.groupby(grp_below).cumcount() + 1
        run_below = run_below.where(sar_below, 0).astype(int)  # 0 quando SAR_Above_Price è True

        df[flip_col] = run_below

        return streak


    def generate_signal_generic(self, long_conditions=None, short_conditions=None,
                                signal_column='Signal', reset_signal=True):
        """Genera segnali dinamicamente con condizioni separate per long e short."""
        if reset_signal:
            self.dataframe[signal_column] = 0

        if long_conditions:
            long_cond = pd.Series(True, index=self.dataframe.index)
            for c in long_conditions:
                long_cond &= c(self.dataframe)
            self.dataframe.loc[long_cond, signal_column] = 1

        if short_conditions:
            short_cond = pd.Series(True, index=self.dataframe.index)
            for c in short_conditions:
                short_cond &= c(self.dataframe)
            self.dataframe.loc[short_cond, signal_column] = -1

    def start_Signals_Generation(self, json_long_strategy=None, json_short_strategy=None,
                                 signal_name='Trading_Signal'):
        """Genera segnali da condizioni JSON con supporto per long/short."""
        long_conditions = []
        if json_long_strategy:
            long_spec = create_conditions_from_json(json_long_strategy)
            long_conditions = build_conditions(self.dataframe, long_spec)

        short_conditions = []
        if json_short_strategy:
            short_spec = create_conditions_from_json(json_short_strategy)
            short_conditions = build_conditions(self.dataframe, short_spec)

        self.generate_signal_generic(
            long_conditions=long_conditions,
            short_conditions=short_conditions,
            signal_column=signal_name
        )

    # TechnicalAnalyzer.py



    def backTestingVBT(
            self,
            plotChart: bool = False,
            freq: Optional[str] = None,
            init_cash: float = 10000,
            fees: float = 0.001,
    ):
        """
        Replica esatta della logica di backTestingVBTv1:
          - entries := (Trading_Signal == 1)
          - exits   := (Trading_Signal == -1)
          - nessuno shift / nessuna logica di transizione
          - nessun accumulo: vectorbt per default non rientra se la posizione è già aperta
        """
        import pandas as pd
        import vectorbt as vbt

        df = self.dataframe.copy()
        if df.index.dtype.kind != 'M':
            df.index = pd.to_datetime(df.index)

        # Inferisci frequenza se non fornita (serve a vbt per le metriche)
        try:
            inferred = pd.infer_freq(df.index)
        except Exception:
            inferred = None
        use_freq = freq or inferred or "1D"

        # Segnale richiesto
        if "Trading_Signal" not in df.columns:
            raise KeyError("Colonna 'Trading_Signal' non trovata nel dataframe")

        sig = df["Trading_Signal"].fillna(0).astype(int)

        # === LOGICA V1 (identica) ===
        entries = (sig == 1)  # bool Series
        exits = (sig == -1)  # bool Series

        # Persisti per debug/plot *esattamente* come v1
        self.dataframe["Entry_Signal"] = entries.astype(int)
        self.dataframe["Exit_Signal"] = exits.astype(int)

        # Portfolio vbt (accumulate=False di default -> nessun riacquisto in posizione)
        pf = vbt.Portfolio.from_signals(
            close=df["Close"],
            entries=entries,
            exits=exits,
            init_cash=init_cash,
            fees=fees,
            freq=use_freq,
        )

        stats = pf.stats()

        if plotChart:
            try:
                pf.plot().show()
            except Exception:
                pass

        return stats

    def backTestingVBTv1(self, plotChart=False):
        df = self.dataframe.copy()

        entries = (df['Trading_Signal'] == 1)
        exits = (df['Trading_Signal'] == -1)

        # Persisti anche nel dataframe principale
        self.dataframe['Entry_Signal'] = entries.astype(int)
        self.dataframe['Exit_Signal'] = exits.astype(int)
        df['Entry_Signal'] = self.dataframe['Entry_Signal']
        df['Exit_Signal'] = self.dataframe['Exit_Signal']

        portfolio = vbt.Portfolio.from_signals(
            close=df["Close"],
            entries=entries,  # booleans vanno benissimo
            exits=exits,
            init_cash=10000,
            fees=0.001,
            freq="1D"
        )

        #print(portfolio.stats())
        # utile per debug rapido
        #print(df[['Close', 'Trading_Signal', 'Entry_Signal', 'Exit_Signal']].tail(10).to_string())

        if plotChart:
            portfolio.plot().show()
        return portfolio.stats()

    def backTestingVBTv0(self,plotChart=False):
        df = self.dataframe.copy()
        entry = (df['Trading_Signal'] == 1)
        exit = (df['Trading_Signal'] == -1)
        # Persisti anche nel dataframe principale
        self.dataframe['Entry_Signal'] = entry.astype(int)
        self.dataframe['Exit_Signal'] = exit.astype(int)
        df['Entry_Signal'] = self.dataframe['Entry_Signal']
        df['Exit_Signal'] = self.dataframe['Exit_Signal']

        portfolio = vbt.Portfolio.from_signals(
            close=self.dataframe["Close"],
            entries=entry.astype(int),
            exits=exit.astype(int),
            init_cash=10000,
            fees=0.001
        )

        #print(portfolio.stats())
        if plotChart:
            portfolio.plot().show()
        return portfolio.stats()


    ### Backtesting con operatori logici
    ### Backtesting con operatori logici
    def backTestingVBTLogic(
            self,
            plotChart: bool = False,
            freq: Optional[str] = None,
            init_cash: float = 10000,
            fees: float = 0.001,
            # >>> NOVITÀ: se passi questi, generiamo Trading_Signal qui sotto
            json_long: Optional[list] = None,
            json_short: Optional[list] = None,
            long_logic: str = "AND",  # "AND" oppure "OR"
            short_logic: str = "AND",  # "AND" oppure "OR"
            signal_name: str = "Trading_Signal",
            prefer_short_on_conflict: bool = True,  # in caso di conflitto, vince l'exit/short
    ):
        """
        Backtest stile VBTv1:
          - entries := (Trading_Signal == 1)
          - exits   := (Trading_Signal == -1)
        In più (opzionale):
          - se fornisci json_long/json_short, costruiamo Trading_Signal combinando
            tutte le condizioni in AND oppure tutte in OR (impostabile).
        """
        import pandas as pd
        import numpy as np
        import vectorbt as vbt

        # ---------------- helpers semplici AND/OR ----------------
        def _op_series(left, op, right):
            if op == ">":
                return left > right
            elif op == "<":
                return left < right
            elif op == ">=":
                return left >= right
            elif op == "<=":
                return left <= right
            elif op == "==":
                return left == right
            elif op == "!=":
                return left != right
            raise ValueError(f"Operatore non supportato: {op}")

        def _single_rule_mask(df, rule):
            # rule: {"col":..., "op":..., "val":...}  oppure {"col":..., "op":..., "col2":...}
            col = rule.get("col")
            op = rule.get("op")
            if col is None or op is None:
                raise ValueError(f"Condizione malformata: {rule}")

            if ("val" in rule) == ("col2" in rule):
                raise ValueError(f"Specificare esattamente uno tra 'val' e 'col2' in {rule}")

            # se la colonna non esiste => tutto False (condizione impossibile)
            if col not in df.columns:
                return pd.Series(False, index=df.index)

            left = df[col]
            if "col2" in rule:
                c2 = rule["col2"]
                if c2 not in df.columns:
                    return pd.Series(False, index=df.index)
                right = df[c2]
            else:
                right = rule["val"]

            # prova a numerizzare dove possibile, così gestiamo bene confronti numerici
            try:
                left = pd.to_numeric(left, errors="ignore")
            except Exception:
                pass
            if isinstance(right, pd.Series):
                try:
                    right = pd.to_numeric(right, errors="ignore")
                except Exception:
                    pass

            mask = _op_series(left, op, right)
            mask = mask.fillna(False).astype(bool)
            return mask

        def _combine_all(df, rules, logic: str):
            """Combina tutte le rules con AND o OR."""
            if not rules:
                return pd.Series(False, index=df.index)
            masks = [_single_rule_mask(df, r) for r in rules]
            out = masks[0].copy()
            if str(logic).upper() == "AND":
                for m in masks[1:]:
                    out &= m
            elif str(logic).upper() == "OR":
                for m in masks[1:]:
                    out |= m
            else:
                raise ValueError("logic deve essere 'AND' oppure 'OR'")
            return out.fillna(False)

        # ---------------- dati & frequenza ----------------
        df = self.dataframe.copy()
        if df.index.dtype.kind != 'M':
            df.index = pd.to_datetime(df.index)

        try:
            inferred = pd.infer_freq(df.index)
        except Exception:
            inferred = None
        use_freq = freq or inferred or "1D"

        # ---------------- (opzionale) costruzione Trading_Signal dai JSON ----------------
        if json_long is not None or json_short is not None:
            long_mask = _combine_all(df, json_long or [], long_logic)
            short_mask = _combine_all(df, json_short or [], short_logic)

            sig = pd.Series(0, index=df.index, dtype=int)
            sig[long_mask] = 1
            if prefer_short_on_conflict:
                # se entrambe vere nella stessa barra, prevale lo short (exit)
                sig[short_mask] = -1
            else:
                # altrimenti scrivi lo short solo dove NON c'è già long
                sig[(short_mask) & (~long_mask)] = -1

            df[signal_name] = sig
            # aggiorna anche il dataframe principale
            self.dataframe[signal_name] = sig

        # ---------------- uso esatto della logica v1 ----------------
        if signal_name not in df.columns:
            raise KeyError(f"Colonna '{signal_name}' non trovata nel dataframe")

        sig = df[signal_name].fillna(0).astype(int)

        entries = (sig == 1)  # identico a v1
        exits = (sig == -1)  # identico a v1

        # ---------- Giorni consecutivi in LONG / SHORT ----------
        # 1) Regime: propaga l’ultimo segnale non nullo (gli 0 non spezzano)
        regime = sig.replace(0, np.nan).ffill().fillna(0).astype(int)

        # 2) Booleani di stato
        is_long = regime.eq(1)
        is_short = regime.eq(-1)

        # 3) Contatori (gli 0 contano dentro la striscia)
        long_days = is_long.groupby((~is_long).cumsum()).cumsum().astype(int)
        short_days = is_short.groupby((~is_short).cumsum()).cumsum().astype(int)

        # Persisti per debug/plot
        self.dataframe["Entry_Signal"] = entries.astype(int)
        self.dataframe["Exit_Signal"] = exits.astype(int)



        # sig: Serie con valori in {-1, 0, 1}
        sig = df[signal_name].fillna(0).astype(int)

        # 1) Regime: propaga l'ultimo segnale non nullo in avanti (gli 0 non spezzano)
        regime = sig.replace(0, np.nan).ffill().fillna(0).astype(int)

        # 2) Booleani di stato
        is_long = regime.eq(1)
        is_short = regime.eq(-1)

        # 3) Contatori di giorni consecutivi in LONG/SHORT (gli 0 contano dentro la striscia)
        long_days = (
            is_long.groupby((~is_long).cumsum()).cumsum()
        )
        short_days = (
            is_short.groupby((~is_short).cumsum()).cumsum()
        )

        long_days = long_days.fillna(0).astype(int)
        short_days = short_days.fillna(0).astype(int)

        # 4) Salva
        df["Long_Days"] = long_days
        df["Short_Days"] = short_days

        self.dataframe.loc[df.index, "Long_Days"] = long_days.values
        self.dataframe.loc[df.index, "Short_Days"] = short_days.values

        # ---------------- portfolio vectorbt ----------------
        pf = vbt.Portfolio.from_signals(
            close=df["Close"],
            entries=entries,
            exits=exits,
            init_cash=init_cash,
            fees=fees,
            freq=use_freq,
        )

        stats = pf.stats()

        if plotChart:
            try:
                pf.plot().show()
            except Exception:
                pass

        return stats

    ### ALLIGATOR ANALISI
    def calculate_alligator_signal6(self, compute_trend_days: bool = True, family: bool = False):
        """
        Calcola Signal6 basato sull'indicatore Alligator e (opzionale) la colonna
        'Signal6_Trend_Days' con i giorni consecutivi nello stesso stato.

        Args:
            compute_trend_days (bool): se True aggiunge 'Signal6_Trend_Days'
            family (bool): se True conta i giorni raggruppando per famiglie
                           (Uptrend, Downtrend, sleep, wakeup)
        """
        # Verifica prerequisiti
        required_cols = ['Alligator_Lips', 'Alligator_Teeth', 'Alligator_Jaw', 'Close']
        missing = [c for c in required_cols if c not in self.dataframe.columns]
        if missing:
            raise ValueError(
                f"Mancano colonne {missing}. Esegui prima calculate_TA_Indicators('ALLIGATOR')."
            )

        df = self.dataframe

        # inizializza
        df['Signal6'] = 'sleep1'

        close = df['Close']
        lips = df['Alligator_Lips']  # veloce (verde)
        teeth = df['Alligator_Teeth']  # intermedia (rosso)
        jaw = df['Alligator_Jaw']  # lenta (blu)

        # ----------------- DOWNTREND & REVERSAL -----------------
        # Struttura base down: Lips > Close < Teeth < Jaw e Lips < Teeth < Jaw
        down_mask = (lips > close) & (lips < teeth) & (teeth < jaw)
        df.loc[down_mask, 'Signal6'] = 'Downtrend'

        # Reversal progressivi nella struttura di downtrend (sovrascrivono)
        rev1 = (lips < close) & (lips < teeth) & (teeth < jaw)
        df.loc[rev1, 'Signal6'] = 'Downtrend_revS3Sig+'

        rev2 = (teeth < close) & (lips < teeth) & (teeth < jaw)
        df.loc[rev2, 'Signal6'] = 'Downtrend_revS3Sig++'

        rev3 = (jaw < close) & (lips < teeth) & (teeth < jaw)
        df.loc[rev3, 'Signal6'] = 'Downtrend_revS3Sig+++'

        # ----------------- UPTREND (mutuamente esclusivo per fascia) -----------------
        up_struct = (jaw < teeth) & (teeth < lips)

        # sotto o uguale alla Jaw -> più debole
        up_weak3 = (close <= jaw) & up_struct
        df.loc[up_weak3, 'Signal6'] = 'Uptrend---'

        # tra Jaw e Teeth
        up_weak2 = (jaw < close) & (close <= teeth) & up_struct
        df.loc[up_weak2, 'Signal6'] = 'Uptrend--'

        # tra Teeth e Lips
        up_weak1 = (teeth < close) & (close <= lips) & up_struct
        df.loc[up_weak1, 'Signal6'] = 'Uptrend-'

        # sopra la Lips -> più forte
        up_strong = (lips < close) & up_struct
        df.loc[up_strong, 'Signal6'] = 'Uptrend'

        # ----------------- SLEEP (alligator “dorme”) -----------------
        sleep1 = (jaw < lips) & (lips < teeth)
        df.loc[sleep1, 'Signal6'] = 'sleep1'

        sleep2 = (lips < jaw) & (jaw < teeth)
        df.loc[sleep2, 'Signal6'] = 'sleep2'

        # ----------------- WAKEUP (alligator si sveglia) -----------------
        # wakeup1: Teeth < Lips < Jaw
        wake1_struct = (teeth < lips) & (lips < jaw)
        df.loc[wake1_struct & (close <= lips), 'Signal6'] = 'wakeup1-'  # debole
        df.loc[wake1_struct & (close > lips), 'Signal6'] = 'wakeup1'  # forte

        # wakeup2: Teeth < Jaw < Lips
        wake2_struct = (teeth < jaw) & (jaw < lips)
        df.loc[wake2_struct & (close <= lips), 'Signal6'] = 'wakeup2-'  # debole (come v0)
        df.loc[wake2_struct & (close > lips), 'Signal6'] = 'wakeup2'  # forte (senza asterisco)

        # ----------------- MARCATURA PRIMO GIORNO CON "*" -----------------
        # Nota: qui usiamo la "famiglia" per evitare che l'asterisco persista ogni giorno.
        prev = df['Signal6'].shift(1).fillna('')

        up_first_mask = (df['Signal6'] == 'Uptrend') & (~prev.str.startswith('Uptrend'))
        down_first_mask = (df['Signal6'] == 'Downtrend') & (~prev.str.startswith('Downtrend'))
        wake2_first_mask = (df['Signal6'] == 'wakeup2') & (~prev.str.startswith('wakeup2'))

        df.loc[up_first_mask, 'Signal6'] = 'Uptrend*'
        df.loc[down_first_mask, 'Signal6'] = 'Downtrend*'
        df.loc[wake2_first_mask, 'Signal6'] = 'wakeup2*'

        # ----------------- Trend days opzionale -----------------
        if compute_trend_days:
            self._add_signal6_trend_days(family=family)

        return df['Signal6']


    def get_signal6_description(self, signal_value):
        """
        Restituisce una descrizione del significato del segnale Signal6

        Args:
            signal_value (str): Valore del Signal6

        Returns:
            str: Descrizione del segnale
        """
        descriptions = {
            'sleep1': 'Alligator dorme - Mercato laterale (Jaw < Lips < Teeth)',
            'sleep2': 'Alligator dorme - Mercato laterale (Lips < Jaw < Teeth)',
            'wakeup1': 'Alligator si sveglia - Possibile inizio trend (Teeth < Lips < Jaw, Price > Lips)',
            'wakeup1-': 'Alligator si sveglia - Cautela (Teeth < Lips < Jaw, Price < Lips)',
            'wakeup2': 'Alligator sveglio - Trend in formazione (Teeth < Jaw < Lips, Price > Lips)',
            'wakeup2*': 'PRIMO giorno wakeup2 - Segnale di entrata possibile',
            'wakeup2-': 'Alligator sveglio - Trend debole (Teeth < Jaw < Lips, Price < Lips)',
            'Uptrend': 'UPTREND forte - Price sopra tutte le linee Alligator',
            'Uptrend*': 'PRIMO giorno uptrend - Segnale di entrata LONG',
            'Uptrend-': 'Uptrend debole - Price sotto Lips ma struttura rialzista',
            'Uptrend--': 'Uptrend molto debole - Price sotto Teeth',
            'Uptrend---': 'Uptrend debolissimo - Price sotto Jaw',
            'Downtrend': 'DOWNTREND forte - Price sotto Lips, struttura ribassista',
            'Downtrend*': 'PRIMO giorno downtrend - Segnale di entrata SHORT',
            'Downtrend_revS3Sig+': 'Downtrend con price sopra Lips - Possibile inversione',
            'Downtrend_revS3Sig++': 'Downtrend con price sopra Teeth - Inversione probabile',
            'Downtrend_revS3Sig+++': 'Downtrend con price sopra Jaw - Inversione forte'
        }

        return descriptions.get(signal_value, f'Segnale sconosciuto: {signal_value}')

    def analyze_signal6_distribution(self):
        """
        Analizza la distribuzione dei segnali Signal6 nel dataset

        Returns:
            pandas.Series: Conteggio di ciascun tipo di segnale
        """
        if 'Signal6' not in self.dataframe.columns:
            self.calculate_alligator_signal6()

        distribution = self.dataframe['Signal6'].value_counts()

        print(f"\n=== DISTRIBUZIONE SIGNAL6 per {self.ticker} ===")
        for signal, count in distribution.items():
            percentage = (count / len(self.dataframe)) * 100
            print(f"{signal:20s}: {count:4d} ({percentage:5.1f}%)")
            print(f"{'':22s} {self.get_signal6_description(signal)}")
            print()

        return distribution

    ## Beging Calcola durante trend S6 signals
    def _calculate_state_runlength(self, series: pd.Series) -> pd.Series:
        """
        Ritorna per ogni riga il numero di giorni consecutivi in cui `series` rimane uguale.
        Esempio: A A A B B A  -> 1 2 3 1 2 1
        """
        s = series.astype('object')  # evitiamo problemi con categorie/NaN
        # Gruppi di run: ogni volta che il valore cambia, incrementa l'id di gruppo
        grp = s.ne(s.shift()).cumsum()
        # Conteggio cumulato per gruppo (parte da 0, somma 1)
        run = s.groupby(grp).cumcount() + 1
        # Mantieni NaN dove l’etichetta è NaN
        return run.where(s.notna())

    def _add_signal6_trend_days(self, family: bool = False) -> None:
        """
        Crea la colonna 'Signal6_Trend_Days' contando i giorni consecutivi
        in cui 'Signal6' resta nello stesso stato.

        Args:
            family (bool): se True accorpa le varianti in famiglie:
                - Uptrend*, Uptrend-, Uptrend--, Uptrend--- -> 'Uptrend'
                - Downtrend*, Downtrend_revS3Sig+, ...      -> 'Downtrend'
                - sleep1, sleep2                            -> 'sleep'
                - wakeup1, wakeup1-, wakeup2, wakeup2*     -> 'wakeup'
        """
        if 'Signal6' not in self.dataframe.columns:
            raise ValueError("Manca la colonna 'Signal6'. Esegui prima calculate_alligator_signal6().")

        base = self.dataframe['Signal6'].astype(str)

        if family:
            # Estrae la "famiglia" principale dal testo
            fam = (
                base.str.extract(r'^(Uptrend|Downtrend|sleep|wakeup)', expand=False)
                    .where(lambda x: x.notna(), base)  # se non matcha, lascia il valore originale
            )
            self.dataframe['Signal6_Trend_Days'] = self._calculate_state_runlength(fam)
        else:
            # Conta i giorni per lo stato esatto (inclusi -, +, * ecc.)
            self.dataframe['Signal6_Trend_Days'] = self._calculate_state_runlength(base)

        # Converto a int dove possibile (lascia NaN dove opportuno)
        self.dataframe['Signal6_Trend_Days'] = (
            self.dataframe['Signal6_Trend_Days'].astype('Int64')
        )
    ## End Calcolare durate trend S6 signals
    ## ALLIGATOR FINE ANALISI

    def generate_stoch_reversal_signals(
            self,
            *,
            signal_name: str = "Trading_Signal",
            entry_col: str = "Entry_Signal",
            exit_col: str = "Exit_Signal",
            prefer_short_on_conflict: bool = True,
            execute_next_bar: bool = False,  # True se l'esecuzione avviene alla barra successiva
    ) -> pd.DataFrame:
        """
        Genera segnali (LONG/SHORT) con le regole:

          LONG:
            Stoch_K <= 30
            SK_Trend == "Up"
            Stoch_K > Stoch_D
            SK_Trend_Days >= 1

          SHORT:
            Stoch_K >= 80
            SK_Trend == "Down"
            Stoch_K < Stoch_D
            SK_Trend_Days >= 1

        Scrive le colonne:
          - signal_name (default 'Trading_Signal'): 1 = long, -1 = short, 0 = flat
          - entry_col   (default 'Entry_Signal'):   1 dove c'è ingresso long
          - exit_col    (default 'Exit_Signal'):    1 dove c'è uscita/short

        Ritorna il DataFrame aggiornato (self.dataframe).
        """

        df = self.dataframe
        if df is None or df.empty:
            raise ValueError("DataFrame vuoto: scarica/calcola prima i dati.")

        # Assicurati che Stoch_K/Stoch_D ci siano; se mancano, calcolali
        needed = ["Stoch_K", "Stoch_D"]
        if not all(c in df.columns for c in needed):
            # calcola solo lo STOCH se non presente
            slowk, slowd = self._calculate_stochastic()
            df["Stoch_K"] = slowk
            df["Stoch_D"] = slowd

        # Assicurati che SK_Trend / SK_Trend_Days ci siano
        if ("SK_Trend" not in df.columns) or ("SK_Trend_Days" not in df.columns):
            self._add_stochastic_analysis(df)  # crea SK_Trend e SK_Trend_Days

        # Costruzione maschere vettoriali
        sk = pd.to_numeric(df["Stoch_K"], errors="coerce")
        sd = pd.to_numeric(df["Stoch_D"], errors="coerce")
        tr = df["SK_Trend"].astype(str)
        tday = pd.to_numeric(df["SK_Trend_Days"], errors="coerce").fillna(0)

        long_mask = (
                (sk <= 30) &
                (tr == "Up") &
                (sk > sd) &
                (tday >= 1)
        )

        short_mask = (
                (sk >= 80) &
                (tr == "Down") &
                (sk < sd) &
                (tday >= 1)
        )

        # Eventuale esecuzione "next bar"
        if execute_next_bar:
            long_mask = long_mask.shift(1, fill_value=False)
            short_mask = short_mask.shift(1, fill_value=False)

        # Costruisci il segnale unico con gestione conflitti
        sig = pd.Series(0, index=df.index, dtype=int)
        sig[long_mask] = 1
        if prefer_short_on_conflict:
            sig[short_mask] = -1
        else:
            sig[(short_mask) & (~long_mask)] = -1

        # Persisti
        df[signal_name] = sig

        # Entrate/Uscite (compatibili con backTestingVBT/backTestingVBTLogic)
        df[entry_col] = (sig == 1).astype(int)
        df[exit_col] = (sig == -1).astype(int)

        return df

    def calculate_technical_score(self, weights=None):
        """
        Calcola uno score tecnico complessivo (0-100).
        Versione con ADX & ATR inclusi e senza Williams %R.
        """
        import numpy as np
        import pandas as pd

        if weights is None:
            # Verranno normalizzati più sotto, i valori qui sono "relativi"
            weights = {
                'MACD': 0.18,
                'RSI': 0.12,
                'STOCH': 0.10,
                'MA_TREND': 0.12,
                'VOLUME': 0.08,
                'SAR': 0.06,
                'PCTV': 0.06,
                'ALLIGATOR': 0.08,
                'Signal6': 0.12,
                'ADX': 0.12,  # <-- nuovo
                'ATR': 0.06,  # <-- nuovo
            }
        else:
            # assicurati che Signal6 esista anche in pesi custom (fallback)
            if 'Signal6' not in weights:
                weights = {**weights, 'Signal6': 0.12}

        # normalizza pesi a somma 1
        total = sum(weights.values())
        weights = {k: (v / total) for k, v in weights.items()}

        # assicura Signal6
        if 'Signal6' not in self.dataframe.columns:
            self.calculate_alligator_signal6()

        df = self.dataframe
        score = pd.Series(0.0, index=df.index)

        # --- MACD ---
        if all(c in df.columns for c in ['MACD', 'MACD_Signal']):
            macd_score = 0
            macd_score += (df['MACD'] > df['MACD_Signal']).astype(int) * 10
            if 'MACDH_Trend' in df.columns:
                macd_score += (df['MACDH_Trend'] == 'Up').astype(int) * 10
            if 'MACDH_Trend_Days' in df.columns:
                macd_score += np.minimum(df['MACDH_Trend_Days'], 5) * 1
            score += macd_score * weights.get('MACD', 0)

        # --- RSI ---
        if 'RSI' in df.columns:
            rsi_score = 0
            rsi_score += (df['RSI'] > 50).astype(int) * 10
            if 'RSI_Trend' in df.columns:
                rsi_score += (df['RSI_Trend'] == 'Up').astype(int) * 5
            rsi_score += (df['RSI'] > 70).astype(int) * 2
            rsi_score += (df['RSI'] < 30).astype(int) * -5
            score += rsi_score * weights.get('RSI', 0)

        # --- STOCH ---
        if all(c in df.columns for c in ['Stoch_K', 'Stoch_D']):
            stoch_score = 0
            stoch_score += (df['Stoch_K'] > df['Stoch_D']).astype(int) * 10
            stoch_score += (df['Stoch_K'] > 80).astype(int) * -3
            stoch_score += (df['Stoch_K'] < 20).astype(int) * 5
            score += stoch_score * weights.get('STOCH', 0)

        # --- MA trend (EMA30/EMA50 + prezzo sopra EMA30) ---
        if all(c in df.columns for c in ['EMA_30', 'EMA_50', 'Close']):
            ma_score = 0
            ma_score += (df['EMA_30'] > df['EMA_50']).astype(int) * 10
            ma_score += (df['Close'] > df['EMA_30']).astype(int) * 5
            score += ma_score * weights.get('MA_TREND', 0)

        # --- Volume (> MA20) ---
        if 'Volume' in df.columns:
            avg_volume = df['Volume'].rolling(20, min_periods=1).mean()
            volume_score = (df['Volume'] > avg_volume).astype(int) * 10
            score += volume_score * weights.get('VOLUME', 0)

        # --- Parabolic SAR (sotto il prezzo = long bias) ---
        if all(c in df.columns for c in ['SAR', 'Close']):
            sar_score = (df['SAR'] < df['Close']).astype(int) * 10
            score += sar_score * weights.get('SAR', 0)

        # --- PCTV (5 giorni) ---
        if 'PCTV_5D' in df.columns:
            pct = df['PCTV_5D'].fillna(0.0)
            pct_score = np.where(pct > 0, np.minimum(pct * 2, 5), np.maximum(pct * 2, -5))
            score += pct_score * weights.get('PCTV', 0)

        # --- Alligator (ordine + prezzo sopra le 3 linee) ---
        if all(c in df.columns for c in ['Alligator_Jaw', 'Alligator_Teeth', 'Alligator_Lips']):
            alligator_score = 0
            alligator_score += (
                                       (df['Alligator_Lips'] > df['Alligator_Teeth']) &
                                       (df['Alligator_Teeth'] > df['Alligator_Jaw'])
                               ).astype(int) * 5
            if 'Close' in df.columns:
                alligator_score += (
                                           (df['Close'] > df['Alligator_Lips']) &
                                           (df['Close'] > df['Alligator_Teeth']) &
                                           (df['Close'] > df['Alligator_Jaw'])
                                   ).astype(int) * 5
            score += alligator_score * weights.get('ALLIGATOR', 0)

        # === NUOVO: ADX ===
        if 'ADX' in df.columns:
            adx_score = 0

            # helper per cast numerico sicuro
            def _num(col, default=0.0):
                s = df[col] if col in df.columns else pd.Series(default, index=df.index)
                s = pd.to_numeric(s, errors='coerce')
                return s.fillna(default)

            # Direzione: DI+ vs DI- (supporta PLUS_DI/+DI/+DX e MINUS_DI/-DI/-DX)
            def _pick_plus_minus():
                plus_candidates = ['PLUS_DI', '+DI', '+DX']
                minus_candidates = ['MINUS_DI', '-DI', '-DX']
                p = next((c for c in plus_candidates if c in df.columns), None)
                m = next((c for c in minus_candidates if c in df.columns), None)
                return (_num(p) if p else None), (_num(m) if m else None)

            di_plus, di_minus = _pick_plus_minus()
            if di_plus is not None and di_minus is not None:
                adx_score += (di_plus > di_minus).astype(int) * 8

            adx = _num('ADX')
            adx_score += (adx >= 25).astype(int) * 6
            adx_score += np.clip((adx - 20) / 20.0, 0, 1) * 4  # 0..4 extra

            # Pendenza ADX
            if 'ADX_Slope' in df.columns:
                adx_slope = _num('ADX_Slope')
                adx_score += (adx_slope > 0).astype(int) * 3
            if 'ADX_Slope_Days' in df.columns:
                adx_score += np.minimum(_num('ADX_Slope_Days'), 3) * 1

            # Cross / Trend (stringhe)
            if 'ADX_Cross' in df.columns:
                cs = df['ADX_Cross'].astype(str).str.lower()
                adx_score += (cs == 'bull').astype(int) * 3
                adx_score += (cs == 'bear').astype(int) * -3
            if 'ADX_Trend' in df.columns:
                tr = df['ADX_Trend'].astype(str).str.lower()
                adx_score += (tr == 'up').astype(int) * 2
                adx_score += (tr == 'down').astype(int) * -2

            score += adx_score * weights.get('ADX', 0)

        # === NUOVO: ATR / Volatilità ===
        atr_weight = weights.get('ATR', 0)
        if atr_weight > 0:
            atr_score = 0

            if 'ATR_PCT' in df.columns:
                atrp = pd.to_numeric(df['ATR_PCT'], errors='coerce').fillna(0).clip(lower=0)

                sweet = np.clip((atrp - 1.0) / (4.0 - 1.0), 0, 1) * 8  # 1–4% → fino a +8
                too_high = np.clip((atrp - 6.0) / 2.0, 0, 1) * 6  # >6% → fino a -6
                too_low = np.clip((0.8 - atrp) / 0.8, 0, 1) * 2  # <0.8% → fino a -2

                atr_score += sweet - too_high - too_low

            if 'ATR_Long_OK' in df.columns:
                atr_score += df['ATR_Long_OK'].fillna(False).astype(bool).astype(int) * 3
            if 'ATR_Short_OK' in df.columns:
                atr_score += df['ATR_Short_OK'].fillna(False).astype(bool).astype(int) * -3

            if all(c in df.columns for c in ['Close', 'CE_Long']):
                close = pd.to_numeric(df['Close'], errors='coerce').fillna(0)
                ce_l = pd.to_numeric(df['CE_Long'], errors='coerce').fillna(np.inf)
                atr_score += (close > ce_l).astype(int) * 2

            score += atr_score * atr_weight

        # --- Signal6 (mappa punteggi) ---
        signal6_score = pd.Series(0, index=df.index)
        if 'Signal6' in df.columns:
            m = {
                'Uptrend': 22, 'Uptrend*': 25, 'wakeup2': 20, 'wakeup2*': 18,
                'wakeup1': 15, 'Uptrend-': 12,
                'sleep1': 5, 'sleep2': 5, 'wakeup1-': 3, 'wakeup2-': 3,
                'Uptrend--': 2, 'Uptrend---': 1,
                'Downtrend': -20, 'Downtrend*': -15,
                'Downtrend_revS3Sig+': -8, 'Downtrend_revS3Sig++': -5, 'Downtrend_revS3Sig+++': -2,
            }
            for k, v in m.items():
                signal6_score += (df['Signal6'] == k).astype(int) * v

            if 'Signal6_Trend_Days' in df.columns:
                bonus = np.where((df['Signal6_Trend_Days'] >= 2) & (df['Signal6_Trend_Days'] <= 5), 3, 0)
                bonus += np.where(df['Signal6_Trend_Days'] > 5, 2, 0)
                signal6_score += bonus

        score += signal6_score * weights.get('Signal6', 0)

        # --- normalizza 0..100 ---
        smin, smax = score.min(), score.max()
        if smax != smin:
            score = (score - smin) / (smax - smin) * 100.0
        else:
            score = pd.Series(50.0, index=df.index)

        self.dataframe['TECH_SCORE'] = score.round(2)
        return score







