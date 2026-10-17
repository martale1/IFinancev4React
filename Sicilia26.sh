#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${IFINANCE_PYTHON:-/home/pi/finance/bin/python}"
ACTION="${1:-start}"
UNIT="ifinance.service"

export IFINANCE_PYTHON="$PYTHON_BIN"

# Se il servizio systemd esiste, i comandi passano da lui.
#
# PERCHE': l'app viene avviata da systemd (riparte da sola dopo un riavvio o una
# caduta di corrente). Se questo script lanciasse anche il vecchio `nohup`, si
# troverebbero due processi a contendersi la porta 8011 e la confusione sarebbe
# garantita: `status` direbbe "non attivo" mentre il sito risponde.
# Cosi' invece lo script resta l'unico comando da ricordare, ma obbedisce a systemd.
#
# Il controllo e' un test sul file, NON una pipe: con `set -o pipefail` un
# `systemctl | grep -q` puo' risultare falso, perche' grep chiude la pipe appena
# trova la riga e systemctl muore di SIGPIPE (exit 141), che pipefail considera
# un errore. E' un errore subdolo: il comando funziona ma la condizione no.
if [[ -f "/etc/systemd/system/${UNIT}" ]] && command -v systemctl >/dev/null 2>&1; then
  case "$ACTION" in
    start)
      exec sudo systemctl start "$UNIT"
      ;;
    stop)
      exec sudo systemctl stop "$UNIT"
      ;;
    restart)
      exec sudo systemctl restart "$UNIT"
      ;;
    status)
      if systemctl is-active --quiet "$UNIT"; then
        echo "Sicilia26 attivo (PID $(systemctl show -p MainPID --value "$UNIT"))."
        echo "  servizio: $UNIT (gestito da systemd)"
        exit 0
      fi
      echo "Sicilia26 non attivo."
      echo "  avvialo con: sudo systemctl start $UNIT"
      exit 1
      ;;
    logs)
      exec sudo journalctl -u "$UNIT" -f -n 40
      ;;
    *)
      echo "Uso: $0 {start|stop|restart|status|logs}"
      exit 2
      ;;
  esac
fi

# Senza systemd, si torna all'avvio manuale di sempre.
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
