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
    "recovery": {"S2": 24, "S3": 18, "S5": 22, "S7": 10, "S8": 12},
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
    pct_1d = _number(row, "PCTV_1D")
    pct_5d = _number(row, "PCTV_5D")
    pct_30d = _number(row, "PCTV_30D")
    pct_180d = _number(row, "PCTV_180D")
    volume_vs_ma20 = _number(row, "Vol_Perc_vs_MA20")
    tech_score = _number(row, "TECH_SCORE", 50.0)
    sar_value = _number(row, "SAR")
    sar_ok = int(_number(row, "SAR_Filter_Ok")) == 1
    sma200_ok = int(_number(row, "SMA200_Filter_Ok")) == 1

    if mode == "recovery":
        # Recovery significa inversione in corso, non solo titolo molto ribassato.
        if pct_30d > -6.0 and pct_180d > -15.0:
            return None
        has_reversal = any(signal["id"] in {"S2", "S5"} for signal in signals)
        if not has_reversal:
            return None
        stoch_k = _number(row, "Stoch_K", 50.0)
        stoch_d = _number(row, "Stoch_D", 50.0)
        bearish_acceleration = pct_1d <= -3.0 or pct_5d <= -7.0
        trend_rejected = not sar_ok and minus_di > plus_di and pct_1d < 0 and stoch_k <= stoch_d
        if bearish_acceleration or trend_rejected:
            return None
        decline_strength = max(max(0.0, -pct_30d - 6.0), max(0.0, (-pct_180d - 15.0) * 0.5))
        signal_score += min(18.0, 8.0 + decline_strength)
        decline_period = "30 giorni" if pct_30d <= -6.0 else "6 mesi"
        decline_value = pct_30d if pct_30d <= -6.0 else pct_180d
        reasons.append(f"Ribasso {decline_value:.1f}% in {decline_period}: base di recupero")
        risk_penalty = 0.0
    else:
        risk_penalty = 0.0

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

    if rsi >= 75:
        risk_penalty += min(10.0, 3.0 + (rsi - 75.0) * 0.7)
        risks.append(f"RSI {rsi:.1f}: possibile sovraestensione")
    if atr_pct >= 7:
        risk_penalty += min(8.0, (atr_pct - 5.0) * 0.8)
        risks.append(f"ATR {atr_pct:.1f}%: volatilità elevata")
    if pct_5d >= 12:
        risk_penalty += min(8.0, (pct_5d - 8.0) * 0.5)
        risks.append(f"+{pct_5d:.1f}% in 5 giorni: ingresso esteso")
    if mode == "recovery":
        if volume_vs_ma20 >= 25:
            quality_score += min(8.0, volume_vs_ma20 / 20.0)
            reasons.append(f"Volume {volume_vs_ma20:+.0f}% rispetto alla media 20g")
        elif volume_vs_ma20 <= -35:
            risk_penalty += 4.0
            risks.append(f"Volume {volume_vs_ma20:.0f}% sotto la media 20g")

    close = _number(row, "Close")
    volume = _number(row, "Volume")
    recovery_state = None
    entry_trigger = None
    invalidation_level = None
    target_2r = None
    entry_distance_pct = None
    setup_risk_pct = None
    entry_status = None
    if mode == "recovery":
        has_confirmation = any(signal["id"] in {"S3", "S7", "S8"} for signal in signals)
        if has_confirmation and sar_ok and plus_di > minus_di:
            recovery_state = "Ripartenza confermata"
        else:
            recovery_state = "Tentativo di recupero"
        high = _number(row, "High", close)
        low = _number(row, "Low", close)
        atr = _number(row, "ATR")
        sar = _number(row, "SAR", low)
        buffer = max(atr * 0.05, close * 0.001)
        entry_trigger = max(close, high) + buffer
        invalidation_level = min(low, sar) - max(atr * 0.20, close * 0.002)
        if entry_trigger > 0 and 0 < invalidation_level < entry_trigger:
            entry_distance_pct = (entry_trigger / close - 1.0) * 100.0 if close > 0 else None
            setup_risk_pct = (entry_trigger - invalidation_level) / entry_trigger * 100.0
            target_2r = entry_trigger + 2.0 * (entry_trigger - invalidation_level)
        if pct_5d >= 12:
            entry_status = "Ingresso esteso: attendere pullback"
        elif recovery_state == "Ripartenza confermata" and setup_risk_pct is not None and setup_risk_pct <= 8:
            entry_status = "Pronto solo sopra conferma"
        elif recovery_state == "Ripartenza confermata":
            entry_status = "Confermato, ma rischio ampio"
        else:
            entry_status = "Monitorare: conferme insufficienti"

    signal_ids = {signal["id"] for signal in signals}
    guidance_trigger = entry_trigger
    if guidance_trigger is None:
        high = _number(row, "High", close)
        atr = _number(row, "ATR")
        guidance_trigger = max(close, high) + max(atr * 0.05, close * 0.001)

    missing_confirmations: list[str] = []
    if mode == "momentum":
        if "S4" not in signal_ids:
            missing_confirmations.append("S4 Momentum")
        if not ({"S7", "S8"} & signal_ids):
            missing_confirmations.append("Alligator Bull o Volume Breakout")
    elif mode == "early_trend":
        if not ({"S3", "S6", "S7"} & signal_ids):
            missing_confirmations.append("MACD, Golden Cross o Alligator")
    elif mode == "reversal":
        if not ({"S2", "S5"} & signal_ids):
            missing_confirmations.append("S2 o RSI Oversold")
        if not ({"S3", "S7", "S8"} & signal_ids):
            missing_confirmations.append("una conferma di ripartenza")
    elif mode == "balanced" and len(signal_ids) < 2:
        missing_confirmations.append("almeno due segnali concordi")

    if mode != "recovery":
        if adx < 20:
            missing_confirmations.append("ADX almeno 20")
        if plus_di <= minus_di:
            missing_confirmations.append("DI+ sopra DI-")
        if not sar_ok:
            missing_confirmations.append("prezzo sopra SAR")
        if not sma200_ok and mode in {"balanced", "early_trend", "momentum"}:
            missing_confirmations.append("recupero SMA200")

    if pct_5d >= 12 or rsi >= 75:
        guidance_status = "PULLBACK"
        guidance_text = "Non inseguire il prezzo: movimento già esteso, attendere pullback e nuova tenuta sopra SAR."
    elif mode == "recovery":
        if entry_status == "Pronto solo sopra conferma":
            guidance_status = "READY"
            guidance_text = "Setup pronto solo al superamento del trigger con volume; evitare l'ingresso se il breakout rientra."
        elif entry_status == "Ingresso esteso: attendere pullback":
            guidance_status = "PULLBACK"
            guidance_text = "Recupero già esteso: attendere un pullback che non violi l'invalidazione."
        else:
            guidance_status = "WAIT"
            guidance_text = "Attendere: il recupero non offre ancora conferme o un rapporto rischio adeguato."
    elif not missing_confirmations:
        guidance_status = "READY"
        guidance_text = "Setup coerente: valutare solo un breakout confermato dal volume oppure un pullback che mantenga il SAR."
    else:
        guidance_status = "WAIT"
        guidance_text = "Attendere ulteriori conferme: " + ", ".join(missing_confirmations) + "."

    if guidance_status == "READY":
        guidance_steps = [
            f"Attendere una chiusura sopra {guidance_trigger:.3f}, non solo un picco intraday.",
            "Cercare volume almeno in linea con la media 20 giorni e DI+ ancora sopra DI-.",
            f"In alternativa attendere un pullback che mantenga il SAR{f' a {sar_value:.3f}' if sar_value > 0 else ''}.",
        ]
    elif guidance_status == "PULLBACK":
        guidance_steps = [
            "Non inseguire il rialzo corrente.",
            "Attendere un rientro ordinato verso l'area di breakout o il SAR, preferibilmente con volumi in calo.",
            "Rivalutare soltanto su una nuova candela rialzista accompagnata dal ritorno dei volumi.",
        ]
    else:
        guidance_steps = [
            "Non usare lo score da solo come segnale d'ingresso.",
            "Rivalutare quando saranno presenti: " + ", ".join(missing_confirmations or ["conferme coerenti con il profilo"]) + ".",
            (f"Prima conferma di prezzo: recupero e tenuta sopra il SAR a {sar_value:.3f}." if not sar_ok and sar_value > 0 else f"Il prezzo deve mantenersi sopra il SAR{f' a {sar_value:.3f}' if sar_value > 0 else ''}."),
        ]

    guidance_invalidation = (
        f"Il setup perde qualità sotto il SAR a {sar_value:.3f} o se DI- torna sopra DI+."
        if sar_value > 0
        else "Il setup perde qualità con nuovi minimi o se DI- torna sopra DI+."
    )

    signals.sort(key=lambda item: (item["days_ago"], -item["points"]))
    return {
        "Ticker": _text(row, "Ticker") or "", "Name": _text(row, "Name") or "",
        "Market": market, "Markets": [market], "ScoreBase": signal_score + quality_score - risk_penalty,
        "Score": 0.0, "Close": close, "Volume": volume, "Turnover": max(0.0, close * volume),
        "RSI": rsi, "ADX": adx, "ATR_PCT": atr_pct, "PCTV_1D": pct_1d,
        "PCTV_5D": pct_5d, "PCTV_30D": pct_30d, "PCTV_180D": pct_180d,
        "Volume_vs_MA20": volume_vs_ma20, "TECH_SCORE": tech_score, "Action": _text(row, "Action"),
        "Recovery_State": recovery_state,
        "Entry_Status": entry_status, "Entry_Trigger": entry_trigger,
        "Invalidation_Level": invalidation_level, "Target_2R": target_2r,
        "Entry_Distance_PCT": entry_distance_pct, "Setup_Risk_PCT": setup_risk_pct,
        "Guidance_Status": guidance_status, "Guidance_Text": guidance_text,
        "Guidance_Trigger": guidance_trigger, "Guidance_Steps": guidance_steps,
        "Guidance_Invalidation": guidance_invalidation,
        "Market_Phase": _text(row, "Market_Phase"), "Signal6": _text(row, "Signal6"),
        "signals": signals, "reasons": reasons, "risks": risks,
    }


def rank_opportunities(
    market: str = "ALL",
    mode: str = "balanced",
    limit: int = 20,
    window: int = 10,
    order: str = "ready",
) -> dict[str, Any]:
    mode = mode.strip().lower()
    if mode not in MODE_WEIGHTS:
        raise ValueError(f"Modalità non supportata: {mode}")
    order = order.strip().lower()
    if order not in {"ready", "score", "recent", "ticker"}:
        raise ValueError(f"Ordinamento non supportato: {order}")
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

    def sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
        if order == "ready":
            status_rank = {"READY": 0, "WAIT": 1, "PULLBACK": 2}
            return (status_rank.get(item["Guidance_Status"], 3), -item["Score"], item["Ticker"])
        if order == "recent":
            most_recent = min((signal["days_ago"] for signal in item["signals"]), default=999)
            return (most_recent, -item["Score"], item["Ticker"])
        if order == "ticker":
            return (item["Ticker"],)
        return (-item["Score"], item["Ticker"])

    deduplicated: dict[str, dict[str, Any]] = {}
    for item in sorted(candidates, key=sort_key):
        key = item["Ticker"].strip().upper()
        existing = deduplicated.get(key)
        if existing is None:
            deduplicated[key] = item
        elif item["Market"] not in existing["Markets"]:
            existing["Markets"].append(item["Market"])
    results = list(deduplicated.values())[:limit]
    return {
        "market": market, "mode": mode, "window": window, "limit": limit, "order": order,
        "total_candidates": len(deduplicated), "skipped_markets": skipped_markets, "results": results,
        "disclaimer": "Ranking quantitativo sperimentale: non costituisce una raccomandazione di investimento.",
    }
