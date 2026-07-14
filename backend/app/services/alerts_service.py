from __future__ import annotations

import json
import importlib
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from app.config import ANALYSES_DIR
from app.services.watchlist_service import load_market_dataframe, prepare_dataframe

RULES_FILE_TEMPLATE = "alert_rules_{market}.yaml"
STATE_FILE_TEMPLATE = "alert_state_{market}.json"


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
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


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
        df_rules = pd.DataFrame(columns=["Market", "Ticker", "RuleID", "Enabled", "Tipo", "Title", "Max_Per_Day", "Fired_Today", "Fired_Total", "Last_Alert"])
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
    return df_rules.sort_values(by=["Ticker", "Enabled", "RuleID"], ascending=[True, False, True])


def upsert_rule(market: str, payload: dict[str, Any]) -> dict[str, Any]:
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
