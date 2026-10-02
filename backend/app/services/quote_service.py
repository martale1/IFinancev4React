from __future__ import annotations

from datetime import datetime
from typing import Any


def _pct_from_positions(closes, last_pos: int, prev_pos: int) -> float | None:
    if len(closes) <= abs(prev_pos):
        return None
    last = float(closes.iloc[last_pos])
    prev = float(closes.iloc[prev_pos])
    if prev == 0:
        return None
    return (last / prev - 1.0) * 100.0


def chart_snapshot(ticker: str) -> dict[str, Any]:
    symbol = str(ticker or "").strip().upper()
    if not symbol:
        raise ValueError("Ticker is required")

    from yfinance_runtime import yf

    tk = yf.Ticker(symbol)
    hist = tk.history(period="1y", interval="1d", actions=False, auto_adjust=False)
    if hist is None or hist.empty or "Close" not in hist.columns:
        raise ValueError(f"No chart data for {symbol}")

    closes = hist["Close"].dropna().astype(float)
    if closes.empty:
        raise ValueError(f"No close data for {symbol}")

    last_price = float(closes.iloc[-1])
    last_date = closes.index[-1].date().isoformat()
    source = "Yahoo Finance / yfinance history"

    try:
        fast = getattr(tk, "fast_info", None)
        if fast:
            fast_price = fast.get("last_price") if hasattr(fast, "get") else getattr(fast, "last_price", None)
            if fast_price is not None:
                fast_price = float(fast_price)
                if fast_price > 0:
                    last_price = fast_price
                    source = "Yahoo Finance / yfinance fast_info + history"
    except Exception:
        pass

    previous_close = float(closes.iloc[-2]) if len(closes) >= 2 else None
    pct_1d = None if not previous_close else (last_price / previous_close - 1.0) * 100.0

    def pct_days(days: int) -> float | None:
        if len(closes) <= days:
            return None
        prev = float(closes.iloc[-1 - days])
        if prev == 0:
            return None
        return (last_price / prev - 1.0) * 100.0

    return {
        "ticker": symbol,
        "close": last_price,
        "date": last_date,
        "previous_close": previous_close,
        "PCTV_1D": pct_1d,
        "PCTV_5D": pct_days(5),
        "PCTV_10D": pct_days(10),
        "PCTV_30D": pct_days(30),
        "PCTV_180D": pct_days(180),
        "source": source,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "delayed": True,
    }


def latest_quote(ticker: str) -> dict[str, Any]:
    snap = chart_snapshot(ticker)
    return {
        "ticker": snap["ticker"],
        "price": snap["close"],
        "previous_close": snap["previous_close"],
        "change": None if snap["previous_close"] is None else snap["close"] - snap["previous_close"],
        "change_percent": snap["PCTV_1D"],
        "price_date": snap["date"],
        "fetched_at": snap["fetched_at"],
        "source": snap["source"],
        "delayed": True,
    }
