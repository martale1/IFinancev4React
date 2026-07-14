from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_project_env_file() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_project_env_file()

MARKETS = ["MIB30", "ETC", "ETF", "Preferite", "US_Others", "DAX"]


def _path_from_env(name: str, default: Path) -> Path:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


DEFAULT_ANALYSES_DIR = PROJECT_ROOT / "analyses"
DEFAULT_LOGS_DIR = PROJECT_ROOT / "logs"

ANALYSES_DIR = _path_from_env("ANALYSES_DIR", DEFAULT_ANALYSES_DIR)
LOGS_DIR = _path_from_env("LOGS_DIR", DEFAULT_LOGS_DIR)
ACCESS_LOG_FILE = LOGS_DIR / "access_log.csv"
FRONTEND_DIST_DIR = _path_from_env("FRONTEND_DIST_DIR", PROJECT_ROOT / "frontend" / "dist")

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "").split(",")
    if o.strip()
]
