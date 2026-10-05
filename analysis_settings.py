"""Quali mercati analizzare: un'unica sorgente per main.py e per il backend.

La scelta si fa dalla GUI (Gestione Liste) e viene salvata in un **file di dati**
(`analyses/analysis_settings.json`), non nel codice. Così vale anche lanciando
`python main.py` da terminale, non solo quando l'analisi la avvia l'applicazione.

Ordine di precedenza:
  1. variabile d'ambiente `IFINANCE_ANALYSIS_MARKETS` (lanci automatici, script)
  2. file delle impostazioni (scelta fatta dalla GUI)
  3. default MIB30

Il file viene letto in modo difensivo: se manca o è corrotto si ripiega sul
default senza interrompere l'analisi. Un errore di scrittura non deve far
perdere un'analisi.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUPPORTED_MARKETS = ["MIB30", "Preferite", "DAX", "ETC", "ETF", "US_Others", "Crypto"]
DEFAULT_MARKETS = ["MIB30"]
SETTINGS_NAME = "analysis_settings.json"

# Quanto è vecchia l'ultima analisi di un mercato, per avvisare nella GUI.
FILE_TEMPLATE = "{market}_TA_Analyses.xlsx"


def settings_path(analyses_dir: Path) -> Path:
    return Path(analyses_dir) / SETTINGS_NAME


def _valida(markets: Any) -> list[str]:
    """Tiene solo i mercati supportati, senza duplicati."""
    if not isinstance(markets, (list, tuple)):
        return []
    visti: list[str] = []
    for market in markets:
        nome = str(market).strip()
        if nome in SUPPORTED_MARKETS and nome not in visti:
            visti.append(nome)
    return visti


def read_settings(analyses_dir: Path) -> dict[str, Any]:
    """Contenuto del file, o struttura vuota se manca o è illeggibile."""
    path = settings_path(analyses_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(analyses_dir: Path, markets: list[str], alerts: bool | None = None) -> dict[str, Any]:
    """Scrive la scelta. Solleva ValueError se non resta nessun mercato valido."""
    validi = _valida(markets)
    if not validi:
        raise ValueError("Seleziona almeno un mercato valido.")

    precedente = read_settings(analyses_dir)
    data: dict[str, Any] = {
        "markets": validi,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    # `send_alerts` e' un default per i lanci manuali; il valore passato vince.
    if alerts is None:
        if isinstance(precedente.get("send_alerts"), bool):
            data["send_alerts"] = precedente["send_alerts"]
    else:
        data["send_alerts"] = bool(alerts)

    path = settings_path(analyses_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporaneo = path.with_suffix(".tmp")
    temporaneo.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temporaneo.replace(path)  # scrittura atomica: nessun file a meta'
    return data


def resolve_markets(analyses_dir: Path, env_value: str | None = None) -> list[str]:
    """Decide quali mercati analizzare, applicando l'ordine di precedenza."""
    grezzo = os.getenv("IFINANCE_ANALYSIS_MARKETS", "") if env_value is None else env_value
    richiesti = _valida([m for m in str(grezzo or "").split(",") if m.strip()])
    if richiesti:
        return richiesti

    da_file = _valida(read_settings(analyses_dir).get("markets"))
    if da_file:
        return da_file

    return list(DEFAULT_MARKETS)


def resolve_send_alerts(analyses_dir: Path, env_value: str | None = None) -> bool:
    """Se inviare le notifiche Telegram in questa esecuzione."""
    grezzo = os.getenv("IFINANCE_SEND_ALERTS", "") if env_value is None else env_value
    testo = str(grezzo or "").strip().lower()
    if testo in {"0", "false", "no", "off"}:
        return False
    if testo in {"1", "true", "yes", "on"}:
        return True
    salvato = read_settings(analyses_dir).get("send_alerts")
    return bool(salvato) if isinstance(salvato, bool) else True


def market_age(analyses_dir: Path) -> list[dict[str, Any]]:
    """Per ogni mercato: se il workbook esiste e da quando non viene aggiornato."""
    adesso = datetime.now(timezone.utc)
    risultato: list[dict[str, Any]] = []
    for market in SUPPORTED_MARKETS:
        path = Path(analyses_dir) / FILE_TEMPLATE.format(market=market)
        voce: dict[str, Any] = {"market": market, "exists": path.exists()}
        if path.exists():
            modificato = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            voce["updated_at"] = modificato.isoformat(timespec="seconds")
            voce["age_days"] = round((adesso - modificato).total_seconds() / 86400, 1)
        else:
            voce["updated_at"] = None
            voce["age_days"] = None
        risultato.append(voce)
    return risultato
