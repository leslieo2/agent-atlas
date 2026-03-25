#!/bin/sh

set -eu

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
API_PORT="${AFLIGHT_LIVE_API_PORT:-8005}"
WEB_PORT="${AFLIGHT_LIVE_WEB_PORT:-3003}"
API_BASE_URL="http://127.0.0.1:${API_PORT}"
WEB_BASE_URL="http://127.0.0.1:${WEB_PORT}"
DB_URL="sqlite:///${BACKEND_DIR}/.aflight-playwright-live.db"

if [ -z "${OPENAI_API_KEY:-${AFLIGHT_OPENAI_API_KEY:-}}" ]; then
  echo "OPENAI_API_KEY or AFLIGHT_OPENAI_API_KEY is required for live e2e." >&2
  exit 1
fi

cleanup() {
  kill "${FRONTEND_PID:-}" "${WORKER_PID:-}" "${API_PID:-}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

cd "$BACKEND_DIR"
AFLIGHT_DATABASE_URL="$DB_URL" AFLIGHT_RUNTIME_MODE=live AFLIGHT_RUNNER_MODE=local \
  .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" \
  >/tmp/agent-flight-recorder-live-api.log 2>&1 &
API_PID=$!

AFLIGHT_DATABASE_URL="$DB_URL" AFLIGHT_RUNTIME_MODE=live AFLIGHT_RUNNER_MODE=local \
  AFLIGHT_WORKER_POLL_INTERVAL_SECONDS=0.2 .venv/bin/python -m app.worker \
  >/tmp/agent-flight-recorder-live-worker.log 2>&1 &
WORKER_PID=$!

until curl --noproxy '*' -sf "$API_BASE_URL/health" >/dev/null; do
  sleep 1
done

cd "$FRONTEND_DIR"
NEXT_PUBLIC_API_BASE_URL="$API_BASE_URL" npm run dev -- --hostname 127.0.0.1 --port "$WEB_PORT" \
  >/tmp/agent-flight-recorder-live-frontend.log 2>&1 &
FRONTEND_PID=$!

until curl --noproxy '*' -sf "$WEB_BASE_URL" >/dev/null; do
  sleep 1
done

AFLIGHT_E2E_LIVE=1 AFLIGHT_API_BASE_URL="$API_BASE_URL" PLAYWRIGHT_BASE_URL="$WEB_BASE_URL" \
  npx playwright test e2e/live-smoke.spec.ts --config=playwright.config.ts "$@"
