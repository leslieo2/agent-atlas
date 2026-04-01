.PHONY: help install backend-install frontend-install dev lint typecheck test build backend-ci frontend-ci ci

CONTROL_PLANE_DIR := apps/control-plane
WEB_DIR := apps/web

API_HOST ?= 127.0.0.1
API_PORT ?= 8000
FRONTEND_HOST ?= 127.0.0.1
FRONTEND_PORT ?= 3000
PHOENIX_HOST ?= 127.0.0.1
PHOENIX_PORT ?= 6006
PHOENIX_WORKING_DIR ?= $(CURDIR)/.phoenix
PHOENIX_PROJECT_NAME ?= agent-atlas-local
PHOENIX_CONTAINER_NAME ?= agent-atlas-phoenix-dev
PHOENIX_IMAGE ?= arizephoenix/phoenix:latest

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make install         Install backend and frontend dependencies' \
		'  make backend-install Install backend dependencies' \
		'  make frontend-install Install frontend dependencies' \
		'  make dev             Start Phoenix, backend API, backend worker, and frontend dev server' \
		'  make lint            Run backend and frontend lint checks' \
		'  make typecheck       Run backend and frontend type checks' \
		'  make test            Run backend and frontend tests' \
		'  make build           Run frontend production build' \
		'  make backend-ci      Run backend CI checks' \
		'  make frontend-ci     Run frontend CI checks' \
		'  make ci              Run backend and frontend CI checks'

install: backend-install frontend-install

backend-install:
	$(MAKE) -C $(CONTROL_PLANE_DIR) install

frontend-install:
	npm --prefix $(WEB_DIR) install

dev:
	@set -e; \
	phoenix_container_id=''; \
	api_pid=''; \
	worker_pid=''; \
	frontend_pid=''; \
	phoenix_base_url='http://$(PHOENIX_HOST):$(PHOENIX_PORT)'; \
	phoenix_otlp_endpoint="$$phoenix_base_url/v1/traces"; \
	allowed_origins='["http://localhost:3000","http://127.0.0.1:3000"]'; \
	cleanup() { \
		status=$$?; \
		for pid in "$$api_pid" "$$worker_pid" "$$frontend_pid"; do \
			if [ -n "$$pid" ]; then \
				kill "$$pid" 2>/dev/null || true; \
			fi; \
		done; \
		if [ -n "$$phoenix_container_id" ]; then \
			docker rm -f "$$phoenix_container_id" >/dev/null 2>&1 || true; \
		fi; \
		for pid in "$$api_pid" "$$worker_pid" "$$frontend_pid"; do \
			if [ -n "$$pid" ]; then \
				wait "$$pid" 2>/dev/null || true; \
			fi; \
		done; \
		exit "$$status"; \
	}; \
	trap cleanup INT TERM EXIT; \
	mkdir -p '$(PHOENIX_WORKING_DIR)'; \
	if ! docker info >/dev/null 2>&1; then \
		printf '%s\n' 'Docker is required for `make dev` because Phoenix runs as a local container.'; \
		exit 1; \
	fi; \
	docker rm -f '$(PHOENIX_CONTAINER_NAME)' >/dev/null 2>&1 || true; \
	printf '%s\n' \
		"Starting Phoenix on $$phoenix_base_url" \
		'Starting backend API on http://$(API_HOST):$(API_PORT)' \
		'Starting backend worker' \
		'Starting frontend on http://$(FRONTEND_HOST):$(FRONTEND_PORT)'; \
	phoenix_container_id=$$(docker run --rm -d \
		--name '$(PHOENIX_CONTAINER_NAME)' \
		-p $(PHOENIX_HOST):$(PHOENIX_PORT):6006 \
		-v '$(PHOENIX_WORKING_DIR)':/mnt/data \
		-e PHOENIX_WORKING_DIR=/mnt/data \
		'$(PHOENIX_IMAGE)'); \
	until python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('$(PHOENIX_HOST)', $(PHOENIX_PORT))); s.close()" >/dev/null 2>&1; do \
		if [ -z "$$(docker ps -q -f id=$$phoenix_container_id)" ]; then \
			docker logs "$$phoenix_container_id" 2>/dev/null || true; \
			exit 1; \
		fi; \
		sleep 1; \
	done; \
	AGENT_ATLAS_ALLOWED_ORIGINS="$$allowed_origins" AGENT_ATLAS_PHOENIX_BASE_URL="$$phoenix_base_url" AGENT_ATLAS_PHOENIX_OTLP_ENDPOINT="$$phoenix_otlp_endpoint" AGENT_ATLAS_PHOENIX_PROJECT_NAME='$(PHOENIX_PROJECT_NAME)' $(MAKE) -C $(CONTROL_PLANE_DIR) run-api & \
	api_pid=$$!; \
	AGENT_ATLAS_ALLOWED_ORIGINS="$$allowed_origins" AGENT_ATLAS_PHOENIX_BASE_URL="$$phoenix_base_url" AGENT_ATLAS_PHOENIX_OTLP_ENDPOINT="$$phoenix_otlp_endpoint" AGENT_ATLAS_PHOENIX_PROJECT_NAME='$(PHOENIX_PROJECT_NAME)' $(MAKE) -C $(CONTROL_PLANE_DIR) run-worker & \
	worker_pid=$$!; \
	NEXT_PUBLIC_API_BASE_URL=http://$(API_HOST):$(API_PORT) npm --prefix $(WEB_DIR) run dev -- --hostname $(FRONTEND_HOST) --port $(FRONTEND_PORT) & \
	frontend_pid=$$!; \
	while \
		[ -n "$$(docker ps -q -f id=$$phoenix_container_id)" ] && \
		kill -0 "$$api_pid" 2>/dev/null && \
		kill -0 "$$worker_pid" 2>/dev/null && \
		kill -0 "$$frontend_pid" 2>/dev/null; \
	do \
		sleep 1; \
	done; \
	status=0; \
	set +e; \
	if [ -z "$$(docker ps -q -f id=$$phoenix_container_id)" ]; then \
		docker logs "$$phoenix_container_id" 2>/dev/null || true; \
		status=1; \
	fi; \
	if ! kill -0 "$$api_pid" 2>/dev/null; then \
		wait "$$api_pid"; \
		status=$$?; \
	fi; \
	if ! kill -0 "$$worker_pid" 2>/dev/null; then \
		wait "$$worker_pid"; \
		status=$$?; \
	fi; \
	if ! kill -0 "$$frontend_pid" 2>/dev/null; then \
		wait "$$frontend_pid"; \
		status=$$?; \
	fi; \
	set -e; \
	printf '%s\n' 'A dev process exited; stopping the remaining processes.'; \
	exit "$$status"

lint:
	$(MAKE) -C $(CONTROL_PLANE_DIR) lint
	npm --prefix $(WEB_DIR) run lint

typecheck:
	$(MAKE) -C $(CONTROL_PLANE_DIR) typecheck
	npm --prefix $(WEB_DIR) run typecheck

test:
	$(MAKE) -C $(CONTROL_PLANE_DIR) test
	npm --prefix $(WEB_DIR) run test

build:
	npm --prefix $(WEB_DIR) run build

backend-ci:
	$(MAKE) -C $(CONTROL_PLANE_DIR) ci

frontend-ci:
	npm --prefix $(WEB_DIR) run ci

ci: backend-ci frontend-ci
