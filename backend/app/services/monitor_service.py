from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import ANALYSES_DIR, MARKETS
from app.services.watchlist_service import NEEDED_COLUMNS, load_market_dataframe, prepare_dataframe, records

MONITOR_FILE = "monitor_items.json"
# Cache disattivata: 0 significa che ogni richiesta rilegge gli Excel.
# Prima erano 90 secondi, e in un'app di trading servivano prezzi vecchi.
# Rimettere un numero qui riattiva la cache.
MARKET_CACHE_TTL_SECONDS = 0
_prepared_market_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_prepared_market_cache_lock = threading.Lock()


def monitor_path() -> Path:
    return ANALYSES_DIR / MONITOR_FILE


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _normalize_ticker(ticker: str) -> str:
    return str(ticker or "").strip().upper()


def _normalize_market(market: str) -> str:
    return str(market or "").strip()


def _fold(value: Any) -> str:
    """Testo normalizzato per confronti: maiuscolo, senza accenti e punteggiatura."""
    text = str(value or "").strip().upper()
    for accent, plain in (("À", "A"), ("È", "E"), ("É", "E"), ("Ì", "I"), ("Ò", "O"), ("Ù", "U")):
        text = text.replace(accent, plain)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _base_symbol(ticker: str) -> str:
    """LTMC.MI -> LTMC (per riconoscere il ticker scritto senza suffisso di borsa)."""
    return _fold(ticker).split(" ")[0].split(".")[0]


def _is_fund(name: str, ticker: str) -> bool:
    """Gli ETF/fondi hanno nomi lunghissimi che rubano i match ai titoli azionari."""
    text = f"{name} {ticker}".upper()
    return any(tag in text for tag in ("ETF", "UCITS", "ETP", "ETC", "SICAV", "FONDO", " FUND"))


# Indice di ricerca leggero: solo Ticker e Name, normalizzati una volta sola.
# Serve a non preparare l'intero dataframe (decine di colonne) per una ricerca.
_search_index: dict[str, dict[str, list]] = {}
_search_index_time: dict[str, float] = {}
SEARCH_INDEX_TTL_SECONDS = 600
_search_index_lock = threading.Lock()


def _market_search_index(market: str) -> dict[str, list] | None:
    now = time.monotonic()
    cached_at = _search_index_time.get(market)
    if cached_at is not None and now - cached_at < SEARCH_INDEX_TTL_SECONDS:
        return _search_index.get(market)

    with _search_index_lock:
        cached_at = _search_index_time.get(market)
        if cached_at is not None and time.monotonic() - cached_at < SEARCH_INDEX_TTL_SECONDS:
            return _search_index.get(market)
        try:
            df = load_market_dataframe(market)
        except Exception:
            return None
        if df.empty or "Ticker" not in df.columns:
            return None
        tickers = df["Ticker"].astype(str).str.strip()
        names = df["Name"].astype(str).str.strip() if "Name" in df.columns else pd.Series([""] * len(df), index=df.index)
        index = {
            "ticker": tickers.tolist(),
            "ticker_fold": tickers.map(_fold).tolist(),
            "name": names.tolist(),
            "name_fold": names.map(_fold).tolist(),
            "base_fold": [part.split(".")[0] for part in tickers.map(_fold).tolist()],
        }
        _search_index[market] = index
        _search_index_time[market] = time.monotonic()
        return index


def _scan_market(query: str, market: str, candidates: list[dict[str, Any]]) -> None:
    """Cerca `query` in un mercato usando l'indice leggero.

    Un ciclo riga per riga sui mercati grandi costava secondi: qui i confronti
    sono su liste già normalizzate.
    """
    index = _market_search_index(market)
    if not index:
        return

    long_enough = len(query) >= 3
    for ticker, ticker_fold, name, name_fold, base_fold in zip(
        index["ticker"], index["ticker_fold"], index["name"], index["name_fold"], index["base_fold"]
    ):
        if not ticker:
            continue
        if query == ticker_fold:
            score = 100
        elif query == name_fold:
            score = 95
        elif query == base_fold:
            score = 90
        elif long_enough and (name_fold.startswith(query) or ticker_fold.startswith(query) or base_fold.startswith(query)):
            score = 70
        elif long_enough and query in name_fold:
            score = 55
        else:
            continue
        candidates.append({
            "ticker": ticker,
            "name": name or ticker,
            "source_market": market,
            "score": score,
            "is_fund": _is_fund(name, ticker),
        })


# Alias per i nomi che in banca dati non contengono la parola cercata.
COMMON_ALIASES: dict[str, str] = {
    "GENERALI": "G.MI",
    "ASSICURAZIONI GENERALI": "G.MI",
    "FERRARI": "RACE.MI",
    "TELECOM ITALIA": "TIT.MI",
    "TIM": "TIT.MI",
    "UNICREDIT": "UCG.MI",
    "UNIPOL": "UNI.MI",
    "POSTE": "PST.MI",
}


def resolve_input(text: str, source_market: str | None = None) -> dict[str, Any]:
    """Trova il ticker di un titolo a partire da un ticker o da un nome.

    Cerca in tutti i mercati disponibili (o solo in quello indicato) e restituisce
    ticker, nome, mercato, punteggio e le alternative. Serve a non salvare mai una
    stringa che non corrisponde a nessun titolo delle liste.
    """
    raw = str(text or "").strip()
    query = _fold(raw)
    if not query:
        raise ValueError("Scrivi un ticker o il nome del titolo.")

    markets = [source_market] if source_market in MARKETS else MARKETS
    candidates: list[dict[str, Any]] = []

    for market in markets:
        _scan_market(query, market, candidates)
    # Il mercato indicato è solo un suggerimento: se lì non c'è nulla, si allarga
    # la ricerca a tutti i mercati invece di dichiarare "non trovato".
    if not candidates and markets != MARKETS:
        for market in MARKETS:
            _scan_market(query, market, candidates)

    if not candidates:
        alias = COMMON_ALIASES.get(query)
        if alias:
            for market in MARKETS:
                try:
                    df = _prepared_market_dataframe(market)
                except Exception:
                    continue
                hit = df[df["Ticker"].astype(str).str.strip().str.upper() == alias]
                if not hit.empty:
                    row = hit.iloc[0]
                    name = str(row.get("Name") or alias)
                    candidates.append({
                        "ticker": alias,
                        "name": name,
                        "source_market": market,
                        "score": 80,
                        "is_fund": _is_fund(name, alias),
                    })
                    break

    if not candidates:
        return {"found": False, "query": raw, "item": None, "matches": []}

    # Ordine: punteggio, poi titoli azionari prima dei fondi (gli ETF hanno nomi
    # lunghi che altrimenti rubano il match a una società), poi ticker.
    candidates.sort(key=lambda c: (-int(c["score"]), bool(c.get("is_fund")), c["ticker"]))
    return {
        "found": True,
        "query": raw,
        "item": candidates[0],
        "matches": candidates[:10],
    }


def _valid_or_found_market(ticker: str, source_market: str) -> tuple[str, str | None]:
    src = _normalize_market(source_market)
    if src in MARKETS:
        return src, None
    found_src, found_name = find_ticker_market(ticker)
    return found_src, found_name


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
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def list_monitor_items() -> list[dict[str, Any]]:
    items = read_monitor().get("items", []) or []
    out = []
    for item in items:
        tk = _normalize_ticker(item.get("ticker", ""))
        if not tk:
            continue
        src, found_name = _valid_or_found_market(tk, item.get("source_market", ""))
        name = str(item.get("name") or found_name or tk)
        out.append({
            "ticker": tk,
            "source_market": src,
            "name": name,
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
    tk_input = _normalize_ticker(ticker)
    if not tk_input:
        raise ValueError("Ticker is required")

    src = _normalize_market(source_market or "")

    # Il testo inserito può essere un ticker oppure il nome del titolo: va sempre
    # risolto contro le liste, altrimenti si salva una stringa senza dati.
    market_hint = src if src in MARKETS else None
    resolution = resolve_input(tk_input, market_hint)
    if not resolution["found"]:
        raise LookupError(
            f"'{tk_input}' non corrisponde a nessun titolo nei database dei mercati. "
            "Controlla il nome o il ticker."
        )

    best = resolution["item"]
    tk = _normalize_ticker(best["ticker"])
    found_name = str(best.get("name") or tk)

    # Il mercato scelto nel form è solo un suggerimento: se il titolo esiste in un
    # altro mercato lo aggiungiamo lì (segnalandolo), invece di bloccare l'utente
    # o salvarlo nel mercato sbagliato.
    src = str(best["source_market"])
    moved_market = market_hint if (market_hint and market_hint != src) else None

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
            return {"status": "updated", "ticker": tk, "name": name_text or found_name,
                    "source_market": src, "note": item["note"], "input": tk_input}

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
    return {"status": "added", "ticker": tk, "name": name_text or found_name,
            "source_market": src, "note": note_text, "input": tk_input,
            "moved_from_market": moved_market}


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


def _prepared_market_dataframe(market: str) -> pd.DataFrame:
    now = time.monotonic()
    cached = _prepared_market_cache.get(market)
    if cached and now - cached[0] < MARKET_CACHE_TTL_SECONDS:
        return cached[1]
    with _prepared_market_cache_lock:
        now = time.monotonic()
        cached = _prepared_market_cache.get(market)
        if cached and now - cached[0] < MARKET_CACHE_TTL_SECONDS:
            return cached[1]
        df = prepare_dataframe(load_market_dataframe(market))
        _prepared_market_cache[market] = (now, df)
        return df


def load_monitor_dataframe() -> pd.DataFrame:
    items = list_monitor_items()
    if not items:
        return pd.DataFrame(columns=NEEDED_COLUMNS)

    items_by_market: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        items_by_market.setdefault(item["source_market"], []).append(item)

    rows: list[pd.DataFrame] = []
    for src, market_items in items_by_market.items():
        try:
            df = _prepared_market_dataframe(src)
        except Exception:
            df = pd.DataFrame(columns=NEEDED_COLUMNS)

        tickers = [i["ticker"] for i in market_items]
        ticker_series = df.get("Ticker", pd.Series(dtype=str)).astype(str).str.strip().str.upper()
        found_by_ticker = {
            str(row.get("Ticker", "")).strip().upper(): row
            for row in df[ticker_series.isin(tickers)].to_dict("records")
        }

        for item in market_items:
            tk = item["ticker"]
            found = found_by_ticker.get(tk)
            if found is None:
                row = pd.DataFrame([{ "Ticker": tk, "Name": item.get("name") or tk }])
            else:
                row = pd.DataFrame([found])
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


def warm_monitor_cache() -> None:
    try:
        load_monitor_dataframe()
    except Exception:
        return
