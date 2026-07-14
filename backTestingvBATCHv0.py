# batch_backtest.py

from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from TechnicalAnalyzer import TechnicalAnalyzer
from ChartManagerBt import AlligatorChartManager  # opzionale per grafici




# -----------------------------
# Trading systems
# -----------------------------
# ===== UNICA LISTA DI SISTEMI =====
def precompute_sig_ma_sar(ta: TechnicalAnalyzer) -> TechnicalAnalyzer:
    ta.generate_signal_SAR_MA(use_ema30=1, use_ema50=0, use_sar=1, column="SIG_MA_SAR")
    return ta

def precompute_alligator(ta: TechnicalAnalyzer) -> TechnicalAnalyzer:
    # già calcolato in calculateTAIndicators; placeholder per estensioni
    return ta

TRADING_SYSTEMS_V1: Dict[str, Dict[str, Any]] = {
    "Trend_MA_SAR_ADX": {
        "long": [
            {"col": "SIG_MA_SAR", "op": ">",  "val": 0},
            {"col": "ADX",        "op": ">=", "val": 25},
            {"col": "Close",      "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "Close", "op": "<", "col2": "EMA_30"},
            {"col": "MACD",  "op": "<", "col2": "MACD_Signal"}
        ],
        "long_logic":  "AND",
        "short_logic": "OR",
        "signal_name": "Trading_Signal",
    },

    "Alligator_Uptrend_ADX": {
        "long": [
            {"col": "Signal6", "op": "==", "val": "Uptrend"},
            {"col": "Close",   "op": ">",  "col2": "Alligator_Teeth"},
            {"col": "ADX",     "op": ">=", "val": 20}
        ],
        "short": [
            {"col": "Close", "op": "<", "col2": "Alligator_Lips"}
        ],
        "long_logic":  "AND",
        "short_logic": "AND",
        "signal_name": "Trading_Signal",
    },

    "Momentum_MACD_RSI_Vol20": {
        "long": [
            {"col": "MACD",            "op": ">",  "col2": "MACD_Signal"},
            {"col": "RSI",             "op": ">",  "val": 55},
            {"col": "Vol_Perc_vs_MA20","op": ">=", "val": 120},
            {"col": "Close",           "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "MACD", "op": "<", "col2": "MACD_Signal"},
            {"col": "RSI",  "op": "<", "val": 45}
        ],
        "long_logic":  "AND",
        "short_logic": "OR",
        "signal_name": "Trading_Signal",
    },

    "Breakout_CE_ATR": {
        "long": [
            {"col": "Close",       "op": ">",  "col2": "CE_Long"},
            {"col": "ATR_Long_OK", "op": "==", "val": True},
            {"col": "Close",       "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "Close",        "op": "<",  "col2": "CE_Short"},
            {"col": "ATR_Short_OK", "op": "==", "val": True}
        ],
        "long_logic":  "AND",
        "short_logic": "AND",
        "signal_name": "Trading_Signal",
    },

    "Breakout_PCTV_Volume": {
        "long": [
            {"col": "PCTV_5D",          "op": ">",  "val": 3},
            {"col": "PCTV_30D",         "op": ">",  "val": 10},
            {"col": "Vol_Perc_vs_MA20", "op": ">=", "val": 110},
            {"col": "Close",            "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "PCTV_5D",  "op": "<", "val": -3},
            {"col": "Close",    "op": "<", "col2": "EMA_30"}
        ],
        "long_logic":  "AND",
        "short_logic": "OR",
        "signal_name": "Trading_Signal",
    },

    "Pullback_Uptrend_StochRSI": {
        "long": [
            {"col": "Close",   "op": ">",  "col2": "EMA_30"},
            {"col": "Stoch_K", "op": ">",  "col2": "Stoch_D"},
            {"col": "Stoch_K", "op": "<",  "val": 80},
            {"col": "RSI",     "op": ">",  "val": 50}
        ],
        "short": [
            {"col": "Close", "op": "<", "col2": "EMA_30"}
        ],
        "long_logic":  "AND",
        "short_logic": "AND",
        "signal_name": "Trading_Signal",
    },

    "VolCompression_Breakout": {
        "long": [
            {"col": "ATR_PCT",         "op": "<",  "val": 1.5},
            {"col": "Vol_Perc_vs_MA20","op": ">=", "val": 130},
            {"col": "Close",           "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "Close", "op": "<", "col2": "EMA_30"}
        ],
        "long_logic":  "AND",
        "short_logic": "AND",
        "signal_name": "Trading_Signal",
    },

    "Reversal_WILLR_MCS": {
        "long": [
            {"col": "WILLR_Oversold","op": "==", "val": True},
            {"col": "MCS_Smoothed",  "op": ">",  "val": 0},
            {"col": "RSI",           "op": ">",  "val": 45}
        ],
        "short": [
            {"col": "WILLR_Overbought","op": "==", "val": True},
            {"col": "MCS_Smoothed",    "op": "<",  "val": 0}
        ],
        "long_logic":  "AND",
        "short_logic": "AND",
        "signal_name": "Trading_Signal",
    },

    "ADX_Building_MACD": {
        "long": [
            {"col": "ADX",       "op": ">=", "val": 18},
            {"col": "ADX_Slope", "op": ">",  "val": 0},
            {"col": "MACD",      "op": ">",  "col2": "MACD_Signal"},
            {"col": "Close",     "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "ADX_Slope", "op": "<",  "val": 0},
            {"col": "Close",     "op": "<",  "col2": "EMA_30"}
        ],
        "long_logic":  "AND",
        "short_logic": "OR",
        "signal_name": "Trading_Signal",
    },

    "SAR_Trailing_MA": {
        "long": [
            {"col": "Close",          "op": ">",  "col2": "EMA_30"},
            {"col": "SAR_Above_Price","op": "==", "val": False}
        ],
        "short": [
            #{"col": "SAR_Above_Price","op": "==", "val": True},
            {"col": "Close",          "op": "<",  "col2": "Alligator_Lips"}
        ],
        "long_logic":  "AND",
        "short_logic": "OR",
        "signal_name": "Trading_Signal",
    },
}

TRADING_SYSTEMS_V2: Dict[str, Dict[str, Any]] = {

    # 1) Trend robusto con MA+SAR e ADX (trend following pulito)
    "Trend_MA_SAR_ADX": {
        "precompute": precompute_sig_ma_sar,   # crea SIG_MA_SAR, usa EMA_30/50 e SAR
        "long": [
            {"col": "SIG_MA_SAR", "op": ">",  "val": 0},
            {"col": "ADX",        "op": ">=", "val": 25},
            {"col": "Close",      "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "Close", "op": "<", "col2": "EMA_30"},
            {"col": "MACD",  "op": "<", "col2": "MACD_Signal"}
        ],
        "long_logic":  "AND",
        "short_logic": "OR",
        "signal_name": "Trading_Signal",
    },

    # 2) Alligator in uptrend + breakout sui Teeth + ADX (trend confermato)
    "Alligator_Uptrend_ADX": {
        "precompute": precompute_alligator,
        "long": [
            {"col": "Signal6", "op": "==", "val": "Uptrend"},
            {"col": "Close",   "op": ">",  "col2": "Alligator_Teeth"},
            {"col": "ADX",     "op": ">=", "val": 20}
        ],
        "short": [
            {"col": "Close", "op": "<", "col2": "Alligator_Lips"}
        ],
        "long_logic":  "AND",
        "short_logic": "AND",
        "signal_name": "Trading_Signal",
    },

    # 3) Momentum classico: MACD + RSI + volume relativo
    "Momentum_MACD_RSI_Vol20": {
        "precompute": precompute_alligator,
        "long": [
            {"col": "MACD",            "op": ">",  "col2": "MACD_Signal"},
            {"col": "RSI",             "op": ">",  "val": 55},
            {"col": "Vol_Perc_vs_MA20","op": ">=", "val": 120},
            {"col": "Close",           "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "MACD", "op": "<", "col2": "MACD_Signal"},
            {"col": "RSI",  "op": "<", "val": 45}
        ],
        "long_logic":  "AND",
        "short_logic": "OR",
        "signal_name": "Trading_Signal",
    },

    # 4) Breakout su Chandelier + filtro ATR (usa flag già calcolati)
    "Breakout_CE_ATR": {
        "precompute": precompute_alligator,  # ATR, CE_Long/CE_Short, ATR_Long_OK/ATR_Short_OK
        "long": [
            {"col": "Close",       "op": ">",  "col2": "CE_Long"},
            {"col": "ATR_Long_OK", "op": "==", "val": True},
            {"col": "Close",       "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "Close",        "op": "<",  "col2": "CE_Short"},
            {"col": "ATR_Short_OK", "op": "==", "val": True}
        ],
        "long_logic":  "AND",
        "short_logic": "AND",
        "signal_name": "Trading_Signal",
    },

    # 5) Breakout multi-periodo + conferma volume
    "Breakout_PCTV_Volume": {
        "precompute": precompute_alligator,
        "long": [
            {"col": "PCTV_5D",          "op": ">",  "val": 3},
            {"col": "PCTV_30D",         "op": ">",  "val": 10},
            {"col": "Vol_Perc_vs_MA20", "op": ">=", "val": 110},
            {"col": "Close",            "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "PCTV_5D",  "op": "<", "val": -3},
            {"col": "Close",    "op": "<", "col2": "EMA_30"}
        ],
        "long_logic":  "AND",
        "short_logic": "OR",
        "signal_name": "Trading_Signal",
    },

    # 6) Pullback in uptrend (rientro con stocastico + RSI)
    "Pullback_Uptrend_StochRSI": {
        "precompute": precompute_alligator,
        "long": [
            {"col": "Close",   "op": ">",  "col2": "EMA_30"},
            {"col": "Stoch_K", "op": ">",  "col2": "Stoch_D"},
            {"col": "Stoch_K", "op": "<",  "val": 80},
            {"col": "RSI",     "op": ">",  "val": 50}
        ],
        "short": [
            {"col": "Close", "op": "<", "col2": "EMA_30"}
        ],
        "long_logic":  "AND",
        "short_logic": "AND",
        "signal_name": "Trading_Signal",
    },

    # 7) Compressione di volatilità + breakout (ATR% basso + volume)
    "VolCompression_Breakout": {
        "precompute": precompute_alligator,
        "long": [
            {"col": "ATR_PCT",         "op": "<",  "val": 1.5},
            {"col": "Vol_Perc_vs_MA20","op": ">=", "val": 130},
            {"col": "Close",           "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "Close", "op": "<", "col2": "EMA_30"}
        ],
        "long_logic":  "AND",
        "short_logic": "AND",
        "signal_name": "Trading_Signal",
    },

    # 8) Reversal da ipervenduto (WILLR + MCS + RSI)
    "WILLR": {
        "precompute": precompute_alligator,
        "long": [
            {"col": "Williams_R", "op": "<=", "val": -80},
            {"col": "WILLR_Trend", "op": "==", "val": "Up"},
        ],
        "short": [
            {"col": "Williams_R", "op": ">=", "val": -20},
            {"col": "WILLR_Trend", "op": "==", "val": "Down"}
        ],
        "long_logic":  "AND",
        "short_logic": "AND",
        "signal_name": "Trading_Signal",
    },

    # 9) ADX in costruzione + MACD (trend che prende forza)
    "ADX_Building_MACD": {
        "precompute": precompute_alligator,
        "long": [
            {"col": "ADX",       "op": ">=", "val": 18},
            {"col": "ADX_Slope", "op": ">",  "val": 0},           # ADX in crescita
            {"col": "MACD",      "op": ">",  "col2": "MACD_Signal"},
            {"col": "Close",     "op": ">",  "col2": "EMA_30"}
        ],
        "short": [
            {"col": "ADX_Slope", "op": "<",  "val": 0},
            {"col": "Close",     "op": "<",  "col2": "EMA_30"}
        ],
        "long_logic":  "AND",
        "short_logic": "OR",
        "signal_name": "Trading_Signal",
    },

    # 10) SAR trail + bias MA (ingressi più frequenti, uscite rapide)
    "SAR_Trailing_MA": {
        "precompute": precompute_sig_ma_sar,
        "long": [
            {"col": "Close",          "op": ">",  "col2": "EMA_30"},
            {"col": "SAR_Above_Price","op": "==", "val": False}
        ],
        "short": [
            {"col": "SAR_Above_Price","op": "==", "val": True},
            {"col": "Close",          "op": "<",  "col2": "Alligator_Lips"}
        ],
        "long_logic":  "AND",
        "short_logic": "OR",
        "signal_name": "Trading_Signal",
    },

"STOCH_Reversal": {
    "precompute": precompute_alligator,   # non serve altro precompute
    "long": [
        {"col": "Stoch_K",  "op": "<=", "val": 30},          # in ipervenduto
        {"col": "SK_Trend", "op": "==", "val": "Up"},        # trend stocastico in ripartenza
        {"col": "Stoch_K",  "op": ">",  "col2": "Stoch_D"},  # K sopra D (momentum up)
        {"col": "SK_Trend_Days", "op": ">=", "val": 1}       # conferma da almeno 1 giorno
    ],
    "short": [
        {"col": "Stoch_K",  "op": ">=", "val": 80},          # in ipercomprato
        {"col": "SK_Trend", "op": "==", "val": "Down"},      # trend stocastico in discesa
        {"col": "Stoch_K",  "op": "<",  "col2": "Stoch_D"},  # K sotto D (momentum down)
        {"col": "SK_Trend_Days", "op": ">=", "val": 1}       # conferma da almeno 1 giorno
    ],
    "long_logic":  "AND",
    "short_logic": "AND",
    "signal_name": "Trading_Signal",
}

}



def precompute_sig_ma_sar(ta: TechnicalAnalyzer) -> TechnicalAnalyzer:
    ta.generate_signal_SAR_MA(use_ema30=1, use_ema50=0, use_sar=1, column="SIG_MA_SAR")
    return ta

def precompute_alligator(ta: TechnicalAnalyzer) -> TechnicalAnalyzer:
    # già calcolato in calculateTAIndicators; placeholder per estensioni
    return ta

# -----------------------------
# Pipeline indicatori / scoring
# -----------------------------
def calculateTAIndicators(ta: TechnicalAnalyzer) -> TechnicalAnalyzer:
    ta.calculate_TA_Indicators("ADX,ATR,MACD,VOL_PERC,RSI,SAR,STOCH,WILLR,ALLIGATOR,EMA_50,EMA_30,PCTV")
    ta.calculate_alligator_signal6()
    return ta

def calculateScoring(ta: TechnicalAnalyzer) -> TechnicalAnalyzer:
    custom_weights = {
        'MACD': 0.18, 'RSI': 0.12, 'STOCH': 0.10, 'MA_TREND': 0.12,
        'VOLUME': 0.08, 'SAR': 0.06, 'PCTV': 0.06, 'ALLIGATOR': 0.08,
        'Signal6': 0.12, 'ADX': 0.12, 'ATR': 0.06,
    }
    ta.calculate_technical_score(weights=custom_weights)
    return ta

def _resolve_logics(cfg: Dict[str, Any]) -> (str, str, bool):
    # gerarchia: FORCE_*  ->  cfg["*_logic"]  ->  default AND
    long_logic  = (FORCE_LONG_LOGIC  or cfg.get("long_logic")  or "AND").upper()
    short_logic = (FORCE_SHORT_LOGIC or cfg.get("short_logic") or "AND").upper()
    prefer_short = cfg.get("prefer_short_on_conflict", DEFAULT_PREFER_SHORT_ON_CONFLICT)
    if long_logic not in ("AND", "OR") or short_logic not in ("AND", "OR"):
        raise ValueError("Logic deve essere 'AND' oppure 'OR'")
    return long_logic, short_logic, bool(prefer_short)

def run_backtest_for(
    ticker: str,
    period: str,
    system_name: str,
    system_cfg: Dict[str, Any],
    freq: str = "1D",
    plot_chart: bool = False
) -> Optional[pd.Series]:
    try:
        ta = TechnicalAnalyzer(ticker, period=period)
        ta = calculateTAIndicators(ta)
        ta = calculateScoring(ta)

        precompute_fn = system_cfg.get("precompute")
        if callable(precompute_fn):
            ta = precompute_fn(ta)

        json_long   = system_cfg.get("long", [])
        json_short  = system_cfg.get("short", [])
        signal_name = system_cfg.get("signal_name", "Trading_Signal")

        # NEW: risolvi logiche
        long_logic, short_logic, prefer_short = _resolve_logics(system_cfg)

        # Usa backTestingVBT per GENERARE segnali (AND/OR) e backtestare (v1 semantics)
        stats = ta.backTestingVBTLogic(
            plotChart=False,
            freq=freq,
            json_long=json_long,
            json_short=json_short,
            long_logic=long_logic,
            short_logic=short_logic,
            signal_name=signal_name,
            prefer_short_on_conflict=prefer_short,
        )

        if plot_chart:
            try:
                cm = AlligatorChartManager(technical_analyzer=ta)
                cm.plot_simple_alligator(
                    days=200, chart_type='candlestick',
                    show_entries_exits=True, show_sar=True,
                    show_moving_averages=True, show_signals=False
                )
                plt.show()
            except Exception as e:
                print(f"[{ticker} | {system_name}] Grafico non generato: {e}")

        stats = stats.copy()
        stats["__ticker__"] = ticker
        stats["__system__"] = system_name
        stats["__period__"] = period

        def _last_int(series) -> Optional[int]:
            s = pd.to_numeric(series, errors="coerce").dropna()
            return int(s.iloc[-1]) if len(s) else np.nan

        sig_last = _last_int(ta.dataframe.get(signal_name, pd.Series(dtype="float64")))
        long_last = _last_int(ta.dataframe.get("Long_Days", pd.Series(dtype="float64")))
        short_last = _last_int(ta.dataframe.get("Short_Days", pd.Series(dtype="float64")))

        stats = stats.copy()
        stats["__ticker__"] = ticker
        stats["__system__"] = system_name
        stats["__period__"] = period

        # >>> aggiunte per la tabella di riepilogo <<<
        stats["Trading_Signal"] = sig_last
        stats["Long_Days"] = long_last
        stats["Short_Days"] = short_last
        return stats

    except Exception as e:
        print(f"[ERRORE] {ticker} | {system_name}: {e}")
        return None

# -----------------------------
# Utilità: pulizia ed export
# -----------------------------
def clean_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    """Rende il DataFrame sicuro per l'export in Excel."""
    out = df.copy()

    # 1) sostituisci inf con NaN
    out.replace([np.inf, -np.inf], np.nan, inplace=True)

    # 2) rimuovi timezone da tutte le datetime
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            try:
                # se tz-aware → togli tz
                if getattr(out[col].dt, 'tz', None) is not None:
                    out[col] = out[col].dt.tz_localize(None)
            except Exception:
                out[col] = pd.to_datetime(out[col], errors='coerce')
                if getattr(out[col].dt, 'tz', None) is not None:
                    out[col] = out[col].dt.tz_localize(None)

    return out

# -----------------------------
# Batch runner
# -----------------------------
def main():
    results: List[pd.Series] = []

    for tk in TICKERS:
        for sys_name, sys_cfg in TRADING_SYSTEMS.items():
            s = run_backtest_for(tk, PERIOD, sys_name, sys_cfg, freq=FREQ, plot_chart=False)
            if s is not None:
                results.append(s)

    if not results:
        print("Nessun risultato prodotto.")
        return

    # Concatena in DataFrame
    df = pd.DataFrame(results)

    # Normalizza alcuni nomi (se esistono varianti nelle stats)
    if "Total Return [%]" not in df.columns:
        for alt in ["Total Return [€]", "Total Return"]:
            if alt in df.columns:
                df.rename(columns={alt: "Total Return [%]"}, inplace=True)
                break

    if "Annualized Return [%]" not in df.columns:
        for alt in ["Annual Return [%]", "CAGR [%]"]:
            if alt in df.columns:
                df.rename(columns={alt: "Annualized Return [%]"}, inplace=True)
                break

    if "Max Drawdown [%]" not in df.columns and "Max Drawdown" in df.columns:
        df.rename(columns={"Max Drawdown": "Max Drawdown [%]"}, inplace=True)

    # Ordina per Sharpe e poi Total Return (se presenti)
    by_cols, ascending = [], []
    if "Sharpe Ratio" in df.columns:
        by_cols.append("Sharpe Ratio"); ascending.append(False)
    if "Total Return [%]" in df.columns:
        by_cols.append("Total Return [%]"); ascending.append(False)
    if by_cols:
        df = df.sort_values(by=by_cols, ascending=ascending)

    # Stampa una vista sintetica
    cols_preferite = [
        "__ticker__", "__system__", "__period__",
        "Total Return [%]", "Long_Days","Short_Days","Trading_Signal","Annualized Return [%]",
        "Max Drawdown [%]", "Sharpe Ratio", "Sortino Ratio",
        "Calmar Ratio", "Omega Ratio", "Win Rate [%]", "Trades"
    ]
    to_show = [c for c in cols_preferite if c in df.columns]
    print("\n=== TOP RISULTATI ===")
    print(df[to_show].head(20).to_string(index=False))

    # Export Excel (senza Category)
    #df_export = clean_for_excel(df)
    #df_export.to_excel(OUTPUT_XLSX, index=False)
    #print(f"\nSalvato: {OUTPUT_XLSX}")

if __name__ == "__main__":
    # File di output
    OUTPUT_XLSX = "batch_backtest_results.xlsx"
    # --- Override globali (opzionali). Metti a None per non forzare ---
    FORCE_LONG_LOGIC = None  # "AND" | "OR" | None
    FORCE_SHORT_LOGIC = None  # "AND" | "OR" | None
    # In caso di conflitto (long & short veri sulla stessa barra) chi vince?
    DEFAULT_PREFER_SHORT_ON_CONFLICT = True
    TICKERS: List[str] = [
        #"GDXJ.MI",
        #"3LCO.MI",
        "VOD.L",
        #"3SIL.MI",

    ]
    PERIOD = "2y"  # "6mo", "2y", "max"
    FREQ =   "1D"  # frequenza logica dei dati per i ratio
    TRADING_SYSTEMS=TRADING_SYSTEMS_V2
    main()
