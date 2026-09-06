"""Configurazione yfinance senza cache persistente tra gli avvii."""
from __future__ import annotations

import atexit
import ctypes
import os
import shutil
from pathlib import Path

import yfinance as yf
import yfinance.cache as yf_cache


_runtime_root = Path(__file__).resolve().parent / ".ifinance_runtime"
_runtime_root.mkdir(parents=True, exist_ok=True)


def _remove_tree(path: Path) -> bool:
    try:
        shutil.rmtree(path, ignore_errors=False)
        return True
    except (FileNotFoundError, PermissionError, OSError):
        return False


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        # Su Windows os.kill(pid, 0) non equivale al controllo POSIX: Python
        # può inoltrarlo a TerminateProcess. Interroghiamo invece l'handle del
        # processo senza inviare alcun segnale.
        process_query_limited_information = 0x1000
        still_active = 259
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(
                handle, ctypes.byref(exit_code)
            ):
                return False
            return exit_code.value == still_active
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, SystemError):
        return False


# Rimuove i database temporanei lasciati da processi già terminati. In questo
# momento yfinance non ha ancora aperto alcuna connessione nel nuovo processo.
for stale_dir in _runtime_root.glob("process-*"):
    try:
        stale_pid = int(stale_dir.name.removeprefix("process-"))
    except ValueError:
        stale_pid = -1
    if not _process_exists(stale_pid):
        _remove_tree(stale_dir)

_runtime_dir = _runtime_root / f"process-{os.getpid()}"
_runtime_dir.mkdir(parents=False, exist_ok=False)


def _clear_runtime_storage() -> None:
    for path in _runtime_dir.glob("*"):
        if path.is_file():
            try:
                path.unlink(missing_ok=True)
            except (PermissionError, OSError):
                pass


_clear_runtime_storage()
yf.set_tz_cache_location(str(_runtime_dir))


@atexit.register
def _remove_runtime_storage() -> None:
    # Su Windows cookies.db resta bloccato finché le connessioni peewee non
    # vengono chiuse esplicitamente. Chiuderle prima evita il traceback atexit.
    for manager_name in ("_CookieDBManager", "_TzDBManager", "_ISINDBManager"):
        manager = getattr(yf_cache, manager_name, None)
        if manager is not None:
            try:
                manager.close_db()
            except Exception:
                pass
    _clear_runtime_storage()
    _remove_tree(_runtime_dir)
