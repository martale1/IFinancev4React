# batch_backtest.py

from typing import Dict, List, Optional, Any, Tuple
import sys, os, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Assicura il path di progetto
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT)

from TechnicalAnalyzer import TechnicalAnalyzer
from ChartManagerBt import AlligatorChartManager  # opzionale per grafici

# --- NEW: valutatore di condizioni e blocchi -------------------------------
from operator import eq, ne, gt, ge, lt, le

_OPS = { "==": eq, "!=": ne, ">": gt, ">=": ge, "<": lt, "<=": le }

def _eval_single_condition(df: pd.DataFrame, cond: Dict[str, Any]) -> pd.Series:
    """
    Supporta:
      {"col":"A","op":">", "val": 10}
      {"col":"A","op":">", "col2":"B"}
    Restituisce una Series booleana (index = df.index).
    """
    col = cond.get("col")
    op  = cond.get("op")
    if op not in _OPS:
        raise ValueError(f"Operatore non supportato: {op}")

    lhs = pd.to_numeric(df[col], errors="ignore") if col in df.columns else pd.Series(False, index=df.index)

    if "col2" in cond:
        rhs_col = cond["col2"]
        rhs = pd.to_numeric(df[rhs_col], errors="ignore") if rhs_col in df.columns else np.nan
    else:
        rhs = cond.get("val", np.nan)

    # Confronti robusti (gestione string/numeric mixed)
    try:
        out = _OPS[op](lhs, rhs)
    except Exception:
        # prova convertendo a numeric, fallback a stringhe
        lhs_num = pd.to_numeric(lhs, errors="coerce")
        rhs_num = pd.to_numeric(rhs, errors="coerce")
        with np.errstate(all='ignore'):
            out = _OPS[op](lhs_num, rhs_num)
        # dove non numerico, riprova come stringa solo per ==/!=
        if op in ("==", "!="):
            mask_na = out.isna()
            if mask_na.any():
                out_str = _OPS[op](lhs.astype(str), str(rhs))
                out = out.where(~mask_na, out_str)

    return out.fillna(False).astype(bool)

def _make_block_series(
    df: pd.DataFrame,
    blocks: List[List[Dict[str, Any]]],
    prefix: str,
) -> Tuple[List[str], pd.DataFrame]:
    """
    Valuta ciascun blocco (AND tra condizioni del blocco) e crea colonne booleane:
        f"{prefix}_B1", f"{prefix}_B2", ...
    Ritorna i nomi colonna create e il df aggiornato.
    """
    created_cols = []
    for i, block in enumerate(blocks, 1):
        if not block:
            continue
        s = pd.Series(True, index=df.index, dtype=bool)
        for cond in block:
            s = s & _eval_single_condition(df, cond)
        col_name = f"{prefix}_B{i}"
        df[col_name] = s.astype(bool)
        created_cols.append(col_name)
    return created_cols, df

# ------------ precompute helpers (richiamati via stringa dal JSON) ------------
def precompute_sig_ma_sar(ta: TechnicalAnalyzer) -> TechnicalAnalyzer:
    ta.generate_signal_SAR_MA(use_ema30=1, use_ema50=0, use_sar=1, column="SIG_MA_SAR")
    return ta

def precompute_alligator(ta: TechnicalAnalyzer) -> TechnicalAnalyzer:
    # Alligator e segnali già calcolati in calculateTAIndicators
    return ta

PRECOMPUTE_FUNCS = {
    "sig_ma_sar": precompute_sig_ma_sar,
    "alligator": precompute_alligator,
    None: None,
    "": None
}

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

# -----------------------------
# Pulizia export (opzionale)
# -----------------------------
def clean_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.replace([np.inf, -np.inf], np.nan, inplace=True)
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            try:
                if getattr(out[col].dt, 'tz', None) is not None:
                    out[col] = out[col].dt.tz_localize(None)
            except Exception:
                out[col] = pd.to_datetime(out[col], errors='coerce')
                if getattr(out[col].dt, 'tz', None) is not None:
                    out[col] = out[col].dt.tz_localize(None)
    return out

# -----------------------------
# Lettura JSON sistemi
# -----------------------------
def load_trading_systems(json_path: str) -> Dict[str, Dict[str, Any]]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Il JSON dei sistemi deve contenere un oggetto {nome_sistema: config, ...}.")
    return data

def _resolve_logics(cfg: Dict[str, Any],
                    FORCE_LONG_LOGIC: Optional[str],
                    FORCE_SHORT_LOGIC: Optional[str],
                    DEFAULT_PREFER_SHORT_ON_CONFLICT: bool) -> Tuple[str, str, bool]:
    long_logic  = (FORCE_LONG_LOGIC  or cfg.get("long_logic")  or "AND").upper()
    short_logic = (FORCE_SHORT_LOGIC or cfg.get("short_logic") or "AND").upper()
    prefer_short = cfg.get("prefer_short_on_conflict", DEFAULT_PREFER_SHORT_ON_CONFLICT)
    if long_logic not in ("AND", "OR") or short_logic not in ("AND", "OR"):
        raise ValueError("Logic deve essere 'AND' oppure 'OR'")
    return long_logic, short_logic, bool(prefer_short)

# -----------------------------
# Esecuzione di un sistema
# -----------------------------
def run_backtest_for(
    ticker: str,
    period: str,
    system_name: str,
    system_cfg: Dict[str, Any],
    freq: str = "1D",
    plot_chart: bool = False,plotSignals:bool=False,
    FORCE_LONG_LOGIC: Optional[str] = None,
    FORCE_SHORT_LOGIC: Optional[str] = None,
    DEFAULT_PREFER_SHORT_ON_CONFLICT: bool = True
) -> Optional[pd.Series]:
    try:
        print(system_name)
        ta = TechnicalAnalyzer(ticker, period=period)
        ta = calculateTAIndicators(ta)
        #ta.add_dynamic_exit_levels() #aggiunge colonna stop level
        ta.add_prev_true_range() #aggiunge colonna stop level
        ta = calculateScoring(ta)

        # precompute indicato nel JSON
        pre_key = system_cfg.get("precompute")
        pre_fn = PRECOMPUTE_FUNCS.get(pre_key)
        if callable(pre_fn):
            ta = pre_fn(ta)

        # --- NEW: blocchi da JSON (retro-compatibile) ----------------------
        blocks_long = system_cfg.get("long_blocks")
        blocks_short = system_cfg.get("short_blocks")
        blocks_long_logic = (system_cfg.get("long_blocks_logic") or system_cfg.get("long_logic") or "AND").upper()
        blocks_short_logic = (system_cfg.get("short_blocks_logic") or system_cfg.get("short_logic") or "AND").upper()

        # Se ci sono i blocchi, sintetizziamo in colonne booleane per blocco
        if blocks_long:
            long_cols, ta.dataframe = _make_block_series(ta.dataframe, blocks_long, prefix=f"{system_name}_LONG")
            json_long = [{"col": c, "op": "==", "val": True} for c in long_cols]
            long_logic = blocks_long_logic
        else:
            json_long = system_cfg.get("long", [])
            long_logic = (system_cfg.get("long_logic") or "AND").upper()

        if blocks_short:
            short_cols, ta.dataframe = _make_block_series(ta.dataframe, blocks_short, prefix=f"{system_name}_SHORT")
            json_short = [{"col": c, "op": "==", "val": True} for c in short_cols]
            short_logic = blocks_short_logic
        else:
            json_short = system_cfg.get("short", [])
            short_logic = (system_cfg.get("short_logic") or "AND").upper()

        # preferenza short-on-conflict
        _, _, prefer_short = _resolve_logics(
            {"long_logic": long_logic, "short_logic": short_logic,
             "prefer_short_on_conflict": system_cfg.get("prefer_short_on_conflict", DEFAULT_PREFER_SHORT_ON_CONFLICT)},
            FORCE_LONG_LOGIC, FORCE_SHORT_LOGIC, DEFAULT_PREFER_SHORT_ON_CONFLICT
        )

        signal_name = system_cfg.get("signal_name", "Trading_Signal")

        stats = ta.backTestingVBTLogic(
            plotChart=plot_chart,
            freq=freq,
            json_long=json_long,
            json_short=json_short,
            long_logic=long_logic,
            short_logic=short_logic,
            signal_name=signal_name,
            prefer_short_on_conflict=prefer_short,
        )
        if plotSignals:
            cols = ["Trading_Signal","TECH_SCORE", "Entry_Signal", "Exit_Signal", "Long_Days", "Short_Days","Stop_Level", "Close", "MCS", "SIG_MA_SAR", "MACD", "MACD_Signal"]
            print(ta.dataframe[cols].tail(50).to_string())

        if plot_chart:
            try:
                cm = AlligatorChartManager(technical_analyzer=ta)
                cm.plot_simple_alligator(
                    days=200, chart_type='candlestick',
                    show_entries_exits=True, show_sar=True,
                    show_moving_averages=True, show_signals=False
                )

                # 📌 1) Prende l'axes CORRETTO del grafico alligatore
                ax = plt.gca()

                # 📌 2) Estrae i valori che ti servono
                ts_name = system_name

                total_return = None
                for col in ["Total Return [%]", "Total Return", "Total Return [€]"]:
                    if col in stats.index:
                        total_return = stats[col]
                        break
                print(total_return)
                text_lines = [f"TS: {ts_name}"]
                if total_return is not None:
                    text_lines.append(f"Rend: {total_return:.2f}%")

                if "Sharpe Ratio" in stats.index:
                    text_lines.append(f"Sharpe: {stats['Sharpe Ratio']:.2f}")

                # 📌 3) Unisce il testo da stampare
                info_text = "\n".join(text_lines)

                # 📌 4) Stampa il testo *sul grafico visibile*
                ax.text(
                    0.99, 0.99,  # <--- prima era (0.01, 0.99)
                    info_text,
                    transform=ax.transAxes,
                    ha="right",  # allinea il testo al bordo destro
                    va="top",
                    fontsize=12,
                    bbox=dict(
                        facecolor="white",
                        alpha=0.9,
                        edgecolor="black"
                    ),
                    zorder=10  # sta sopra le altre cose
                )

                plt.show()

            except Exception as e:
                print(f"[{ticker} | {system_name}] Grafico non generato: {e}")

        # Helper per estrarre ultimo valore intero (senza decimali)
        def _last_int(series) -> Optional[int]:
            s = pd.to_numeric(series, errors="coerce").dropna()
            return int(s.iloc[-1]) if len(s) else np.nan

        sig_last   = _last_int(ta.dataframe.get(signal_name, pd.Series(dtype="float64")))
        long_last  = _last_int(ta.dataframe.get("Long_Days", pd.Series(dtype="float64")))
        short_last = _last_int(ta.dataframe.get("Short_Days", pd.Series(dtype="float64")))

        stats = stats.copy()
        stats["__ticker__"] = ticker
        stats["__system__"] = system_name
        stats["__period__"] = period
        stats["Trading_Signal"] = sig_last
        stats["Long_Days"] = long_last
        stats["Short_Days"] = short_last
        return stats

    except Exception as e:
        print(f"[ERRORE] {ticker} | {system_name}: {e}")
        return None

# -----------------------------
# Batch runner
# -----------------------------
def main(tsFile,plotChart=False,plotSignals=False):
    # Path JSON sistemi
    systems_json_path = os.path.join(ROOT, "tradingSystems", tsFile)
    TRADING_SYSTEMS: Dict[str, Dict[str, Any]] = load_trading_systems(systems_json_path)

    results: List[pd.Series] = []
    for tk in TICKERS:
        for sys_name, sys_cfg in TRADING_SYSTEMS.items():
            s = run_backtest_for(
                tk, PERIOD, sys_name, sys_cfg, freq=FREQ, plot_chart=plotChart, plotSignals=plotSignals,
                FORCE_LONG_LOGIC=FORCE_LONG_LOGIC,
                FORCE_SHORT_LOGIC=FORCE_SHORT_LOGIC,
                DEFAULT_PREFER_SHORT_ON_CONFLICT=DEFAULT_PREFER_SHORT_ON_CONFLICT
            )
            if s is not None:
                results.append(s)

    if not results:
        print("Nessun risultato prodotto.")
        return

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

    # Vista sintetica
    cols_preferite = [
        "__ticker__", "__system__", "__period__",
        "Total Return [%]", "Long_Days", "Short_Days", "Trading_Signal",
        "Annualized Return [%]", "Max Drawdown [%]", "Sharpe Ratio", "Sortino Ratio",
        "Calmar Ratio", "Omega Ratio", "Win Rate [%]", "Trades"
    ]
    to_show = [c for c in cols_preferite if c in df.columns]
    # --- Ordinamento e stampa finale (multi-chiave) ---
    primary_key = "__ticker__"  # primo livello: ticker (A→Z)
    secondary_key = "Total Return [%]"  # secondo livello: per ticker, ordina per performance (alto→basso)

    keys = [primary_key, secondary_key]
    ascending_flags = [True, False]  # True per ticker crescente, False per return decrescente

    missing = [k for k in keys if k not in df.columns]
    if missing:
        print(f"[AVVISO] Colonne mancanti per l'ordinamento: {missing}. Uso ordinamento semplice per {primary_key}.")
        df_sorted = df.sort_values(by=primary_key, ascending=True)
    else:
        df_sorted = df.sort_values(by=keys, ascending=ascending_flags, na_position="last")

    to_show = [c for c in [
        "__ticker__", "__system__", "__period__",
        "Total Return [%]", "Long_Days", "Short_Days", "Trading_Signal",
        "Annualized Return [%]", "Max Drawdown [%]", "Sharpe Ratio", "Sortino Ratio",
        "Calmar Ratio", "Omega Ratio", "Win Rate [%]", "Trades"
    ] if c in df_sorted.columns]

    print(f"\n=== RISULTATI ORDINATI PER {primary_key} (crescente) e {secondary_key} (decrescente) ===")
    print(df_sorted[to_show].to_string(index=False))

    # (Opzionale) Raggruppa per sistema
    # for system, g in df_sorted.groupby("__system__"):
    #     print(f"\n--- {system} ---")
    #     print(g[to_show].to_string(index=False))



    #print(df[to_show].to_string(index=False))
    # Export opzionale
    # df_export = clean_for_excel(df)
    # df_export.to_excel(OUTPUT_XLSX, index=False)
    # print(f"\nSalvato: {OUTPUT_XLSX}")

if __name__ == "__main__":
    OUTPUT_XLSX = "batch_backtest_results.xlsx"

    # Override globali (metti a None per non forzare)
    FORCE_LONG_LOGIC: Optional[str] = None   # "AND" | "OR" | None
    FORCE_SHORT_LOGIC: Optional[str] = None  # "AND" | "OR" | None
    DEFAULT_PREFER_SHORT_ON_CONFLICT = True

    # Parametri batch
    TICKERS: List[str] = [
        #"VOD.L",

       # "STMMI.mi",
       # "STLAM.MI",
       # "3SIL.MI",
       # "3NVD.mi",
        "LCOC.MI",
    ]
    PERIOD = "2y"   # "6mo", "2y", "max"
    FREQ   = "1D"   # frequenza logica dei dati per i ratio

    main(tsFile="final.json",plotChart=False,plotSignals=False)
