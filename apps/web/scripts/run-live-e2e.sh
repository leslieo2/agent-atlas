#!/bin/sh

set -eu

ROOT_DIR=$(cd "$(dirname "$0")/../../.." && pwd)
BACKEND_DIR="$ROOT_DIR/apps/control-plane"
FRONTEND_DIR="$ROOT_DIR/apps/web"
API_PORT="${AGENT_ATLAS_LIVE_API_PORT:-8005}"
WEB_PORT="${AGENT_ATLAS_LIVE_WEB_PORT:-3003}"
API_BASE_URL="http://127.0.0.1:${API_PORT}"
WEB_BASE_URL="http://127.0.0.1:${WEB_PORT}"
DB_URL="sqlite:///${BACKEND_DIR}/.agent-atlas-playwright-live.db"

if [ -z "${AGENT_ATLAS_OPENAI_API_KEY:-}" ]; then
  echo "AGENT_ATLAS_OPENAI_API_KEY is required for live e2e." >&2
  exit 1
fi

cleanup() {
  kill "${FRONTEND_PID:-}" "${WORKER_PID:-}" "${API_PID:-}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

cd "$BACKEND_DIR"
AGENT_ATLAS_CONTROL_PLANE_DATABASE_URL="$DB_URL" AGENT_ATLAS_DATA_PLANE_DATABASE_URL="$DB_URL" AGENT_ATLAS_RUNTIME_MODE=live AGENT_ATLAS_RUNNER_MODE=local AGENT_ATLAS_SEED_DEMO=false \
  .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" \
  >/tmp/agent-atlas-live-api.log 2>&1 &
API_PID=$!

AGENT_ATLAS_CONTROL_PLANE_DATABASE_URL="$DB_URL" AGENT_ATLAS_DATA_PLANE_DATABASE_URL="$DB_URL" AGENT_ATLAS_RUNTIME_MODE=live AGENT_ATLAS_RUNNER_MODE=local AGENT_ATLAS_SEED_DEMO=false \
  AGENT_ATLAS_WORKER_POLL_INTERVAL_SECONDS=0.2 .venv/bin/python -m app.worker \
  >/tmp/agent-atlas-live-worker.log 2>&1 &
WORKER_PID=$!

until curl --noproxy '*' -sf "$API_BASE_URL/health" >/dev/null; do
  sleep 1
done

cd "$FRONTEND_DIR"
NEXT_PUBLIC_API_BASE_URL="$API_BASE_URL" npm run dev -- --hostname 127.0.0.1 --port "$WEB_PORT" \
  >/tmp/agent-atlas-live-frontend.log 2>&1 &
FRONTEND_PID=$!

until curl --noproxy '*' -sf "$WEB_BASE_URL" >/dev/null; do
  sleep 1
done

AGENT_ATLAS_E2E_LIVE=1 AGENT_ATLAS_API_BASE_URL="$API_BASE_URL" PLAYWRIGHT_BASE_URL="$WEB_BASE_URL" \
  npx playwright test e2e/live-smoke.spec.ts --config=playwright.config.ts "$@"
