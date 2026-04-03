#!/bin/sh

set -eu

ROOT_DIR=$(cd "$(dirname "$0")/../../.." && pwd)
BACKEND_DIR="$ROOT_DIR/apps/control-plane"
FRONTEND_DIR="$ROOT_DIR/apps/web"

allocate_port() {
  python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
}

append_no_proxy() {
  current_value="$1"
  addition="$2"
  if [ -z "$current_value" ]; then
    printf '%s\n' "$addition"
    return
  fi

  case ",$current_value," in
    *",$addition,"*) printf '%s\n' "$current_value" ;;
    *) printf '%s,%s\n' "$current_value" "$addition" ;;
  esac
}

API_PORT="${AGENT_ATLAS_LIVE_API_PORT:-$(allocate_port)}"
WEB_PORT="${AGENT_ATLAS_LIVE_WEB_PORT:-$(allocate_port)}"
API_BASE_URL="http://127.0.0.1:${API_PORT}"
WEB_BASE_URL="http://127.0.0.1:${WEB_PORT}"
RUN_DIR=$(mktemp -d "${TMPDIR:-/tmp}/agent-atlas-live-e2e.XXXXXX")
CONTROL_DB_URL="sqlite:///${RUN_DIR}/control-plane.db"
DATA_DB_URL="sqlite:///${RUN_DIR}/data-plane.db"
ALLOWED_ORIGINS=$(printf '["%s","%s"]' "$WEB_BASE_URL" "http://localhost:${WEB_PORT}")
NO_PROXY_VALUE=$(append_no_proxy "${NO_PROXY:-}" "127.0.0.1")
NO_PROXY_VALUE=$(append_no_proxy "$NO_PROXY_VALUE" "localhost")

cleanup() {
  kill "${FRONTEND_PID:-}" "${WORKER_PID:-}" "${API_PID:-}" 2>/dev/null || true
  rm -rf "$RUN_DIR"
}

trap cleanup EXIT INT TERM

cd "$BACKEND_DIR"
NO_PROXY="$NO_PROXY_VALUE" no_proxy="$NO_PROXY_VALUE" \
  AGENT_ATLAS_ALLOWED_ORIGINS="$ALLOWED_ORIGINS" \
  AGENT_ATLAS_CONTROL_PLANE_DATABASE_URL="$CONTROL_DB_URL" \
  AGENT_ATLAS_DATA_PLANE_DATABASE_URL="$DATA_DB_URL" \
  AGENT_ATLAS_RUNTIME_MODE=live AGENT_ATLAS_RUNNER_MODE=local AGENT_ATLAS_SEED_DEMO=false \
  .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" \
  >"${RUN_DIR}/api.log" 2>&1 &
API_PID=$!

NO_PROXY="$NO_PROXY_VALUE" no_proxy="$NO_PROXY_VALUE" \
  AGENT_ATLAS_ALLOWED_ORIGINS="$ALLOWED_ORIGINS" \
  AGENT_ATLAS_CONTROL_PLANE_DATABASE_URL="$CONTROL_DB_URL" \
  AGENT_ATLAS_DATA_PLANE_DATABASE_URL="$DATA_DB_URL" \
  AGENT_ATLAS_RUNTIME_MODE=live AGENT_ATLAS_RUNNER_MODE=local AGENT_ATLAS_SEED_DEMO=false \
  AGENT_ATLAS_WORKER_POLL_INTERVAL_SECONDS=0.2 .venv/bin/python -m app.worker \
  >"${RUN_DIR}/worker.log" 2>&1 &
WORKER_PID=$!

until curl --noproxy '*' -sf "$API_BASE_URL/health" >/dev/null; do
  sleep 1
done

cd "$FRONTEND_DIR"
NO_PROXY="$NO_PROXY_VALUE" no_proxy="$NO_PROXY_VALUE" \
  NEXT_PUBLIC_API_BASE_URL="$API_BASE_URL" npm run dev -- --hostname 127.0.0.1 --port "$WEB_PORT" \
  >"${RUN_DIR}/frontend.log" 2>&1 &
FRONTEND_PID=$!

until curl --noproxy '*' -sf "$WEB_BASE_URL" >/dev/null; do
  sleep 1
done

NO_PROXY="$NO_PROXY_VALUE" no_proxy="$NO_PROXY_VALUE" \
  AGENT_ATLAS_E2E_LIVE=1 AGENT_ATLAS_API_BASE_URL="$API_BASE_URL" PLAYWRIGHT_BASE_URL="$WEB_BASE_URL" \
  npx playwright test e2e/live-smoke.spec.ts --config=playwright.config.ts "$@"
