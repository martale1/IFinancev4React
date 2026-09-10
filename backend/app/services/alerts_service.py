from __future__ import annotations

import json
import importlib
import os
import re
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any

import pandas as pd
import yaml

from app.config import ANALYSES_DIR
from app.services.watchlist_service import load_market_dataframe, prepare_dataframe

RULES_FILE_TEMPLATE = "alert_rules_{market}.yaml"
STATE_FILE_TEMPLATE = "alert_state_{market}.json"
_RULES_WRITE_LOCK = RLock()


def rules_path_for_market(market: str) -> Path:
    return ANALYSES_DIR / RULES_FILE_TEMPLATE.format(market=str(market))


def state_path_for_market(market: str) -> Path:
    return ANALYSES_DIR / STATE_FILE_TEMPLATE.format(market=str(market))


def ensure_rules_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    base = {
        "version": 1,
        "defaults": {
            "cooldown_minutes": 0,
            "send_on_first_match_only": True,
            "max_per_day": 3,
            "min_gap_minutes": 0,
        },
        "rules": [],
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(base, f, sort_keys=False, allow_unicode=True)


def read_rules_file(path: Path) -> dict[str, Any]:
    ensure_rules_file(path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("version", 1)
    data.setdefault("defaults", {})
    data.setdefault("rules", [])
    data["defaults"].setdefault("cooldown_minutes", 0)
    data["defaults"].setdefault("send_on_first_match_only", True)
    data["defaults"].setdefault("max_per_day", 3)
    data["defaults"].setdefault("min_gap_minutes", 0)
    return data


def write_rules_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with open(temporary_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary_path, path)


def read_state_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f) or {}


def write_state_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _fmt_last_sent_ts(ts: int) -> str:
    try:
        ts = int(ts)
        if ts <= 0:
            return "-"
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"


def _safe_float(x: Any) -> float | None:
    try:
        if x is None or pd.isna(x):
            return None
        if isinstance(x, str):
            x = x.strip().replace("\u202f", "").replace(" ", "").replace(",", ".")
        return float(x)
    except Exception:
        return None


def _eval_op(left: Any, op: str, right: Any) -> bool:
    l = _safe_float(left)
    r = _safe_float(right)

    if l is not None and r is not None:
        if op == ">":
            return l > r
        if op == "<":
            return l < r
        if op == ">=":
            return l >= r
        if op == "<=":
            return l <= r
        if op == "==":
            return l == r
        if op == "!=":
            return l != r
        return False

    ls = str(left).strip()
    rs = str(right).strip()
    if op == "==":
        return ls == rs
    if op == "!=":
        return ls != rs
    return False


def _number_from_trigger(trigger: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", trigger)
    return float(match.group(0).replace(",", ".")) if match else None


def normalize_ai_conditions(raw_conditions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert AI-friendly indicator/trigger pairs into deterministic alert clauses."""
    normalized: list[dict[str, Any]] = []
    unsupported: list[str] = []

    aliases = {
        "price": "Close", "prezzo": "Close", "close": "Close",
        "rsi": "RSI", "adx": "ADX", "macd_hist": "MACD_Hist",
        "williams_r": "Williams_R", "williams %r": "Williams_R",
        "stoch_k": "Stoch_K", "stoch_d": "Stoch_D", "volume": "Volume", "volumi": "Volume",
        "ema30": "EMA30", "ema_30": "EMA30",
    }

    for item in raw_conditions or []:
        indicator_raw = str(item.get("indicator") or item.get("field") or "").strip()
        trigger = str(item.get("trigger") or "").strip()
        field_given = str(item.get("field") or "").strip()
        op_given = str(item.get("op") or "").strip()
        value_given = item.get("value")
        key = indicator_raw.lower().replace("+", "_plus").replace("-", "_minus")

        if field_given and op_given in {"==", "!=", ">", ">=", "<", "<="} and value_given is not None:
            normalized.append({"field": field_given, "op": op_given, "value": value_given,
                               "description": item.get("description", "")})
            continue

        lo = trigger.lower()
        volume_period = re.search(r"(?:ma|media(?:\s+mobile)?)\s*(?:a\s*)?(5|10|20)(?:\s*giorni)?", lo)
        if key in {"volume", "volumi"} and volume_period:
            period = volume_period.group(1)
            multiplier = re.search(r"(?:\*|x)\s*(\d+(?:[.,]\d+)?)", lo)
            threshold_pct = (float(multiplier.group(1).replace(",", ".")) - 1.0) * 100.0 if multiplier else 0.0
            normalized.append({"field": f"Vol_Perc_vs_MA{period}", "op": ">", "value": threshold_pct,
                               "description": item.get("description", trigger)})
            continue
        if key == "macd" and ("cross" in lo or "signal" in lo):
            normalized.append({"field": "MACD_vs_Signal", "op": ">", "value": 0,
                               "description": item.get("description", trigger)})
            if "istogram" in lo and any(word in lo for word in ("positivo", "> 0", "sopra 0")):
                normalized.append({"field": "MACD_Hist", "op": ">", "value": 0,
                                   "description": "Istogramma MACD positivo"})
            continue
        if "adx" in indicator_raw.lower() and "di" in indicator_raw.lower():
            added = False
            di_match = re.search(r"di\s*\+\s*(>=|>)\s*di\s*-", lo)
            if di_match:
                normalized.append({"field": "DI_diff", "op": di_match.group(1), "value": 0,
                                   "description": "DI+ sopra DI-"})
                added = True
            adx_limit = re.search(r"adx\s*(?:sopra|supera|maggiore\s+di|sotto|inferiore\s+a)?\s*(>=|<=|>|<)?\s*(-?\d+(?:[.,]\d+)?)", lo)
            if adx_limit:
                explicit_op = adx_limit.group(1)
                prefix = adx_limit.group(0).lower()
                adx_op = explicit_op or ("<" if any(word in prefix for word in ("sotto", "inferiore")) else ">")
                normalized.append({"field": "ADX", "op": adx_op, "value": float(adx_limit.group(2).replace(",", ".")),
                                   "description": item.get("description", trigger)})
                added = True
            if added:
                continue
        if key in {"di_plus", "di+"} and "di" in lo:
            normalized.append({"field": "DI_diff", "op": ">", "value": 0,
                               "description": item.get("description", trigger)})
            continue
        if key == "alligator" or ("lips" in lo and "teeth" in lo and "jaw" in lo):
            normalized.append({"field": "Signal6", "op": "==", "value": "Uptrend",
                               "description": item.get("description", trigger)})
            continue
        if key == "stoch_k" and "stoch_d" in lo:
            normalized.append({"field": "Stoch_KvsD", "op": ">", "value": 0,
                               "description": "Stoch K sopra Stoch D"})
            for op, value in re.findall(r"stoch_k\s*(>=|<=|>|<)\s*(-?\d+(?:[.,]\d+)?)", lo):
                normalized.append({"field": "Stoch_K", "op": op, "value": float(value.replace(",", ".")),
                                   "description": item.get("description", trigger)})
            continue

        field = aliases.get(key)
        number = _number_from_trigger(trigger)
        op_match = re.search(r"(>=|<=|>|<|==|!=)", trigger)
        if not op_match:
            word_op = ">" if any(x in lo for x in ("sopra", "supera", "maggiore")) else "<" if any(x in lo for x in ("sotto", "inferiore")) else None
        else:
            word_op = op_match.group(1)
        if field and number is not None and word_op:
            normalized.append({"field": field, "op": word_op, "value": number,
                               "description": item.get("description", trigger)})
            if key == "adx" and any(word in lo for word in ("crescente", "in aumento", "rising")):
                normalized.append({"field": "ADX_Change", "op": ">", "value": 0,
                                   "description": "ADX crescente rispetto alla seduta precedente"})
        else:
            unsupported.append(f"{indicator_raw}: {trigger}")

    if unsupported:
        raise ValueError("Condizioni AI non convertibili: " + "; ".join(unsupported))
    if not normalized:
        raise ValueError("Nessuna condizione AI valida")
    return normalized


def create_ai_alert_rule(market: str, ticker: str, raw_conditions: list[dict[str, Any]], title: str | None = None) -> dict[str, Any]:
    ticker = str(ticker).strip().upper()
    if not ticker:
        raise ValueError("Ticker mancante")
    conditions = normalize_ai_conditions(raw_conditions)
    safe_ticker = re.sub(r"[^A-Z0-9]+", "_", ticker).strip("_")
    rule_id = f"AI_{safe_ticker}"
    payload = {
        "id": rule_id,
        "enabled": True,
        "source": "ai",
        "scope": {"tickers": [ticker]},
        "when": {"all": [{"field": c["field"], "op": c["op"], "value": c["value"]} for c in conditions]},
        "ai_conditions": conditions,
        "cooldown_minutes": 0,
        "max_per_day": 3,
        "min_gap_minutes": 0,
        "message": {
            "title": title or "🤖 Alert AI {{Ticker}}",
            "body": "Tutte le condizioni AI sono verificate.\nClose: {{Close}}",
        },
    }
    upsert_rule(market, payload)
    return payload


def create_ai_level_alert_rule(market: str, ticker: str, level: dict[str, Any], current_price: float | None = None) -> dict[str, Any]:
    ticker = str(ticker).strip().upper()
    level_type = str(level.get("type", "")).strip().lower()
    trigger = str(level.get("trigger", "")).strip()
    price = _safe_float(level.get("price"))
    if not ticker or level_type not in {"support", "resistance"} or trigger not in {"<", ">"} or price is None or price <= 0:
        raise ValueError("Livello AI non valido: richiede ticker, type support/resistance, trigger </> e price positivo")
    actual = _safe_float(current_price)
    if actual is not None and ((trigger == ">" and actual >= price) or (trigger == "<" and actual <= price)):
        raise ValueError(f"Livello già superato: prezzo corrente {actual:g}, trigger {trigger} {price:g}")
    safe_ticker = re.sub(r"[^A-Z0-9]+", "_", ticker).strip("_")
    price_key = str(price).replace(".", "_")
    rule_id = f"AI_LEVEL_{safe_ticker}_{level_type.upper()}_{price_key}"
    label = "Supporto" if level_type == "support" else "Resistenza"
    payload = {
        "id": rule_id, "enabled": True, "source": "ai_level",
        "scope": {"tickers": [ticker]},
        "when": {"all": [{"field": "Close", "op": trigger, "value": price}]},
        "ai_level": {"type": level_type, "price": price, "trigger": trigger, "description": str(level.get("description", ""))},
        "cooldown_minutes": 0, "max_per_day": 3, "min_gap_minutes": 0,
        "message": {"title": f"🤖 {label} AI {{Ticker}}", "body": f"{label} critico {trigger} {price}.\nClose: {{{{Close}}}}"},
    }
    upsert_rule(market, payload)
    return payload


def _tickers_from_where_scope(market: str, where: list[dict[str, Any]]) -> list[str]:
    if not where:
        return []
    try:
        df_raw = load_market_dataframe(market)
        df = prepare_dataframe(df_raw)
        out: list[str] = []
        for row in df.to_dict(orient="records"):
            ok = True
            for c in where:
                field = c.get("field")
                op = str(c.get("op", ""))
                val = c.get("value")
                if not _eval_op(row.get(field), op, val):
                    ok = False
                    break
            if ok:
                ticker = str(row.get("Ticker", "")).strip()
                if ticker:
                    out.append(ticker)
        return out
    except Exception:
        return []


def _rule_to_rows(rule: dict[str, Any], market: str, defaults: dict[str, Any]) -> list[dict[str, Any]]:
    scope = (rule.get("scope", {}) or {})
    tickers = scope.get("tickers", []) or []
    where = scope.get("where", []) or []
    if (not tickers) and where:
        tickers = _tickers_from_where_scope(market, where)

    enabled = bool(rule.get("enabled", True))
    rid = str(rule.get("id", "")).strip()

    when = (rule.get("when", {}) or {})
    conds = (when.get("all", []) or [])
    if conds:
        desc = " AND ".join([f"{c.get('field', '?')} {c.get('op', '?')} {c.get('value', '?')}" for c in conds])
    else:
        desc = "-"

    title = ((rule.get("message", {}) or {}).get("title", "") or "").strip()
    max_per_day = int(rule.get("max_per_day", defaults.get("max_per_day", 3)) or 3)
    rows = []
    for t in tickers:
        ticker = str(t).strip()
        if not ticker:
            continue
        rows.append(
            {
                "Market": market,
                "Ticker": ticker,
                "RuleID": rid,
                "Source": str(rule.get("source", "manual")),
                "Enabled": enabled,
                "Tipo": desc,
                "Title": title,
                "Max_Per_Day": max_per_day,
                "Fired_Today": 0,
                "Fired_Total": 0,
                "Last_Alert": "-",
            }
        )
    return rows


def build_alerts_df_for_market(market: str) -> pd.DataFrame:
    rules_data = read_rules_file(rules_path_for_market(market))
    defaults = rules_data.get("defaults", {}) or {}
    rules = rules_data.get("rules", []) or []
    rows: list[dict[str, Any]] = []
    for r in rules:
        rows.extend(_rule_to_rows(r, market, defaults))
    state = read_state_file(state_path_for_market(market))
    today = datetime.now().strftime("%Y-%m-%d")

    if not rows:
        df_rules = pd.DataFrame(columns=["Market", "Ticker", "RuleID", "Source", "Enabled", "Tipo", "Title", "Max_Per_Day", "Fired_Today", "Fired_Total", "Last_Alert"])
    else:
        df_rules = pd.DataFrame(rows)

    # Ensure summary includes rules that have already fired and are only present in state
    # (for example dynamic scope.where rules that might not match current snapshot rows).
    existing_keys = set()
    if not df_rules.empty:
        existing_keys = set(
            df_rules.apply(lambda r: f"{str(r['RuleID']).strip()}__{str(r['Ticker']).strip()}", axis=1).tolist()
        )

    def _rule_desc(rule: dict[str, Any]) -> str:
        when = (rule.get("when", {}) or {})
        conds = (when.get("all", []) or [])
        if not conds:
            return "-"
        return " AND ".join([f"{c.get('field', '?')} {c.get('op', '?')} {c.get('value', '?')}" for c in conds])

    rules_by_id: dict[str, dict[str, Any]] = {}
    for r in rules:
        rid = str(r.get("id", "")).strip()
        if rid:
            rules_by_id[rid] = r

    for key in state.keys():
        if "__" not in key:
            continue
        if key in existing_keys:
            continue
        rid, ticker = key.split("__", 1)
        rid = str(rid).strip()
        ticker = str(ticker).strip()
        if not rid or not ticker:
            continue
        rule = rules_by_id.get(rid, {})
        title = ((rule.get("message", {}) or {}).get("title", "") or "").strip()
        max_per_day = int(rule.get("max_per_day", defaults.get("max_per_day", 3)) or 3)
        enabled = bool(rule.get("enabled", True))
        desc = _rule_desc(rule) if rule else "-"
        df_rules = pd.concat(
            [
                df_rules,
                pd.DataFrame(
                    [
                        {
                            "Market": market,
                            "Ticker": ticker,
                            "RuleID": rid,
                            "Source": str(rule.get("source", "manual")),
                            "Enabled": enabled,
                            "Tipo": desc,
                            "Title": title,
                            "Max_Per_Day": max_per_day,
                            "Fired_Today": 0,
                            "Fired_Total": 0,
                            "Last_Alert": "-",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

    def _key(rid: str, ticker: str) -> str:
        return f"{rid}__{ticker}"

    def _today_count(rid: str, ticker: str) -> int:
        s = state.get(_key(rid, ticker), {}) or {}
        if str(s.get("sent_day", "")) == today:
            return int(s.get("sent_count", 0) or 0)
        return 0

    def _total(rid: str, ticker: str) -> int:
        return int((state.get(_key(rid, ticker), {}) or {}).get("sent_total", 0) or 0)

    def _last(rid: str, ticker: str) -> str:
        return _fmt_last_sent_ts(int((state.get(_key(rid, ticker), {}) or {}).get("last_sent_ts", 0) or 0))

    df_rules["Fired_Today"] = df_rules.apply(lambda r: _today_count(r["RuleID"], r["Ticker"]), axis=1)
    df_rules["Fired_Total"] = df_rules.apply(lambda r: _total(r["RuleID"], r["Ticker"]), axis=1)
    df_rules["Last_Alert"] = df_rules.apply(lambda r: _last(r["RuleID"], r["Ticker"]), axis=1)

    # Live per-condition progress for the dedicated AI alerts view.
    try:
        current = prepare_dataframe(load_market_dataframe(market))
        current_rows = {str(r.get("Ticker", "")).strip(): r for r in current.to_dict(orient="records")}

        def _condition_progress(row: pd.Series) -> str:
            rule = rules_by_id.get(str(row["RuleID"]).strip(), {})
            snapshot = current_rows.get(str(row["Ticker"]).strip(), {})
            details = []
            for cond in ((rule.get("when") or {}).get("all") or []):
                field, op, value = cond.get("field"), cond.get("op"), cond.get("value")
                actual = snapshot.get(field)
                details.append({"field": field, "op": op, "value": value, "actual": actual,
                                "verified": _eval_op(actual, str(op), value)})
            return json.dumps(details, ensure_ascii=False, default=str)

        df_rules["Condition_Status"] = df_rules.apply(_condition_progress, axis=1)
    except Exception:
        df_rules["Condition_Status"] = "[]"
    return df_rules.sort_values(by=["Ticker", "Enabled", "RuleID"], ascending=[True, False, True])


def upsert_rule(market: str, payload: dict[str, Any]) -> dict[str, Any]:
    with _RULES_WRITE_LOCK:
        path = rules_path_for_market(market)
        rules_data = read_rules_file(path)
        rules = rules_data.get("rules", []) or []
        rid = str(payload.get("id", "")).strip()
        if not rid:
            raise ValueError("Rule id is required")
        idx = next((i for i, r in enumerate(rules) if str(r.get("id", "")).strip() == rid), None)
        if idx is None:
            rules.append(payload)
        else:
            rules[idx] = payload
        rules_data["rules"] = rules
        write_rules_file(path, rules_data)
        return rules_data


def delete_rule(market: str, rule_id: str) -> dict[str, Any]:
    with _RULES_WRITE_LOCK:
        path = rules_path_for_market(market)
        rules_data = read_rules_file(path)
        rules_data["rules"] = [r for r in (rules_data.get("rules", []) or []) if str(r.get("id", "")).strip() != str(rule_id).strip()]
        write_rules_file(path, rules_data)

        sp = state_path_for_market(market)
        state = read_state_file(sp)
        rid = str(rule_id).strip()
        for k in list(state.keys()):
            if k == rid or k.startswith(rid + "__"):
                state.pop(k, None)
        write_state_file(sp, state)
        return rules_data


def set_rule_enabled(market: str, rule_id: str, enabled: bool) -> dict[str, Any]:
    with _RULES_WRITE_LOCK:
        path = rules_path_for_market(market)
        rules_data = read_rules_file(path)
        for r in (rules_data.get("rules", []) or []):
            if str(r.get("id", "")).strip() == str(rule_id).strip():
                r["enabled"] = bool(enabled)
                break
        write_rules_file(path, rules_data)
        return rules_data


def run_alert_engine(markets_to_run: list[str], telegram_channel: int = 5) -> dict[str, Any]:
    try:
        mod = importlib.import_module("AlertEngine")
        mod = importlib.reload(mod)
        AlertEngine = getattr(mod, "AlertEngine")
    except Exception as exc:
        raise RuntimeError(
            "Import AlertEngine fallito. Verifica dipendenze backend (es. telepot) e PYTHONPATH."
        ) from exc

    try:
        engine = AlertEngine(
            analyses_dir=str(ANALYSES_DIR),
            markets=markets_to_run,
            telegram_channel=int(telegram_channel),
        )
    except Exception as exc:
        raise RuntimeError(
            "Init AlertEngine fallita. Controlla .env (TELEGRAM_BOT_TOKEN_CH5/DEFAULT e TELEGRAM_RECEIVER_ID)."
        ) from exc

    try:
        return engine.run()
    except Exception as exc:
        raise RuntimeError(
            f"Esecuzione AlertEngine fallita: {type(exc).__name__}: {exc}"
        ) from exc
