from __future__ import annotations

from pathlib import Path

from app.config import ACCESS_LOG_FILE


def access_log_health() -> dict:
    path = Path(ACCESS_LOG_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    writable = True
    error = ""
    try:
        with open(path, "a", encoding="utf-8"):
            pass
    except Exception as exc:
        writable = False
        error = f"{type(exc).__name__}: {exc}"

    return {
        "path": str(path),
        "exists": path.exists(),
        "writable": writable,
        "error": error,
    }

