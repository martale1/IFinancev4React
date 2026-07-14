from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import ANALYSES_DIR

NEED_COLUMNS_START = 1
NEEDED_COLUMNS = [
    "Ticker", "Name", "Close", "PCTV_1D", "PCTV_5D", "TECH_SCORE", "Liquidity",
    "Action", "Market_Phase", "Action_Reason", "Layer3_Warning",
    "MACD", "MACD_Signal", "MACD_Hist", "MACDH_Trend", "MACDH_Trend_Days",
    "RSI", "RSI_Trend", "RSI_Trend_Days",
    "Stoch_K", "Stoch_D", "Williams_R",
    "ADX", "PLUS_DI", "MINUS_DI",
    "ATR", "ATR_PCT",
    "EMA_30", "EMA_50", "Signal6",
    "SAR", "SAR_Above_Price", "PCTV_10D", "PCTV_30D", "PCTV_180D",
    "Vol_Perc_vs_MA20",
    "MACD_vs_Signal",
    "Alligator_Jaw", "Alligator_Teeth", "Alligator_Lips", "Volume",
    "Pullback_Entry_Level", "Pullback_Entry_Zone_Low", "Pullback_Entry_Zone_High",
    "Pullback_Stop_Level", "Pullback_Invalidation", "Pullback_Entry_Note",
    "Trend_Stop_Level", "Trend_Stop_Invalidation", "Trend_Stop_Type",
    "Trading_State", "Layer1_Action", "Layer2_Label", "Layer2_Score",
    "ADX_Trend", "CE_Long", "Profit_Protect_Level", "Signal6_Trend_Days",
]


def build_analysis_filename(market: str) -> str:
    if market == "MIB30":
        return "MIB30_TA_Analyses.xlsx"
    return f"{market}_TA_Analyses.xlsx"


def analysis_path_for_market(market: str) -> Path:
    fp = ANALYSES_DIR / build_analysis_filename(market)
    if not fp.exists():
        raise FileNotFoundError(f"Analysis file not found for market '{market}': {fp}")
    return fp


def analysis_source_info_for_market(market: str) -> dict[str, str]:
    fp = analysis_path_for_market(market)
    st = fp.stat()
    updated = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
    return {"source_file": fp.name, "source_path": str(fp.resolve()), "source_updated_at": updated}


_EXCEL_CACHE: dict[str, tuple[pd.DataFrame, float]] = {}


def load_market_dataframe(market: str) -> pd.DataFrame:
    fp = analysis_path_for_market(market)
    try:
        mtime = fp.stat().st_mtime
    except Exception:
        mtime = 0.0

    if market in _EXCEL_CACHE:
        cached_df, cached_mtime = _EXCEL_CACHE[market]
        if cached_mtime == mtime:
            return cached_df.copy()

    df = pd.read_excel(fp)
    _EXCEL_CACHE[market] = (df, mtime)
    return df.copy()


def _to_num_series(s: pd.Series) -> pd.Series:
    x = s.astype(str).str.strip()
    x = x.str.replace(" ", "", regex=False).str.replace("\u202f", "", regex=False)
    x = x.str.replace(",", ".", regex=False)
    x = x.replace({"nan": None, "None": None, "": None})
    return pd.to_numeric(x, errors="coerce")


def prepare_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    for c in NEEDED_COLUMNS:
        if c not in df.columns:
            df[c] = None

    df["Ticker"] = df["Ticker"].astype(str)
    df["Name"] = df["Name"].astype(str)

    numeric_cols = [
        "Close", "PCTV_1D", "PCTV_5D", "TECH_SCORE",
        "RSI", "ADX", "PLUS_DI", "MINUS_DI", "ATR", "ATR_PCT",
        "MACD", "MACD_Signal", "MACD_Hist",
        "Stoch_K", "Stoch_D", "Volume",
        "MACDH_Trend_Days", "RSI_Trend_Days", "MACD_vs_Signal",
        "Vol_Perc_vs_MA20", "EMA_30", "EMA_50", "SAR", "Layer2_Score",
        "Alligator_Jaw", "Alligator_Teeth", "Alligator_Lips", "Profit_Protect_Level",
        "Pullback_Entry_Level", "Pullback_Entry_Zone_Low", "Pullback_Entry_Zone_High",
        "Pullback_Stop_Level", "Trend_Stop_Level", "CE_Long",
        "PCTV_10D", "PCTV_30D", "PCTV_180D", "Signal6_Trend_Days",
        "Williams_R",
    ]
    for c in numeric_cols:
        df[c] = _to_num_series(df[c])

    df["Action"] = df["Action"].astype(str).str.upper()
    df["Market_Phase"] = df["Market_Phase"].astype(str).str.upper()

    note_u = df["Pullback_Entry_Note"].astype(str).str.upper()
    df["PB_RANK"] = 0
    df.loc[(df["Market_Phase"] == "PULLBACK") & note_u.str.contains("ABOVE_ZONE", na=False), "PB_RANK"] = 1
    df.loc[(df["Market_Phase"] == "PULLBACK") & note_u.str.contains("IN_ZONE", na=False), "PB_RANK"] = 2

    df["SL1_RiskPct"] = (pd.to_numeric(df["Trend_Stop_Level"], errors="coerce") / pd.to_numeric(df["Close"], errors="coerce") - 1.0) * 100.0
    df["SL2_RiskPct"] = (pd.to_numeric(df["CE_Long"], errors="coerce") / pd.to_numeric(df["Close"], errors="coerce") - 1.0) * 100.0

    if df["Action"].isin(["NONE", "NAN", ""]).all() and "Trading_State" in df.columns:
        ts = df["Trading_State"].astype(str).str.upper()
        df.loc[ts == "WAIT", "Action"] = "WAIT"
        df.loc[ts == "HOLD", "Action"] = "HOLD"
        df.loc[ts.isin(["PREPARE", "ENTER"]), "Action"] = "WATCH"

    return df


def apply_search_and_volume_filters(df: pd.DataFrame, search: str = "", min_volume: int = 0, force_ticker: str = "") -> pd.DataFrame:
    out = df.copy()
    s = (search or "").strip().lower()
    if s:
        out = out[
            out["Ticker"].str.lower().str.contains(s, na=False)
            | out["Name"].str.lower().str.contains(s, na=False)
        ]

    if min_volume and min_volume > 0:
        if force_ticker:
            ticker = force_ticker.strip()
            keep = out[out["Ticker"].astype(str).str.strip() == ticker]
            rest = out[out["Volume"].fillna(0) >= float(min_volume)]
            out = pd.concat([rest, keep]).drop_duplicates(subset=["Ticker"], keep="first")
        else:
            out = out[out["Volume"].fillna(0) >= float(min_volume)]
    return out


def apply_state_filters(
    df: pd.DataFrame,
    action: str = "",
    market_phase: str = "",
    trend_phase_detail: str = "",
) -> pd.DataFrame:
    out = df.copy()

    filters = [
        ("Action", action),
        ("Market_Phase", market_phase),
        ("Trend_Phase_Detail", trend_phase_detail),
    ]
    for col, value in filters:
        v = str(value or "").strip().upper()
        if not v or col not in out.columns:
            continue
        out = out[out[col].astype(str).str.strip().str.upper() == v]

    return out


def filter_by_tab(df_in: pd.DataFrame, tab_name: str, n: int, only_neg_in_worst: bool = True) -> pd.DataFrame:
    d = df_in.copy()
    t = (tab_name or "").strip().lower()
    d["Action"] = d["Action"].astype(str).str.upper()
    d["Market_Phase"] = d["Market_Phase"].astype(str).str.upper()
    if "Trend_Phase_Detail" not in d.columns:
        d["Trend_Phase_Detail"] = ""
    d["Trend_Phase_Detail"] = d["Trend_Phase_Detail"].astype(str).str.upper()

    def sort_plain(df_: pd.DataFrame, by_cols: list[str], asc_list: list[bool]) -> pd.DataFrame:
        return df_.sort_values(by=by_cols, ascending=asc_list, na_position="last")

    def sort_pullback(df_: pd.DataFrame, by_cols: list[str], asc_list: list[bool]) -> pd.DataFrame:
        return df_.sort_values(by=["PB_RANK"] + by_cols, ascending=[False] + asc_list, na_position="last")

    if t == "buy":
        return sort_plain(d[d["Action"] == "BUY"].copy(), ["Market_Phase", "TECH_SCORE", "PCTV_1D"], [True, False, False])
    if t == "sell":
        return sort_plain(d[d["Action"] == "SELL"].copy(), ["Market_Phase", "TECH_SCORE", "PCTV_1D"], [True, False, False])
    if t == "pullback":
        return sort_pullback(d[d["Market_Phase"] == "PULLBACK"].copy(), ["TECH_SCORE", "PCTV_1D"], [False, False])
    if t == "breakout":
        return sort_plain(d[d["Market_Phase"] == "BREAKOUT"].copy(), ["TECH_SCORE", "PCTV_1D"], [False, False])
    if t in {"early trend", "early_trend"}:
        return sort_plain(d[d["Trend_Phase_Detail"] == "EARLY_TREND"].copy(), ["TECH_SCORE", "PCTV_1D"], [False, False])
    if t == "expansion":
        return sort_plain(d[d["Trend_Phase_Detail"] == "EXPANSION"].copy(), ["TECH_SCORE", "PCTV_1D"], [False, False])
    if t == "migliori (1d)":
        return sort_plain(d, ["PCTV_1D"], [False]).head(n)
    if t == "peggiori (1d)":
        dd = d[pd.to_numeric(d["PCTV_1D"], errors="coerce") < 0] if only_neg_in_worst else d
        return sort_plain(dd, ["PCTV_1D"], [True]).head(n)
    if t == "migliori (5d)":
        return sort_plain(d, ["PCTV_5D"], [False]).head(n)
    if t == "peggiori (5d)":
        dd = d[pd.to_numeric(d["PCTV_5D"], errors="coerce") < 0] if only_neg_in_worst else d
        return sort_plain(dd, ["PCTV_5D"], [True]).head(n)
    if t in {"azioni (tutte)", "segnali (tutti)", "all"}:
        action_rank = {"BUY": 1, "ADD": 2, "REDUCE": 3, "EXIT": 4, "SELL": 5, "WAIT": 6, "AVOID": 7, "WATCH": 8, "HOLD": 9}
        dd = d.copy()
        dd["ActionRank"] = dd["Action"].map(action_rank).fillna(99).astype(int)
        return dd.sort_values(by=["TECH_SCORE", "ActionRank", "PCTV_1D"], ascending=[False, True, False], na_position="last")

    return sort_plain(d, ["PCTV_1D"], [False])


def paginate(df: pd.DataFrame, page: int, page_size: int) -> tuple[pd.DataFrame, int, int]:
    total_rows = len(df)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    p = min(max(page, 1), total_pages)
    start_idx = (p - 1) * page_size
    end_idx = start_idx + page_size
    return df.iloc[start_idx:end_idx], total_rows, total_pages


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.where(pd.notna(df), None)
    return clean.to_dict(orient="records")
