#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/.run/ifinance.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "IFinance non risulta attivo."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if ! kill -0 "$PID" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "PID non più attivo; stato ripulito."
  exit 0
fi

echo "Arresto IFinance (PID $PID)..."
kill "$PID"

for _ in {1..15}; do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PID_FILE"
    echo "IFinance arrestato."
    exit 0
  fi
  sleep 1
done

echo "Arresto forzato..."
kill -9 "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
echo "IFinance arrestato."
