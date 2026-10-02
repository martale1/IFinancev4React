from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import ANALYSES_DIR, MARKETS
from app.services.watchlist_service import NEEDED_COLUMNS, load_market_dataframe, prepare_dataframe, records

MONITOR_FILE = "monitor_items.json"


def monitor_path() -> Path:
    return ANALYSES_DIR / MONITOR_FILE


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_ticker(ticker: str) -> str:
    return str(ticker or "").strip().upper()


def _normalize_market(market: str) -> str:
    return str(market or "").strip()


def ensure_monitor_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "items": []}, f, indent=2, ensure_ascii=False)


def read_monitor() -> dict[str, Any]:
    path = monitor_path()
    ensure_monitor_file(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f) or {}
    data.setdefault("version", 1)
    data.setdefault("items", [])
    return data


def write_monitor(data: dict[str, Any]) -> None:
    path = monitor_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def list_monitor_items() -> list[dict[str, Any]]:
    items = read_monitor().get("items", []) or []
    out = []
    for item in items:
        tk = _normalize_ticker(item.get("ticker", ""))
        src = _normalize_market(item.get("source_market", ""))
        if not tk or src not in MARKETS:
            continue
        out.append({
            "ticker": tk,
            "source_market": src,
            "name": str(item.get("name") or ""),
            "note": str(item.get("note") or ""),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "status": item.get("status") or "active",
        })
    out.sort(key=lambda x: (str(x.get("source_market", "")), str(x.get("ticker", ""))))
    return out


def find_ticker_market(ticker: str) -> tuple[str, str]:
    tk = _normalize_ticker(ticker)
    for m in MARKETS:
        try:
            df = prepare_dataframe(load_market_dataframe(m))
            found = df[df["Ticker"].astype(str).str.strip().str.upper() == tk]
            if not found.empty:
                name = str(found.iloc[0].get("Name") or tk)
                return m, name
        except Exception:
            continue
    return MARKETS[0], tk


def upsert_monitor_item(ticker: str, source_market: str | None = None, note: str | None = None, name: str | None = None) -> dict[str, Any]:
    tk = _normalize_ticker(ticker)
    if not tk:
        raise ValueError("Ticker is required")

    src = _normalize_market(source_market or "")
    if not src or src not in MARKETS:
        found_src, found_name = find_ticker_market(tk)
        src = found_src
        if not name:
            name = found_name

    data = read_monitor()
    items = data.get("items", []) or []
    now = _now()
    note_text = str(note or "").strip()
    name_text = str(name or "").strip()

    for item in items:
        if _normalize_ticker(item.get("ticker", "")) == tk and _normalize_market(item.get("source_market", "")) == src:
            if note is not None:
                item["note"] = note_text
            if name_text:
                item["name"] = name_text
            item["status"] = "active"
            item["updated_at"] = now
            write_monitor(data)
            return {"status": "updated", "ticker": tk, "source_market": src, "note": item["note"]}

    items.append({
        "ticker": tk,
        "source_market": src,
        "name": name_text,
        "note": note_text,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    })
    data["items"] = items
    write_monitor(data)
    return {"status": "added", "ticker": tk, "source_market": src, "note": note_text}


def remove_monitor_item(ticker: str, source_market: str | None = None) -> dict[str, Any]:
    tk = _normalize_ticker(ticker)
    src = _normalize_market(source_market or "")
    if not tk:
        raise ValueError("Ticker is required")

    data = read_monitor()
    items = data.get("items", []) or []
    before = len(items)
    
    kept = []
    for item in items:
        item_tk = _normalize_ticker(item.get("ticker", ""))
        item_src = _normalize_market(item.get("source_market", ""))
        if item_tk == tk and (not src or item_src == src):
            continue
        kept.append(item)

    data["items"] = kept
    write_monitor(data)
    removed = before - len(kept)
    return {"status": "removed" if removed else "not_found", "ticker": tk, "source_market": src, "removed": removed}


def monitor_source_info() -> dict[str, str]:
    path = monitor_path()
    st = path.stat() if path.exists() else None
    updated = datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds") if st else "-"
    return {"source_file": path.name, "source_path": str(path.resolve()), "source_updated_at": updated}


def load_monitor_dataframe() -> pd.DataFrame:
    items = list_monitor_items()
    if not items:
        return pd.DataFrame(columns=NEEDED_COLUMNS)

    per_market_df: dict[str, pd.DataFrame] = {}
    rows: list[pd.DataFrame] = []
    for item in items:
        tk = item["ticker"]
        src = item["source_market"]
        if src not in per_market_df:
            per_market_df[src] = prepare_dataframe(load_market_dataframe(src))
        df = per_market_df[src]
        found = df[df["Ticker"].astype(str).str.strip().str.upper() == tk]
        if found.empty:
            row = pd.DataFrame([{ "Ticker": tk, "Name": item.get("name") or tk }])
        else:
            row = found.iloc[[0]].copy()
        row["WL_Source_Market"] = src
        row["Monitor_Note"] = item.get("note") or ""
        row["Monitor_Created_At"] = item.get("created_at") or ""
        row["Monitor_Updated_At"] = item.get("updated_at") or ""
        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=NEEDED_COLUMNS)
    return pd.concat(rows, ignore_index=True)


def monitor_records() -> list[dict[str, Any]]:
    df = load_monitor_dataframe()
    return records(df)
