"""Cosa e' cambiato rispetto alla seduta precedente: il blocco "Nuovi oggi".

PERCHE' SERVE UN FILE DI STATO. L'Excel di analisi e' una fotografia: contiene una
riga per titolo, con la data dell'ultima seduta. Non c'e' storico, quindi senza
ricordare com'era la seduta prima non si puo' dire cosa e' cambiato. Il blocco
"Nuovi oggi" della pagina Highlights restava per questo vuoto.

COME FUNZIONA. A ogni richiesta si legge l'Excel e si confronta con l'ultimo
stato salvato in `analyses/highlights_state.json`:

  - se la data dell'analisi e' DIVERSA da quella salvata, si calcolano i
    cambiamenti e si salva il nuovo stato insieme ai cambiamenti calcolati;
  - se la data e' la STESSA, si restituiscono i cambiamenti gia' calcolati.

Cosi' i cambiamenti restano visibili per tutta la giornata invece di sparire
alla prima lettura, e diventano "nuovi" solo quando arriva una nuova analisi.

Cosa si considera un cambiamento, in ordine di importanza:
  1. indicazione (ENTRA/OSSERVA/ATTENDI/EVITA) diversa
  2. fase di mercato diversa (es. LATERALE -> TENDENZA)
  3. un pattern scattato oggi (Pattern_*_Days_Ago == 0)
Di ogni titolo si mostra il cambiamento piu' importante: altrimenti la stessa
riga comparirebbe tre volte.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import ANALYSES_DIR
from app.services.watchlist_service import load_market_dataframe

STATO = ANALYSES_DIR / "highlights_state.json"

# Colonne che si ricordano di ogni titolo.
CAMPI = ("Entry_Signal", "Market_Phase", "Rischio_Trend", "Momento_Trend", "TECH_SCORE")


def _testo(valore: Any) -> str:
    if valore is None:
        return ""
    try:
        import math

        if isinstance(valore, float) and (math.isnan(valore) or math.isinf(valore)):
            return ""
    except Exception:
        pass
    return str(valore).strip()


def _leggi_stato() -> dict[str, Any]:
    try:
        return json.loads(STATO.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _scrivi_stato(stato: dict[str, Any]) -> None:
    """Scrittura atomica: se fallisce, il file precedente resta valido."""
    try:
        STATO.parent.mkdir(parents=True, exist_ok=True)
        temporaneo = STATO.with_suffix(".json.tmp")
        temporaneo.write_text(json.dumps(stato, ensure_ascii=False, indent=2), encoding="utf-8")
        temporaneo.replace(STATO)
    except Exception:
        pass


def _istantanea(market: str) -> tuple[str, dict[str, dict[str, str]]]:
    """Data dell'analisi e stato dei titoli del mercato, letti dall'Excel."""
    df = load_market_dataframe(market)
    if df is None or df.empty or "Ticker" not in df.columns:
        return "", {}

    data = ""
    if "Date" in df.columns:
        try:
            date = df["Date"].dropna().astype(str)
            if len(date):
                data = date.iloc[0][:10]
        except Exception:
            data = ""

    titoli: dict[str, dict[str, str]] = {}
    for _, riga in df.iterrows():
        ticker = _testo(riga.get("Ticker")).upper()
        if not ticker:
            continue
        titoli[ticker] = {campo: _testo(riga.get(campo)) for campo in CAMPI}
    return data, titoli


def _pattern_di_oggi(riga: Any) -> str | None:
    """Il primo pattern che ha `Days_Ago == 0`, cioe' scattato nella seduta."""
    for colonna in riga.index:
        if "Pattern_" in colonna and colonna.endswith("_Days_Ago"):
            valore = riga.get(colonna)
            try:
                if valore is not None and float(valore) == 0.0:
                    return colonna.replace("Pattern_", "").replace("_Days_Ago", "")
            except (TypeError, ValueError):
                continue
    return None


def cambiamenti(markets: list[str]) -> dict[str, Any]:
    """I cambiamenti rispetto allo stato salvato, per i mercati richiesti.

    Restituisce anche `disponibile`: al primo avvio non c'e' nulla con cui
    confrontare, e l'interfaccia deve dirlo invece di mostrare un blocco vuoto
    senza spiegazione.
    """
    stato = _leggi_stato()
    stato.setdefault("markets", {})
    modificato = False
    raccolti: list[dict[str, Any]] = []
    data_corrente = ""

    for market in markets:
        try:
            data, titoli = _istantanea(market)
        except Exception:
            continue
        if not data:
            continue
        data_corrente = data

        precedente = stato["markets"].get(market) or {}
        data_precedente = str(precedente.get("date") or "")

        if data_precedente == data:
            # Stessa analisi: si riusano i cambiamenti gia' calcolati, cosi' il
            # blocco non si svuota alla seconda lettura.
            for voce in precedente.get("changes") or []:
                raccolti.append({**voce, "market": market})
            continue

        vecchi = precedente.get("items") or {}
        cambi_del_giorno: list[dict[str, Any]] = []

        for ticker, valori in titoli.items():
            prima = vecchi.get(ticker)
            if not prima:
                # Titolo nuovo nell'analisi: non e' un "cambiamento" ma vale la
                # pena segnalarlo se l'analisi precedente esisteva.
                if vecchi:
                    cambi_del_giorno.append(
                        {
                            "tipo": "nuovo",
                            "ticker": ticker,
                            "da": "",
                            "a": valori.get("Entry_Signal", ""),
                            "testo": "entrato per la prima volta nell'analisi",
                        }
                    )
                continue

            if prima.get("Entry_Signal") != valori.get("Entry_Signal"):
                cambi_del_giorno.append(
                    {
                        "tipo": "indicazione",
                        "ticker": ticker,
                        "da": prima.get("Entry_Signal", ""),
                        "a": valori.get("Entry_Signal", ""),
                        "testo": f"{prima.get('Entry_Signal', '?')} → {valori.get('Entry_Signal', '?')}",
                    }
                )
            elif prima.get("Market_Phase") != valori.get("Market_Phase"):
                cambi_del_giorno.append(
                    {
                        "tipo": "fase",
                        "ticker": ticker,
                        "da": prima.get("Market_Phase", ""),
                        "a": valori.get("Market_Phase", ""),
                        "testo": f"{prima.get('Market_Phase', '?')} → {valori.get('Market_Phase', '?')}",
                    }
                )

        # Pattern iniziati nella seduta: `Days_Ago == 0` significa che la striscia
        # del pattern e' cominciata oggi (pattern diversi hanno eta' diverse:
        # S7=0 con S2=16 vuol dire che S7 e' nuovo e S2 no). Un solo pattern per
        # titolo, il primo trovato: altrimenti la stessa riga comparirebbe piu' volte.
        try:
            df = load_market_dataframe(market)
            if df is not None and not df.empty:
                gia = {c["ticker"] for c in cambi_del_giorno}
                for _, riga in df.iterrows():
                    ticker = _testo(riga.get("Ticker")).upper()
                    if not ticker or ticker in gia:
                        continue
                    pattern = _pattern_di_oggi(riga)
                    if pattern:
                        cambi_del_giorno.append(
                            {
                                "tipo": "pattern",
                                "ticker": ticker,
                                "da": "",
                                "a": pattern,
                                "testo": f"pattern {pattern} iniziato oggi",
                            }
                        )
                        gia.add(ticker)
        except Exception:
            pass

        # Un titolo, una riga: si tiene il cambiamento piu' importante.
        priorita = {"indicazione": 0, "nuovo": 1, "fase": 2, "pattern": 3}
        per_ticker: dict[str, dict[str, Any]] = {}
        for voce in cambi_del_giorno:
            esistente = per_ticker.get(voce["ticker"])
            if esistente is None or priorita.get(voce["tipo"], 9) < priorita.get(esistente["tipo"], 9):
                per_ticker[voce["ticker"]] = voce
        cambi_del_giorno = list(per_ticker.values())

        peso = {"indicazione": 0, "nuovo": 0, "fase": 1, "pattern": 2}
        cambi_del_giorno.sort(key=lambda c: (peso.get(c["tipo"], 9), c["ticker"]))

        stato["markets"][market] = {
            "date": data,
            "items": titoli,
            "changes": cambi_del_giorno,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        modificato = True
        for voce in cambi_del_giorno:
            raccolti.append({**voce, "market": market})

    if modificato:
        stato["updated_at"] = datetime.now().isoformat(timespec="seconds")
        _scrivi_stato(stato)

    return {
        "date": data_corrente,
        "changes": raccolti,
        "available": bool(raccolti),
    }
