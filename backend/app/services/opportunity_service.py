from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.services.watchlist_service import load_market_dataframe, prepare_dataframe


STANDARD_MARKETS = ["MIB30", "DAX", "ETC", "ETF", "Preferite"]
PATTERN_LABELS = {
    "S2": "S2 Reversal", "S3": "S3 MACD Cross", "S4": "S4 Momentum",
    "S5": "RSI Oversold", "S6": "Golden Cross", "S7": "Alligator Bull",
    "S8": "Volume Breakout",
}
MODE_WEIGHTS = {
    "balanced": {"S2": 10, "S3": 12, "S4": 12, "S5": 10, "S6": 14, "S7": 12, "S8": 10},
    "reversal": {"S2": 34, "S5": 38, "S3": 8},
    "early_trend": {"S2": 6, "S3": 22, "S6": 28, "S7": 24},
    "momentum": {"S3": 10, "S4": 34, "S7": 8, "S8": 30},
}


def _number(row: pd.Series, key: str, default: float = 0.0) -> float:
    try:
        value = float(row.get(key, default))
        return value if np.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def _text(row: pd.Series, key: str) -> str | None:
    value = row.get(key)
    if value is None or pd.isna(value):
        return None
    return str(value)


def _freshness(days: int, window: int) -> float:
    if days < 0 or days >= window or days >= 999:
        return 0.0
    return max(0.15, 1.0 - (days / max(window, 1)) * 0.85)


def _score_row(row: pd.Series, market: str, mode: str, window: int) -> dict[str, Any] | None:
    signals: list[dict[str, Any]] = []
    signal_score = 0.0
    for pattern, weight in MODE_WEIGHTS[mode].items():
        days = int(_number(row, f"Pattern_{pattern}_Days_Ago", 999))
        fresh = _freshness(days, window)
        if fresh <= 0:
            continue
        contribution = weight * fresh
        signal_score += contribution
        signals.append({"id": pattern, "label": PATTERN_LABELS[pattern], "days_ago": days, "points": round(contribution, 1)})
    if not signals:
        return None

    reasons: list[str] = []
    risks: list[str] = []
    quality_score = 0.0
    adx = _number(row, "ADX")
    plus_di = _number(row, "PLUS_DI")
    minus_di = _number(row, "MINUS_DI")
    rsi = _number(row, "RSI", 50.0)
    atr_pct = _number(row, "ATR_PCT")
    pct_5d = _number(row, "PCTV_5D")
    tech_score = _number(row, "TECH_SCORE", 50.0)
    sar_ok = int(_number(row, "SAR_Filter_Ok")) == 1
    sma200_ok = int(_number(row, "SMA200_Filter_Ok")) == 1

    if adx >= 20:
        quality_score += min(8.0, (adx - 20.0) / 2.5)
        reasons.append(f"ADX {adx:.1f}: trend con forza")
    else:
        risks.append(f"ADX {adx:.1f}: trend debole")
    if plus_di > minus_di:
        quality_score += 4.0
        reasons.append("DI+ sopra DI-")
    elif minus_di > plus_di:
        quality_score -= 3.0
        risks.append("DI- sopra DI+")
    if sar_ok:
        quality_score += 4.0
        reasons.append("Prezzo sopra SAR")
    else:
        quality_score -= 4.0
        risks.append("Prezzo sotto SAR")
    if sma200_ok:
        quality_score += 4.0
        reasons.append("Prezzo sopra SMA200")
    else:
        quality_score -= 2.0
        risks.append("Prezzo sotto SMA200")
    quality_score += max(-3.0, min(5.0, (tech_score - 50.0) / 10.0))

    risk_penalty = 0.0
    if rsi >= 75:
        risk_penalty += min(10.0, 3.0 + (rsi - 75.0) * 0.7)
        risks.append(f"RSI {rsi:.1f}: possibile sovraestensione")
    if atr_pct >= 7:
        risk_penalty += min(8.0, (atr_pct - 5.0) * 0.8)
        risks.append(f"ATR {atr_pct:.1f}%: volatilità elevata")
    if pct_5d >= 12:
        risk_penalty += min(8.0, (pct_5d - 8.0) * 0.5)
        risks.append(f"+{pct_5d:.1f}% in 5 giorni: ingresso esteso")

    close = _number(row, "Close")
    volume = _number(row, "Volume")
    signals.sort(key=lambda item: (item["days_ago"], -item["points"]))
    return {
        "Ticker": _text(row, "Ticker") or "", "Name": _text(row, "Name") or "",
        "Market": market, "Markets": [market], "ScoreBase": signal_score + quality_score - risk_penalty,
        "Score": 0.0, "Close": close, "Volume": volume, "Turnover": max(0.0, close * volume),
        "RSI": rsi, "ADX": adx, "ATR_PCT": atr_pct, "PCTV_1D": _number(row, "PCTV_1D"),
        "PCTV_5D": pct_5d, "TECH_SCORE": tech_score, "Action": _text(row, "Action"),
        "Market_Phase": _text(row, "Market_Phase"), "Signal6": _text(row, "Signal6"),
        "signals": signals, "reasons": reasons, "risks": risks,
    }


def rank_opportunities(market: str = "ALL", mode: str = "balanced", limit: int = 20, window: int = 10) -> dict[str, Any]:
    mode = mode.strip().lower()
    if mode not in MODE_WEIGHTS:
        raise ValueError(f"Modalità non supportata: {mode}")
    markets = STANDARD_MARKETS if market.upper() == "ALL" else [market]
    candidates: list[dict[str, Any]] = []
    skipped_markets: list[str] = []
    for current_market in markets:
        try:
            dataframe = prepare_dataframe(load_market_dataframe(current_market))
        except Exception:
            skipped_markets.append(current_market)
            continue
        for _, row in dataframe.iterrows():
            candidate = _score_row(row, current_market, mode, window)
            if candidate:
                candidates.append(candidate)

    if candidates:
        turnover = pd.Series([item["Turnover"] for item in candidates], dtype=float)
        liquidity_rank = turnover.rank(method="average", pct=True).fillna(0.0)
        for item, percentile in zip(candidates, liquidity_rank):
            item["Score"] = round(max(0.0, min(100.0, item.pop("ScoreBase") + float(percentile) * 10.0)), 1)
            if percentile >= 0.7:
                item["reasons"].append("Liquidità relativa elevata")
            elif percentile <= 0.2:
                item["risks"].append("Liquidità relativa bassa")

    deduplicated: dict[str, dict[str, Any]] = {}
    for item in sorted(candidates, key=lambda value: (-value["Score"], value["Ticker"])):
        key = item["Ticker"].strip().upper()
        existing = deduplicated.get(key)
        if existing is None:
            deduplicated[key] = item
        elif item["Market"] not in existing["Markets"]:
            existing["Markets"].append(item["Market"])
    results = list(deduplicated.values())[:limit]
    return {
        "market": market, "mode": mode, "window": window, "limit": limit,
        "total_candidates": len(deduplicated), "skipped_markets": skipped_markets, "results": results,
        "disclaimer": "Ranking quantitativo sperimentale: non costituisce una raccomandazione di investimento.",
    }
