#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${IFINANCE_PYTHON:-/home/pi/finance-sicilia26/bin/python}"
ACTION="${1:-start}"

export IFINANCE_PYTHON="$PYTHON_BIN"

case "$ACTION" in
  start)
    exec "$ROOT_DIR/start_raspberry.sh"
    ;;
  stop)
    exec "$ROOT_DIR/stop_raspberry.sh"
    ;;
  restart)
    "$ROOT_DIR/stop_raspberry.sh"
    exec "$ROOT_DIR/start_raspberry.sh"
    ;;
  status)
    PID_FILE="$ROOT_DIR/.run/ifinance.pid"
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Sicilia26 attivo (PID $(cat "$PID_FILE"))."
      exit 0
    fi
    echo "Sicilia26 non attivo."
    exit 1
    ;;
  logs)
    exec tail -f "$ROOT_DIR/logs/ifinance.log"
    ;;
  *)
    echo "Uso: $0 {start|stop|restart|status|logs}"
    exit 2
    ;;
esac
