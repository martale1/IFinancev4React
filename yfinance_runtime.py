"""Configurazione yfinance senza cache persistente tra gli avvii."""
from __future__ import annotations

import atexit
import os
from pathlib import Path

import yfinance as yf


_runtime_root = Path(__file__).resolve().parent / ".ifinance_runtime"
_runtime_root.mkdir(parents=True, exist_ok=True)
_runtime_dir = _runtime_root / f"process-{os.getpid()}"
_runtime_dir.mkdir(parents=False, exist_ok=False)


def _clear_runtime_storage() -> None:
    for path in _runtime_dir.glob("*"):
        if path.is_file():
            path.unlink(missing_ok=True)


_clear_runtime_storage()
yf.set_tz_cache_location(str(_runtime_dir))


@atexit.register
def _remove_runtime_storage() -> None:
    _clear_runtime_storage()
    _runtime_dir.rmdir()
