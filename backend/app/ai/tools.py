from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from app.config import MARKETS
from app.services.custom_watchlists_service import custom_markets, is_custom_market, custom_name_from_market, load_custom_watchlist_dataframe, custom_watchlist_source_info
from app.services.watchlist_service import (
    analysis_source_info_for_market,
    apply_search_and_volume_filters,
    filter_by_tab,
    load_market_dataframe,
    prepare_dataframe,
    records,
)

IMPORTANT_COLUMNS = [
    "Ticker",
    "Name",
    "Date",
    "Close",
    "Volume",
    "Action",
    "Market_Phase",
    "TECH_SCORE",
    "PCTV_1D",
    "PCTV_5D",
    "PCTV_10D",
    "PCTV_30D",
    "PCTV_180D",
    "Liquidity",
    "MACD",
    "MACD_Signal",
    "MACD_Hist",
    "MACD_vs_Signal",
    "MACDH_Trend",
    "RSI",
    "RSI_Trend",
    "ADX",
    "ADX_Trend",
    "PLUS_DI",
    "MINUS_DI",
    "ATR_PCT",
    "Vol_Perc_vs_MA20",
    "EMA_30",
    "EMA_50",
    "SAR",
    "SAR_Above_Price",
    "Trend_Stop_Level",
    "CE_Long",
    "SL1_RiskPct",
    "SL2_RiskPct",
    "Profit_Protect_Level",
    "Pullback_Entry_Level",
    "Pullback_Entry_Zone_Low",
    "Pullback_Entry_Zone_High",
    "Pullback_Stop_Level",
    "Layer3_Warning",
    "Action_Reason",
]

SCREENING_FIELD_ALIASES = {
    "ticker": "Ticker",
    "nome": "Name",
    "name": "Name",
    "prezzo": "Close",
    "price": "Close",
    "close": "Close",
    "volume": "Volume",
    "liquidita": "Liquidity",
    "liquidità": "Liquidity",
    "liquidity": "Liquidity",
    "azione": "Action",
    "action": "Action",
    "fase": "Market_Phase",
    "fase mercato": "Market_Phase",
    "market phase": "Market_Phase",
    "score": "TECH_SCORE",
    "tech": "TECH_SCORE",
    "tech score": "TECH_SCORE",
    "rsi": "RSI",
    "trend rsi": "RSI_Trend",
    "macd": "MACD",
    "macd signal": "MACD_Signal",
    "macd hist": "MACD_Hist",
    "s3": "MACD_vs_Signal",
    "macd vs signal": "MACD_vs_Signal",
    "trend macd": "MACDH_Trend",
    "adx": "ADX",
    "trend adx": "ADX_Trend",
    "+di": "PLUS_DI",
    "plus di": "PLUS_DI",
    "-di": "MINUS_DI",
    "minus di": "MINUS_DI",
    "stoch": "Stoch_K",
    "stocastico": "Stoch_K",
    "stoch k": "Stoch_K",
    "stoch d": "Stoch_D",
    "atr": "ATR_PCT",
    "atr pct": "ATR_PCT",
    "vol ma20": "Vol_Perc_vs_MA20",
    "ema30": "EMA_30",
    "ema 30": "EMA_30",
    "ema50": "EMA_50",
    "ema 50": "EMA_50",
    "sar sopra prezzo": "SAR_Above_Price",
    "signal6": "Signal6",
    "warning": "Layer3_Warning",
    "reason": "Action_Reason",
    "stop": "Trend_Stop_Level",
    "sl1": "Trend_Stop_Level",
    "sl2": "CE_Long",
    "rischio sl1": "SL1_RiskPct",
    "rischio sl2": "SL2_RiskPct",
    "pullback entry": "Pullback_Entry_Level",
    "pullback low": "Pullback_Entry_Zone_Low",
    "pullback high": "Pullback_Entry_Zone_High",
    "pullback stop": "Pullback_Stop_Level",
    "profit protect": "Profit_Protect_Level",
}

TAB_ALIASES = {
    "buy": "BUY",
    "acquisti": "BUY",
    "azioni": "AZIONI (tutte)",
    "tutte": "AZIONI (tutte)",
    "all": "AZIONI (tutte)",
    "pullback": "PULLBACK",
    "breakout": "BREAKOUT",
    "sell": "SELL",
    "vendite": "SELL",
    "migliori": "Migliori (1D)",
    "top": "Migliori (1D)",
    "migliori 1d": "Migliori (1D)",
    "migliori 5d": "Migliori (5D)",
    "peggiori": "Peggiori (1D)",
    "peggiori 1d": "Peggiori (1D)",
    "peggiori 5d": "Peggiori (5D)",
}


def _clean_value(v: Any) -> Any:
    if pd.isna(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, datetime):
        return v.isoformat()
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass
    return v


def _compact_record(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in IMPORTANT_COLUMNS:
        if col in row:
            out[col] = _clean_value(row[col])
    return out


def _resolve_field(df: pd.DataFrame, field: str) -> str:
    raw = str(field or "").strip()
    if not raw:
        raise ValueError("Campo filtro mancante.")
    alias = SCREENING_FIELD_ALIASES.get(raw.lower(), raw)
    for col in df.columns:
        if col.lower() == alias.lower():
            return col
    available = ", ".join([c for c in IMPORTANT_COLUMNS if c in df.columns])
    raise ValueError(f"Campo non disponibile: {field}. Campi principali: {available}")


def _value_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _apply_filter(df: pd.DataFrame, field: str, op: str, value: Any) -> pd.DataFrame:
    col = _resolve_field(df, field)
    operator = str(op or "==").strip().lower()
    series = df[col]

    if operator in ["is_null", "null"]:
        return df[series.isna()]
    if operator in ["not_null", "not null"]:
        return df[series.notna()]

    numeric = pd.to_numeric(series, errors="coerce")
    values = _value_list(value)

    def _num(v: Any) -> float:
        return float(str(v).replace(",", ".").strip())

    if operator in [">", ">=", "<", "<="]:
        threshold = _num(value)
        if operator == ">":
            return df[numeric > threshold]
        if operator == ">=":
            return df[numeric >= threshold]
        if operator == "<":
            return df[numeric < threshold]
        return df[numeric <= threshold]

    if operator in ["between", "range"]:
        if len(values) != 2:
            raise ValueError(f"Filtro between su {field} richiede due valori.")
        lo, hi = _num(values[0]), _num(values[1])
        return df[(numeric >= lo) & (numeric <= hi)]

    text = series.astype(str).str.strip()
    value_text = str(value).strip()
    if operator in ["==", "=", "eq"]:
        if pd.api.types.is_numeric_dtype(numeric) and str(value).replace(",", ".").replace(".", "", 1).lstrip("-").isdigit():
            return df[numeric == _num(value)]
        return df[text.str.upper() == value_text.upper()]
    if operator in ["!=", "<>", "ne"]:
        return df[text.str.upper() != value_text.upper()]
    if operator == "contains":
        return df[text.str.contains(value_text, case=False, na=False, regex=False)]
    if operator in ["not_contains", "not contains"]:
        return df[~text.str.contains(value_text, case=False, na=False, regex=False)]
    if operator == "in":
        wanted = {str(v).strip().upper() for v in values}
        return df[text.str.upper().isin(wanted)]
    if operator in ["not_in", "not in"]:
        wanted = {str(v).strip().upper() for v in values}
        return df[~text.str.upper().isin(wanted)]

    raise ValueError(f"Operatore non supportato: {op}")


def normalize_market(market: str | None) -> str:
    raw = str(market or "MIB30").strip()
    if not raw:
        return "MIB30"
    for candidate in MARKETS + custom_markets():
        if candidate.lower() == raw.lower():
            return candidate
    raise ValueError(f"Mercato non supportato: {raw}. Mercati disponibili: {', '.join(MARKETS + custom_markets())}")


def normalize_tab(tab: str | None) -> str:
    raw = str(tab or "BUY").strip()
    if not raw:
        return "BUY"
    direct = {
        "BUY",
        "AZIONI (tutte)",
        "PULLBACK",
        "Migliori (1D)",
        "Migliori (5D)",
        "Peggiori (1D)",
        "Peggiori (5D)",
        "BREAKOUT",
        "SELL",
    }
    for t in direct:
        if t.lower() == raw.lower():
            return t
    alias = TAB_ALIASES.get(raw.lower())
    if alias:
        return alias
    return raw


def _market_dataframe(market: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    market = normalize_market(market)
    if is_custom_market(market):
        name = custom_name_from_market(market)
        return load_custom_watchlist_dataframe(name), custom_watchlist_source_info(name)
    return prepare_dataframe(load_market_dataframe(market)), analysis_source_info_for_market(market)


def list_available_markets_data() -> dict[str, Any]:
    return {"markets": MARKETS + custom_markets()}


def get_screening_fields_data() -> dict[str, Any]:
    return {
        "fields": IMPORTANT_COLUMNS,
        "aliases": SCREENING_FIELD_ALIASES,
        "operators": ["==", "!=", ">", ">=", "<", "<=", "between", "contains", "not_contains", "in", "not_in", "is_null", "not_null"],
        "examples": [
            {"field": "Market_Phase", "op": "==", "value": "PULLBACK"},
            {"field": "RSI", "op": "<", "value": 55},
            {"field": "TECH_SCORE", "op": ">=", "value": 70},
            {"field": "Layer3_Warning", "op": "contains", "value": "Overbought"},
        ],
    }


def screen_tickers_data(
    market: str = "MIB30",
    filters: list[dict[str, Any]] | None = None,
    sort_by: str = "TECH_SCORE",
    sort_dir: str = "desc",
    limit: int = 20,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    market = normalize_market(market)
    safe_limit = max(1, min(int(limit or 20), 100))
    df, source_info = _market_dataframe(market)
    original_count = int(len(df))

    filters_applied: list[dict[str, Any]] = []
    out = df.copy()
    for f in filters or []:
        field = f.get("field")
        op = f.get("op", "==")
        value = f.get("value")
        resolved = _resolve_field(out, str(field))
        out = _apply_filter(out, str(field), str(op), value)
        filters_applied.append({"field": resolved, "op": op, "value": value})

    if sort_by:
        sort_col = _resolve_field(out, sort_by)
        ascending = str(sort_dir or "desc").lower() in ["asc", "ascending", "crescente"]
        sort_values = pd.to_numeric(out[sort_col], errors="coerce")
        if sort_values.notna().any():
            out = out.assign(__sort_value=sort_values).sort_values("__sort_value", ascending=ascending, na_position="last").drop(columns=["__sort_value"])
        else:
            out = out.sort_values(sort_col, ascending=ascending, na_position="last")

    selected_columns = columns or IMPORTANT_COLUMNS
    resolved_columns: list[str] = []
    if columns:
        for c in selected_columns:
            try:
                resolved_columns.append(_resolve_field(out, c))
            except Exception:
                continue

    compact_rows = []
    for row in records(out.head(safe_limit)):
        if columns:
            compact_rows.append({c: _clean_value(row.get(c)) for c in resolved_columns if c in row})
        else:
            compact_rows.append(_compact_record(row))

    return {
        "market": market,
        "source_file": source_info.get("source_file"),
        "source_updated_at": source_info.get("source_updated_at"),
        "initial_rows": original_count,
        "matched_rows": int(len(out)),
        "returned_rows": int(len(compact_rows)),
        "filters_applied": filters_applied,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "items": compact_rows,
    }


def get_top_tickers_data(
    market: str = "MIB30",
    tab: str = "BUY",
    limit: int = 8,
    min_volume: int = 2000,
) -> dict[str, Any]:
    market = normalize_market(market)
    tab = normalize_tab(tab)
    safe_limit = max(1, min(int(limit or 8), 25))
    df, source_info = _market_dataframe(market)
    df = apply_search_and_volume_filters(df, min_volume=max(0, int(min_volume or 0)))
    ranked = filter_by_tab(df, tab, safe_limit, only_neg_in_worst=True).head(safe_limit)
    return {
        "market": market,
        "tab": tab,
        "limit": safe_limit,
        "source_file": source_info.get("source_file"),
        "source_updated_at": source_info.get("source_updated_at"),
        "total": int(len(ranked)),
        "items": [_compact_record(r) for r in records(ranked)],
    }


def get_ticker_snapshot_data(market: str, ticker: str) -> dict[str, Any]:
    market = normalize_market(market)
    ticker_u = str(ticker or "").strip().upper()
    if not ticker_u:
        raise ValueError("Ticker mancante.")

    df, source_info = _market_dataframe(market)
    found = df[df["Ticker"].astype(str).str.strip().str.upper() == ticker_u]
    if found.empty:
        raise FileNotFoundError(f"Ticker '{ticker}' non trovato nel mercato '{market}'.")
    row = records(found.iloc[[0]])[0]
    return {
        "market": market,
        "source_file": source_info.get("source_file"),
        "source_updated_at": source_info.get("source_updated_at"),
        "item": _compact_record(row),
    }


def get_price_sequence_data(ticker: str, period: str = "6mo", bars: int = 30) -> dict[str, Any]:
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        raise ValueError("Ticker mancante.")
    period = str(period or "6mo").strip()
    safe_bars = max(5, min(int(bars or 30), 260))

    try:
        from TechnicalAnalyzer import TechnicalAnalyzer

        ta = TechnicalAnalyzer(ticker=ticker, period=period)
        df = ta.dataframe.copy()
        source = "TechnicalAnalyzer/yfinance"
    except Exception:
        import yfinance as yf

        df = yf.Ticker(ticker).history(period=period, actions=False, auto_adjust=False)
        source = "yfinance"

    if df is None or df.empty:
        raise FileNotFoundError(f"Nessuna serie prezzi trovata per {ticker}.")

    df = df.reset_index().tail(safe_bars)
    cols = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    rows = []
    for row in df[cols].to_dict(orient="records"):
        rows.append({k: _clean_value(v) for k, v in row.items()})

    close = pd.to_numeric(df["Close"], errors="coerce").dropna() if "Close" in df.columns else pd.Series(dtype=float)
    summary: dict[str, Any] = {"bars": int(len(rows))}
    if not close.empty:
        first = float(close.iloc[0])
        last = float(close.iloc[-1])
        summary.update(
            {
                "first_close": round(first, 4),
                "last_close": round(last, 4),
                "pct_change": round(((last / first) - 1.0) * 100.0, 2) if first else None,
                "max_close": round(float(close.max()), 4),
                "min_close": round(float(close.min()), 4),
            }
        )

    return {
        "ticker": ticker,
        "period": period,
        "source": source,
        "summary": summary,
        "prices": rows,
    }
