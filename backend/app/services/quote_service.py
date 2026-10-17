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


def _snapshot_da_excel(symbol: str) -> dict[str, Any] | None:
    """Prezzo e variazioni dall'Excel di analisi, se il titolo c'e'.

    Restituisce None quando il titolo non compare in nessun mercato analizzato:
    in quel caso chi chiama ripiega su Yahoo.

    Perche' non si usa Yahoo quando l'Excel c'e': l'Excel e' prodotto da
    `main.py` con i dati del giorno dell'analisi. Yahoo puo' essere indietro di
    una seduta (misurato: il 17 ottobre Yahoo non aveva ancora la barra del 16),
    e cosi' card e grafico mostravano numeri diversi per lo stesso titolo.
    """
    try:
        from app.services.watchlist_service import (
            build_analysis_filename,
            analysis_path_for_market,
        )
        from app.config import ANALYSES_DIR
    except Exception:
        return None

    # I mercati con un file di analisi. I nomi devono combaciare con quelli del
    # backend: MIB30, DAX, ETF, ETC, Crypto, US_Others, Preferite.
    mercati = ["MIB30", "DAX", "ETF", "ETC", "Crypto", "US_Others", "Preferite"]
    for mercato in mercati:
        try:
            percorso = analysis_path_for_market(mercato)
        except Exception:
            continue
        try:
            import pandas as pd

            df = pd.read_excel(percorso)
        except Exception:
            continue
        if df is None or df.empty or "Ticker" not in df.columns:
            continue
        riga = df[df["Ticker"].astype(str).str.upper() == symbol]
        if riga.empty:
            continue
        r = riga.iloc[0]

        def numero(colonna: str):
            try:
                valore = r[colonna]
            except Exception:
                return None
            if valore is None:
                return None
            try:
                import math

                f = float(valore)
                if math.isnan(f) or math.isinf(f):
                    return None
                return f
            except (TypeError, ValueError):
                return None

        chiusura = numero("Close")
        if chiusura is None:
            continue

        data = r["Date"] if "Date" in df.columns else None
        data_iso = None
        if data is not None:
            try:
                data_iso = str(data)[:10]
            except Exception:
                data_iso = None

        aggiornato = None
        try:
            from datetime import datetime

            aggiornato = datetime.fromtimestamp(percorso.stat().st_mtime).isoformat(timespec="seconds")
        except Exception:
            pass

        return {
            "ticker": symbol,
            "close": chiusura,
            "date": data_iso,
            "previous_close": None,
            "PCTV_1D": numero("PCTV_1D"),
            "PCTV_5D": numero("PCTV_5D"),
            "PCTV_10D": numero("PCTV_10D"),
            "PCTV_30D": numero("PCTV_30D"),
            "PCTV_180D": numero("PCTV_180D"),
            "source": f"Excel di analisi · {build_analysis_filename(mercato)}",
            "fetched_at": aggiornato,
            "delayed": False,
        }
    return None


def chart_snapshot(ticker: str) -> dict[str, Any]:
    symbol = str(ticker or "").strip().upper()
    if not symbol:
        raise ValueError("Ticker is required")

    # Prima l'Excel: e' la stessa fonte della card, quindi i due numeri coincidono.
    da_excel = _snapshot_da_excel(symbol)
    if da_excel is not None:
        return da_excel

    # Ripiego: Yahoo, per i titoli non ancora analizzati.
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
