#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${IFINANCE_PYTHON:-$HOME/miniforge3/envs/IFinanceTA/bin/python}"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$ROOT_DIR/logs"
PID_FILE="$RUN_DIR/ifinance.pid"
LOG_FILE="$LOG_DIR/ifinance.log"

mkdir -p "$RUN_DIR" "$LOG_DIR"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Errore: Python IFinanceTA non trovato in $PYTHON_BIN"
  exit 1
fi

if [[ ! -s "$ROOT_DIR/.env" ]]; then
  echo "Errore: configura prima $ROOT_DIR/.env"
  exit 1
fi

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE")"
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "IFinance è già attivo (PID $OLD_PID)."
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if [[ ! -f "$ROOT_DIR/frontend/dist/index.html" ]]; then
  echo "Build frontend non trovata: avvio npm install e npm run build..."
  cd "$ROOT_DIR/frontend"
  npm install
  npm run build
fi

echo "Avvio IFinance..."
cd "$ROOT_DIR/backend"
nohup "$PYTHON_BIN" -u -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8011 \
  >"$LOG_FILE" 2>&1 &
PID=$!
echo "$PID" > "$PID_FILE"

for _ in {1..120}; do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "Errore durante l'avvio. Ultime righe del log:"
    tail -n 30 "$LOG_FILE" || true
    rm -f "$PID_FILE"
    exit 1
  fi

  if curl --silent --fail --output /dev/null http://127.0.0.1:8011/api/markets; then
    IP_ADDRESS="$(hostname -I 2>/dev/null | awk '{print $1}')"
    echo "IFinance avviato (PID $PID)."
    echo "Pagina React: http://${IP_ADDRESS:-127.0.0.1}:8011"
    echo "Swagger API:  http://${IP_ADDRESS:-127.0.0.1}:8011/docs"
    echo "Log: $LOG_FILE"
    exit 0
  fi
  sleep 1
done

echo "Il processo è attivo ma non ha risposto entro 120 secondi."
echo "Controlla il log con: tail -f $LOG_FILE"
exit 1
