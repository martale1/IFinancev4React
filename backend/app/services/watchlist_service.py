from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import ANALYSES_DIR

NEED_COLUMNS_START = 1
NEEDED_COLUMNS = [
    "Ticker", "Name", "Close", "PCTV_1D", "PCTV_5D", "TECH_SCORE",
    "TECH_STRUCTURE", "TECH_MOMENTUM", "TECH_PARTICIPATION", "TECH_EXTENSION_PENALTY", "Liquidity",
    "Action", "Market_Phase", "Trend_Phase_Detail", "Action_Reason", "Layer3_Warning",
    "MACD", "MACD_Signal", "MACD_Hist", "MACDH_Trend", "MACDH_Trend_Days",
    "RSI", "RSI_Trend", "RSI_Trend_Days",
    "Stoch_K", "Stoch_D", "Williams_R",
    "ADX", "PLUS_DI", "MINUS_DI",
    "ATR", "ATR_PCT",
    "EMA_30", "EMA_50", "Signal6",
    "SAR", "SAR_Above_Price", "PCTV_10D", "PCTV_30D", "PCTV_180D",
    "Vol_Perc_vs_MA5", "Vol_Perc_vs_MA10", "Vol_Perc_vs_MA20", "ADX_Change",
    "MACD_vs_Signal",
    "Alligator_Jaw", "Alligator_Teeth", "Alligator_Lips", "Volume",
    "Pullback_Entry_Level", "Pullback_Entry_Zone_Low", "Pullback_Entry_Zone_High",
    "Pullback_Stop_Level", "Pullback_Invalidation", "Pullback_Entry_Note",
    "Trend_Stop_Level", "Trend_Stop_Invalidation", "Trend_Stop_Type",
    "Trading_State", "Layer1_Action", "Layer2_Label", "Layer2_Score",
    "ADX_Trend", "CE_Long", "Profit_Protect_Level", "Signal6_Trend_Days",
    "Pattern_Type", "Pattern_Days_Ago", "Pattern_S2_Days_Ago", "Pattern_S3_Days_Ago",
    "Data_Quality", "History_Rows",
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


def load_market_dataframe(market: str) -> pd.DataFrame:
    fp = analysis_path_for_market(market)
    return pd.read_excel(fp)


def _to_num_series(s: pd.Series) -> pd.Series:
    x = s.astype(str).str.strip()
    x = x.str.replace(" ", "", regex=False).str.replace("\u202f", "", regex=False)
    x = x.str.replace(",", ".", regex=False)
    x = x.replace({"nan": None, "None": None, "": None})
    return pd.to_numeric(x, errors="coerce")


def _num_series(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce") if column in df.columns else pd.Series(float("nan"), index=df.index)


def _fmt(value: float, digits: int = 1) -> str:
    if value is None or pd.isna(value):
        return "n/d"
    return f"{value:.{digits}f}".replace(".", ",")


def _build_entry_diagnosis(
    df: pd.DataFrame,
    action_u: pd.Series,
    phase_u: pd.Series,
    detail_u: pd.Series,
    liquidity_u: pd.Series,
) -> pd.Series:
    """Descrive perché il segnale d'ingresso non è ENTRA, elencando cosa manca.

    Le soglie sono quelle del trigger di acquisto del trading state v4
    (TechnicalAnalyzer.add_trading_statev4_v1) e dell'indicazione d'ingresso in
    questo modulo: ADX >= 20, ADX_Trend Bullish, DI+ > DI-, 0 < MACD_vs_Signal <= 10,
    MACDH_Trend Up, RSI >= 45 con trend Up, prezzo sopra EMA30 ed EMA50,
    SAR sotto il prezzo, TECH_SCORE >= 65.
    """
    adx = _num_series(df, "ADX")
    adx_trend = df["ADX_Trend"].astype(str).str.strip().str.lower() if "ADX_Trend" in df.columns else pd.Series("", index=df.index)
    plus_di = _num_series(df, "PLUS_DI")
    minus_di = _num_series(df, "MINUS_DI")
    macd_vs = _num_series(df, "MACD_vs_Signal")
    macdh = df["MACDH_Trend"].astype(str).str.strip().str.lower() if "MACDH_Trend" in df.columns else pd.Series("", index=df.index)
    rsi = _num_series(df, "RSI")
    rsi_trend = df["RSI_Trend"].astype(str).str.strip().str.lower() if "RSI_Trend" in df.columns else pd.Series("", index=df.index)
    tech = _num_series(df, "TECH_SCORE")
    close = _num_series(df, "Close")
    ema30 = _num_series(df, "EMA_30")
    ema50 = _num_series(df, "EMA_50")
    sar_above = df["SAR_Above_Price"].astype(str).str.strip().str.upper() if "SAR_Above_Price" in df.columns else pd.Series("", index=df.index)

    def rowwise(index: int) -> str:
        if action_u.iloc[index] == "BUY" and liquidity_u.iloc[index] == "OK":
            return ""
        if liquidity_u.iloc[index] == "AVOID":
            return "Liquidità insufficiente: il titolo è escluso dalle indicazioni operative."

        # La fase viene per prima: in laterale NESSUNA condizione tecnica può far
        # scattare il trigger, quindi elencarle suggerirebbe un progresso che non
        # esiste (es. "ADX >= 20 (ora 18,9)" quando l'ADX può salire quanto vuole
        # senza cambiare l'esito). Le fasi RIBASSO non arrivano qui: sono marcate
        # EVITA e la diagnosi viene svuotata, con "Struttura fragile" come motivo.
        fase = phase_u.iloc[index]
        if fase == "LATERALE":
            return (
                "🎯 Serve prima una direzione: ora è laterale. "
                "Servono prezzo sopra la media con pendenza, oppure ADX >= 22."
            )

        missing: list[str] = []
        if not (adx.iloc[index] >= 20):
            missing.append(f"ADX >= 20 (ora {_fmt(adx.iloc[index])})")
        if "bullish" not in adx_trend.iloc[index]:
            missing.append(f"ADX_Trend Bullish (ora {adx_trend.iloc[index] or 'n/d'})")
        if not (plus_di.iloc[index] > minus_di.iloc[index]):
            missing.append(f"DI+ > DI- (ora {_fmt(plus_di.iloc[index])} / {_fmt(minus_di.iloc[index])})")
        if not (macd_vs.iloc[index] > 0):
            missing.append(f"MACD sopra il segnale (ora {_fmt(macd_vs.iloc[index], 0)})")
        elif macd_vs.iloc[index] > 10:
            missing.append(f"incrocio MACD recente, entro 10 sedute (ora {_fmt(macd_vs.iloc[index], 0)})")
        if macdh.iloc[index] != "up":
            missing.append(f"istogramma MACD in salita (ora {macdh.iloc[index] or 'n/d'})")
        if not (rsi.iloc[index] >= 45):
            missing.append(f"RSI >= 45 (ora {_fmt(rsi.iloc[index], 0)})")
        if rsi_trend.iloc[index] != "up":
            missing.append(f"RSI in salita (ora {rsi_trend.iloc[index] or 'n/d'})")
        if not (close.iloc[index] > ema30.iloc[index]):
            missing.append(f"prezzo sopra EMA30 (ora {_fmt(close.iloc[index], 2)} vs {_fmt(ema30.iloc[index], 2)})")
        if not (close.iloc[index] > ema50.iloc[index]):
            missing.append(f"prezzo sopra EMA50 (ora {_fmt(close.iloc[index], 2)} vs {_fmt(ema50.iloc[index], 2)})")
        if sar_above.iloc[index] in {"TRUE", "1", "YES"}:
            missing.append("Parabolic SAR sotto il prezzo")
        if not (tech.iloc[index] >= 65):
            missing.append(f"TECH_SCORE >= 65 (ora {_fmt(tech.iloc[index], 0)})")

        if not missing:
            return "Nessuna condizione mancante: il trigger è soddisfatto."
        return "Manca: " + " · ".join(missing[:5]) + (" · …" if len(missing) > 5 else "")

    values = [rowwise(i) for i in range(len(df))]
    # Chi è già ENTRA non ha nulla da recuperare; chi è EVITA ha una motivazione
    # di rischio che resta più utile della lista delle condizioni.
    result = pd.Series(values, index=df.index)
    result = result.mask(df["Entry_Signal"] == "ENTRA", "")
    result = result.mask(df["Entry_Signal"] == "EVITA", "")
    return result


def prepare_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()
    for c in NEEDED_COLUMNS:
        if c not in df.columns:
            df[c] = None

    df["Ticker"] = df["Ticker"].astype(str)
    df["Name"] = df["Name"].astype(str)

    numeric_cols = [
        "Close", "PCTV_1D", "PCTV_5D", "TECH_SCORE",
        "TECH_STRUCTURE", "TECH_MOMENTUM", "TECH_PARTICIPATION", "TECH_EXTENSION_PENALTY",
        "RSI", "ADX", "PLUS_DI", "MINUS_DI", "ATR", "ATR_PCT",
        "MACD", "MACD_Signal", "MACD_Hist",
        "Stoch_K", "Stoch_D", "Volume",
        "MACDH_Trend_Days", "RSI_Trend_Days", "MACD_vs_Signal",
        "Vol_Perc_vs_MA5", "Vol_Perc_vs_MA10", "Vol_Perc_vs_MA20", "ADX_Change",
        "EMA_30", "EMA_50", "SAR", "Layer2_Score",
        "Alligator_Jaw", "Alligator_Teeth", "Alligator_Lips", "Profit_Protect_Level",
        "Pullback_Entry_Level", "Pullback_Entry_Zone_Low", "Pullback_Entry_Zone_High",
        "Pullback_Stop_Level", "Trend_Stop_Level", "CE_Long",
        "PCTV_10D", "PCTV_30D", "PCTV_180D", "Signal6_Trend_Days",
        "Williams_R",
    ]
    for c in numeric_cols:
        df[c] = _to_num_series(df[c])

    # Derived fields used by relational alert conditions.
    df["Stoch_KvsD"] = df["Stoch_K"] - df["Stoch_D"]
    df["DI_diff"] = df["PLUS_DI"] - df["MINUS_DI"]
    df["EMA30"] = df["EMA_30"]

    df["Action"] = df["Action"].astype(str).str.upper()
    df["Market_Phase"] = df["Market_Phase"].astype(str).str.upper()
    df["Data_Quality"] = df["Data_Quality"].fillna("OK").astype(str).str.upper()

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

    # Indicazione unica per chi sta valutando un nuovo ingresso. Le vecchie
    # Action restano disponibili internamente, ma HOLD/ADD/REDUCE/EXIT non
    # vengono presentate come istruzioni senza conoscere il portafoglio.
    action_u = df["Action"].astype(str).str.strip().str.upper()
    phase_u = df["Market_Phase"].astype(str).str.strip().str.upper()
    detail_u = df["Trend_Phase_Detail"].astype(str).str.strip().str.upper()
    liquidity_u = df["Liquidity"].astype(str).str.strip().str.upper()
    invalidated = df["Pullback_Invalidation"].astype(str).str.strip().str.upper().isin(["TRUE", "1", "YES"])

    risk = (
        action_u.isin(["SELL", "EXIT", "AVOID"])
        | phase_u.isin(["DOWNTREND", "REVERSAL_RISK", "RIBASSO"])
        | detail_u.isin(["PULLBACK_RISKY", "REVERSAL_RISK", "DOWNTREND", "RIBASSO"])
        | invalidated
        | liquidity_u.eq("AVOID")
    )
    enter = action_u.eq("BUY") & ~risk & liquidity_u.eq("OK")
    observe = (
        ~risk
        & ~enter
        & liquidity_u.eq("OK")
        & (
            action_u.eq("ADD")
            | detail_u.isin(["EARLY_TREND", "EXPANSION", "BREAKOUT_FRESH", "PULLBACK_HEALTHY", "PULLBACK_NORMAL"])
        )
    )

    df["Entry_Signal"] = "ATTENDI"
    df.loc[observe, "Entry_Signal"] = "OSSERVA"
    df.loc[enter, "Entry_Signal"] = "ENTRA"
    df.loc[risk, "Entry_Signal"] = "EVITA"

    df["Entry_Reason"] = "Condizioni di ingresso non ancora complete"
    df.loc[observe, "Entry_Reason"] = "Setup interessante: attendere conferma operativa"
    df.loc[enter, "Entry_Reason"] = "Trigger rialzista completo"
    df.loc[risk, "Entry_Reason"] = "Struttura fragile, rischio o liquidità non idonea"

    # Diagnosi concreta: quali condizioni del trigger di acquisto mancano, con il
    # valore attuale. Senza questo la card mostrava una frase generica identica
    # per situazioni molto diverse (es. TECH 78 con ADX 17 e TECH 44 con DI- > DI+).
    df["Entry_Missing"] = _build_entry_diagnosis(df, action_u, phase_u, detail_u, liquidity_u)

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
    entry_signal: str = "",
) -> pd.DataFrame:
    out = df.copy()

    filters = [
        ("Action", action),
        ("Market_Phase", market_phase),
        ("Trend_Phase_Detail", trend_phase_detail),
        ("Entry_Signal", entry_signal),
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
    if t in {"opportunità", "opportunita", "entra"}:
        return sort_plain(d[d["Entry_Signal"] == "ENTRA"].copy(), ["TECH_SCORE", "PCTV_1D"], [False, False])
    if t in {"da osservare", "osserva"}:
        return sort_plain(d[d["Entry_Signal"] == "OSSERVA"].copy(), ["TECH_SCORE", "PCTV_1D"], [False, False])
    if t in {"attendi", "da attendere"}:
        return sort_plain(d[d["Entry_Signal"] == "ATTENDI"].copy(), ["TECH_SCORE", "PCTV_1D"], [False, False])
    if t in {"da evitare", "evita"}:
        return sort_plain(d[d["Entry_Signal"] == "EVITA"].copy(), ["TECH_SCORE", "PCTV_1D"], [False, False])
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


def sort_watchlist(df: pd.DataFrame, sort_key: str, sort_dir: str) -> pd.DataFrame:
    """Sort the complete filtered result before pagination."""
    allowed = {
        "Ticker", "Close", "PCTV_1D", "PCTV_5D", "TECH_SCORE",
        "MACD_vs_Signal", "SIG_MA_SAR", "RSI", "Williams_R",
    }
    if sort_key not in allowed or sort_key not in df.columns:
        return df

    if sort_key in {"MACD_vs_Signal", "SIG_MA_SAR"}:
        values = pd.to_numeric(df[sort_key], errors="coerce")
        if sort_key == "SIG_MA_SAR":
            # Positivi (1, 2, 3...), negativi crescenti, zero, valori mancanti.
            groups = pd.Series(3, index=df.index)
            groups.loc[values > 0] = 0
            groups.loc[values < 0] = 1
            groups.loc[values == 0] = 2
        else:
            # S3: zero/positivi crescenti, poi negativi crescenti.
            groups = pd.Series(2, index=df.index)
            groups.loc[values >= 0] = 0
            groups.loc[values < 0] = 1
        return (
            df.assign(__sort_group=groups, __sort_value=values)
            .sort_values(["__sort_group", "__sort_value"], ascending=True, na_position="last", kind="mergesort")
            .drop(columns=["__sort_group", "__sort_value"])
        )

    ascending = sort_dir == "asc"
    return df.sort_values(sort_key, ascending=ascending, na_position="last", kind="mergesort")


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    return value


def records(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.where(pd.notna(df), None)
    return [
        {key: _json_safe_value(value) for key, value in row.items()}
        for row in clean.to_dict(orient="records")
    ]
