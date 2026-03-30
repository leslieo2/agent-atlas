#!/usr/bin/env sh

set -eu

PORT=3000
HOST=127.0.0.1
BASE_URL="http://${HOST}:${PORT}"
LOG_PATH="/tmp/agent-atlas-playwright.log"
PLAYWRIGHT_ARGS=""

if [ "${1:-}" = "--ui" ]; then
  LOG_PATH="/tmp/agent-atlas-playwright-ui.log"
  PLAYWRIGHT_ARGS="--ui"
fi

if command -v lsof >/dev/null 2>&1; then
  EXISTING_PIDS="$(lsof -ti tcp:${PORT} || true)"
  if [ -n "${EXISTING_PIDS}" ]; then
    kill ${EXISTING_PIDS} 2>/dev/null || true
    sleep 1
  fi
fi

NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --hostname "${HOST}" --port "${PORT}" >"${LOG_PATH}" 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "${SERVER_PID}" 2>/dev/null || true
  wait "${SERVER_PID}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

until curl --noproxy "*" -sf "${BASE_URL}" >/dev/null; do
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    cat "${LOG_PATH}"
    exit 1
  fi
  sleep 1
done

npx playwright test ${PLAYWRIGHT_ARGS}
