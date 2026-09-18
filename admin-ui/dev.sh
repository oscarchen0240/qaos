#!/bin/bash
# 一鍵啟動 QAOS 管理介面（後端 :8780 + 前端 Vite :5180）。第一次會自動建 venv / npm install。
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "[dev] 建立 Python venv…"
  python3 -m venv .venv
  .venv/bin/pip install -q --disable-pip-version-check -r backend/requirements.txt
fi
if [ ! -d frontend/node_modules ]; then
  echo "[dev] npm install…"
  (cd frontend && npm install --no-audit --no-fund --loglevel=error)
fi
mkdir -p data

for port in 8780 5180; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[dev] port $port 已被佔用（可能已有一份在跑）。停掉它："
    echo "      kill \$(lsof -t -nP -iTCP:$port -sTCP:LISTEN)"
    exit 1
  fi
done

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "[dev] 後端 http://127.0.0.1:8780  (API docs: /api/docs)"
.venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8780 --reload --reload-dir backend --timeout-graceful-shutdown 3 &

echo "[dev] 前端 http://127.0.0.1:5180"
(cd frontend && npm run dev -- --host 127.0.0.1) &

wait
