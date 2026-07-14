from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import ANALYSES_DIR, MARKETS
from app.services.watchlist_service import NEEDED_COLUMNS, load_market_dataframe, prepare_dataframe

CUSTOM_WATCHLISTS_FILE = "custom_watchlists.json"
CUSTOM_MARKET_PREFIX = "WL:"


def custom_watchlists_path() -> Path:
    return ANALYSES_DIR / CUSTOM_WATCHLISTS_FILE


def is_custom_market(market: str) -> bool:
    return str(market).strip().upper().startswith(CUSTOM_MARKET_PREFIX)


def custom_name_from_market(market: str) -> str:
    m = str(market).strip()
    if m.upper().startswith(CUSTOM_MARKET_PREFIX):
        return m[len(CUSTOM_MARKET_PREFIX):].strip()
    return m


def market_from_custom_name(name: str) -> str:
    return f"{CUSTOM_MARKET_PREFIX}{str(name).strip()}"


def _normalize_name(name: str) -> str:
    return " ".join(str(name or "").strip().split())


def _normalize_ticker(ticker: str) -> str:
    return str(ticker or "").strip().upper()


def _normalize_market(market: str) -> str:
    return str(market or "").strip()


def ensure_custom_watchlists_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    base = {"version": 1, "watchlists": {}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(base, f, indent=2, ensure_ascii=False)


def read_custom_watchlists() -> dict[str, Any]:
    path = custom_watchlists_path()
    ensure_custom_watchlists_file(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    data.setdefault("version", 1)
    data.setdefault("watchlists", {})
    return data


def write_custom_watchlists(data: dict[str, Any]) -> None:
    path = custom_watchlists_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_custom_watchlists() -> list[dict[str, Any]]:
    data = read_custom_watchlists()
    watchlists = data.get("watchlists", {}) or {}
    out: list[dict[str, Any]] = []
    for name, cfg in watchlists.items():
        items = (cfg or {}).get("items", []) or []
        out.append({"name": name, "size": len(items)})
    out.sort(key=lambda x: str(x.get("name", "")).lower())
    return out


def custom_markets() -> list[str]:
    return [market_from_custom_name(x["name"]) for x in list_custom_watchlists()]


def create_custom_watchlist(name: str) -> dict[str, Any]:
    wl_name = _normalize_name(name)
    if not wl_name:
        raise ValueError("Watchlist name is required")

    data = read_custom_watchlists()
    watchlists = data.get("watchlists", {}) or {}
    if wl_name in watchlists:
        return {"status": "exists", "name": wl_name}

    watchlists[wl_name] = {"items": [], "created_at": datetime.now().isoformat(timespec="seconds")}
    data["watchlists"] = watchlists
    write_custom_watchlists(data)
    return {"status": "created", "name": wl_name}


def delete_custom_watchlist(name: str) -> dict[str, Any]:
    wl_name = _normalize_name(name)
    if not wl_name:
        raise ValueError("Watchlist name is required")

    data = read_custom_watchlists()
    watchlists = data.get("watchlists", {}) or {}
    if wl_name not in watchlists:
        return {"status": "not_found", "name": wl_name}

    del watchlists[wl_name]
    data["watchlists"] = watchlists
    write_custom_watchlists(data)
    return {"status": "deleted", "name": wl_name}


def add_ticker_to_custom_watchlist(name: str, ticker: str, source_market: str) -> dict[str, Any]:
    wl_name = _normalize_name(name)
    tk = _normalize_ticker(ticker)
    src = _normalize_market(source_market)

    if not wl_name:
        raise ValueError("Watchlist name is required")
    if not tk:
        raise ValueError("Ticker is required")
    if src not in MARKETS:
        raise ValueError(f"Unsupported source market: {src}")

    data = read_custom_watchlists()
    watchlists = data.get("watchlists", {}) or {}
    if wl_name not in watchlists:
        watchlists[wl_name] = {"items": [], "created_at": datetime.now().isoformat(timespec="seconds")}

    cfg = watchlists[wl_name] or {}
    items = cfg.get("items", []) or []
    exists = any(
        _normalize_ticker(i.get("ticker", "")) == tk
        and _normalize_market(i.get("source_market", "")) == src
        for i in items
    )
    if exists:
        return {"status": "exists", "name": wl_name, "ticker": tk, "source_market": src}

    items.append(
        {
            "ticker": tk,
            "source_market": src,
            "added_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    cfg["items"] = items
    cfg["updated_at"] = datetime.now().isoformat(timespec="seconds")
    watchlists[wl_name] = cfg
    data["watchlists"] = watchlists
    write_custom_watchlists(data)
    return {"status": "added", "name": wl_name, "ticker": tk, "source_market": src}


def remove_ticker_from_custom_watchlist(name: str, ticker: str, source_market: str | None = None) -> dict[str, Any]:
    wl_name = _normalize_name(name)
    tk = _normalize_ticker(ticker)
    src = _normalize_market(source_market) if source_market is not None else None

    if not wl_name:
        raise ValueError("Watchlist name is required")
    if not tk:
        raise ValueError("Ticker is required")

    data = read_custom_watchlists()
    watchlists = data.get("watchlists", {}) or {}
    cfg = watchlists.get(wl_name)
    if not cfg:
        return {"status": "not_found", "name": wl_name, "ticker": tk, "source_market": src}

    items = cfg.get("items", []) or []
    before = len(items)
    kept = []
    for i in items:
        i_tk = _normalize_ticker(i.get("ticker", ""))
        i_src = _normalize_market(i.get("source_market", ""))
        same_ticker = i_tk == tk
        same_src = src is None or i_src == src
        if same_ticker and same_src:
            continue
        kept.append(i)

    removed = before - len(kept)
    cfg["items"] = kept
    cfg["updated_at"] = datetime.now().isoformat(timespec="seconds")
    watchlists[wl_name] = cfg
    data["watchlists"] = watchlists
    write_custom_watchlists(data)

    if removed <= 0:
        return {"status": "not_found", "name": wl_name, "ticker": tk, "source_market": src}
    return {"status": "removed", "name": wl_name, "ticker": tk, "source_market": src, "removed": removed}


def custom_watchlist_source_info(name: str) -> dict[str, str]:
    path = custom_watchlists_path()
    st = path.stat() if path.exists() else None
    updated = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds") if st else "-"
    return {"source_file": path.name, "source_path": str(path.resolve()), "source_updated_at": updated, "watchlist_name": name}


def load_custom_watchlist_dataframe(name: str) -> pd.DataFrame:
    wl_name = _normalize_name(name)
    if not wl_name:
        raise ValueError("Watchlist name is required")

    data = read_custom_watchlists()
    watchlists = data.get("watchlists", {}) or {}
    cfg = watchlists.get(wl_name)
    if not cfg:
        return pd.DataFrame(columns=NEEDED_COLUMNS)

    items = cfg.get("items", []) or []
    if not items:
        return pd.DataFrame(columns=NEEDED_COLUMNS)

    per_market_df: dict[str, pd.DataFrame] = {}
    rows: list[pd.DataFrame] = []
    for it in items:
        tk = _normalize_ticker(it.get("ticker", ""))
        src = _normalize_market(it.get("source_market", ""))
        if not tk or src not in MARKETS:
            continue
        if src not in per_market_df:
            per_market_df[src] = prepare_dataframe(load_market_dataframe(src))
        df = per_market_df[src]
        found = df[df["Ticker"].astype(str).str.strip().str.upper() == tk]
        if found.empty:
            continue
        row = found.iloc[[0]].copy()
        row["WL_Source_Market"] = src
        row["WL_Name"] = wl_name
        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=NEEDED_COLUMNS)
    return pd.concat(rows, ignore_index=True)
