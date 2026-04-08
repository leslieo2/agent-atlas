.PHONY: help install backend-install frontend-install dev lint typecheck test build \
	backend-lint backend-typecheck backend-test backend-ci \
	frontend-lint frontend-typecheck frontend-test frontend-build frontend-ci frontend-e2e \
	contracts-lint contracts-build contracts-test contracts-smoke contracts-ci \
	runner-base-lint runner-base-build runner-base-test runner-base-smoke runner-base-ci \
	runner-langgraph-lint runner-langgraph-build runner-langgraph-test runner-langgraph-smoke runner-langgraph-ci \
	runner-openai-agents-lint runner-openai-agents-build runner-openai-agents-test runner-openai-agents-smoke runner-openai-agents-ci \
	ci-apps ci-packages ci ci-all

CONTROL_PLANE_DIR := apps/control-plane
WEB_DIR := apps/web
CONTRACTS_DIR := packages/contracts/python
RUNNER_BASE_DIR := runtimes/runner-base
RUNNER_LANGGRAPH_DIR := runtimes/runner-langgraph
RUNNER_OPENAI_AGENTS_DIR := runtimes/runner-openai-agents
CI_JOBS ?= $(shell sh -c 'getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 2')

ifneq ($(filter -j -j%,$(MAKEFLAGS)),)
PARALLEL_MAKE_FLAGS :=
else ifeq ($(CI),true)
PARALLEL_MAKE_FLAGS := -j$(CI_JOBS)
else
PARALLEL_MAKE_FLAGS :=
endif

API_HOST ?= 127.0.0.1
API_PORT ?= 8000
FRONTEND_HOST ?= 127.0.0.1
FRONTEND_PORT ?= 3000
PHOENIX_HOST ?= 127.0.0.1
PHOENIX_PORT ?= 6006
REDIS_HOST ?= 127.0.0.1
REDIS_PORT ?= 6379
PHOENIX_WORKING_DIR ?= $(CURDIR)/.phoenix
PHOENIX_PROJECT_NAME ?= agent-atlas-local
PHOENIX_CONTAINER_NAME ?= agent-atlas-phoenix-dev
PHOENIX_IMAGE ?= arizephoenix/phoenix:latest
REDIS_CONTAINER_NAME ?= agent-atlas-redis-dev
REDIS_IMAGE ?= redis:7-alpine

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make install         Install backend and frontend dependencies' \
		'  make backend-install Install backend dependencies' \
		'  make frontend-install Install frontend dependencies' \
		'  make dev             Start Redis/Phoenix, backend API, backend worker, and frontend dev server' \
		'  make lint            Run repo-wide lint and syntax checks serially on local machines' \
		'  make typecheck       Run repo-wide type checks serially on local machines' \
		'  make test            Run app tests and shared package smoke checks serially on local machines' \
		'  make build           Build frontend and Python package distributions serially on local machines' \
		'  make ci-apps         Run app CI checks' \
		'  make ci-packages     Run shared package and runtime CI checks' \
		'  make backend-ci      Run backend CI checks' \
		'  make frontend-ci     Run hermetic frontend CI checks' \
		'  make frontend-e2e    Run frontend local browser smoke checks' \
		'  make ci              Run full monorepo CI coverage serially on local machines'

install: backend-install frontend-install

backend-install:
	$(MAKE) -C $(CONTROL_PLANE_DIR) install

frontend-install:
	npm --prefix $(WEB_DIR) install

dev:
	@set -e; \
	phoenix_container_id=''; \
	redis_container_id=''; \
	api_pid=''; \
	worker_pid=''; \
	frontend_pid=''; \
	phoenix_base_url='http://$(PHOENIX_HOST):$(PHOENIX_PORT)'; \
	phoenix_otlp_endpoint="$$phoenix_base_url/v1/traces"; \
	allowed_origins='["http://localhost:3000","http://127.0.0.1:3000"]'; \
	wait_for_container_removal() { \
		container_name="$$1"; \
		while docker ps -a --format '{{.Names}}' | grep -Fx "$$container_name" >/dev/null 2>&1; do \
			sleep 1; \
		done; \
	}; \
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
		if [ -n "$$redis_container_id" ]; then \
			docker rm -f "$$redis_container_id" >/dev/null 2>&1 || true; \
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
	docker rm -f '$(REDIS_CONTAINER_NAME)' >/dev/null 2>&1 || true; \
	docker rm -f '$(PHOENIX_CONTAINER_NAME)' >/dev/null 2>&1 || true; \
	wait_for_container_removal '$(REDIS_CONTAINER_NAME)'; \
	wait_for_container_removal '$(PHOENIX_CONTAINER_NAME)'; \
	if python3 -c "import socket, sys; s = socket.socket(); s.settimeout(1); code = s.connect_ex(('$(REDIS_HOST)', $(REDIS_PORT))); s.close(); sys.exit(0 if code == 0 else 1)" >/dev/null 2>&1; then \
		printf '%s\n' "Using existing Redis on redis://$(REDIS_HOST):$(REDIS_PORT)/0"; \
	else \
		printf '%s\n' "Starting Redis on redis://$(REDIS_HOST):$(REDIS_PORT)/0"; \
		docker rm -f '$(REDIS_CONTAINER_NAME)' >/dev/null 2>&1 || true; \
		wait_for_container_removal '$(REDIS_CONTAINER_NAME)'; \
		redis_container_id=$$(docker run --rm -d \
			--name '$(REDIS_CONTAINER_NAME)' \
			-p $(REDIS_HOST):$(REDIS_PORT):6379 \
			'$(REDIS_IMAGE)'); \
		until python3 -c "import socket, sys; s = socket.socket(); s.settimeout(1); code = s.connect_ex(('$(REDIS_HOST)', $(REDIS_PORT))); s.close(); sys.exit(0 if code == 0 else 1)" >/dev/null 2>&1; do \
			if [ -z "$$(docker ps -q -f id=$$redis_container_id)" ]; then \
				docker logs "$$redis_container_id" 2>/dev/null || true; \
				exit 1; \
			fi; \
			sleep 1; \
		done; \
	fi; \
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
	+$(MAKE) $(PARALLEL_MAKE_FLAGS) backend-lint frontend-lint contracts-lint runner-base-lint runner-langgraph-lint runner-openai-agents-lint

typecheck:
	+$(MAKE) $(PARALLEL_MAKE_FLAGS) backend-typecheck frontend-typecheck

test:
	+$(MAKE) $(PARALLEL_MAKE_FLAGS) backend-test frontend-test contracts-test contracts-smoke runner-base-test runner-base-smoke runner-langgraph-test runner-langgraph-smoke runner-openai-agents-test runner-openai-agents-smoke

build:
	+$(MAKE) $(PARALLEL_MAKE_FLAGS) frontend-build contracts-build runner-base-build runner-langgraph-build runner-openai-agents-build

backend-lint:
	$(MAKE) -C $(CONTROL_PLANE_DIR) lint

backend-typecheck:
	$(MAKE) -C $(CONTROL_PLANE_DIR) typecheck

backend-test:
	$(MAKE) -C $(CONTROL_PLANE_DIR) test

backend-ci:
	+$(MAKE) -C $(CONTROL_PLANE_DIR) ci

frontend-lint:
	$(MAKE) -C $(WEB_DIR) lint

frontend-typecheck:
	$(MAKE) -C $(WEB_DIR) typecheck

frontend-test:
	$(MAKE) -C $(WEB_DIR) test

frontend-build:
	$(MAKE) -C $(WEB_DIR) build

frontend-ci:
	+$(MAKE) -C $(WEB_DIR) ci

frontend-e2e:
	$(MAKE) -C $(WEB_DIR) e2e

contracts-lint:
	python3 -m compileall -q $(CONTRACTS_DIR)/src

contracts-build:
	cd $(CONTRACTS_DIR) && uv build --sdist --wheel

contracts-test:
	cd $(CONTRACTS_DIR) && uv run --extra dev pytest

contracts-smoke:
	cd $(CONTRACTS_DIR) && uv run --with-editable . python -c "import agent_atlas_contracts"

contracts-ci: contracts-lint contracts-build contracts-test contracts-smoke

runner-base-lint:
	python3 -m compileall -q $(RUNNER_BASE_DIR)/src $(RUNNER_BASE_DIR)/validation

runner-base-build:
	cd $(RUNNER_BASE_DIR) && uv build --sdist --wheel

runner-base-test:
	cd $(RUNNER_BASE_DIR) && uv run --extra dev pytest

runner-base-smoke:
	cd $(RUNNER_BASE_DIR) && uv run --no-project --with-editable ../../packages/contracts/python --with-editable . python -c "import agent_atlas_runner_base"

runner-base-ci: runner-base-lint runner-base-build runner-base-test runner-base-smoke

runner-langgraph-lint:
	python3 -m compileall -q $(RUNNER_LANGGRAPH_DIR)/src

runner-langgraph-build:
	cd $(RUNNER_LANGGRAPH_DIR) && uv build --sdist --wheel

runner-langgraph-test:
	cd $(RUNNER_LANGGRAPH_DIR) && uv run --extra dev pytest

runner-langgraph-smoke:
	cd $(RUNNER_LANGGRAPH_DIR) && uv run --no-project --with-editable ../../packages/contracts/python --with-editable ../runner-base --with-editable . python -c "import agent_atlas_runner_langgraph"

runner-langgraph-ci: runner-langgraph-lint runner-langgraph-build runner-langgraph-test runner-langgraph-smoke

runner-openai-agents-lint:
	python3 -m compileall -q $(RUNNER_OPENAI_AGENTS_DIR)/src

runner-openai-agents-build:
	cd $(RUNNER_OPENAI_AGENTS_DIR) && uv build --sdist --wheel

runner-openai-agents-test:
	cd $(RUNNER_OPENAI_AGENTS_DIR) && uv run --extra dev pytest

runner-openai-agents-smoke:
	cd $(RUNNER_OPENAI_AGENTS_DIR) && uv run --no-project --with-editable ../../packages/contracts/python --with-editable ../runner-base --with-editable . python -c "import agent_atlas_runner_openai_agents"

runner-openai-agents-ci: runner-openai-agents-lint runner-openai-agents-build runner-openai-agents-test runner-openai-agents-smoke

ci-apps: backend-ci frontend-ci

ci-packages: contracts-ci runner-base-ci runner-langgraph-ci runner-openai-agents-ci

ci:
	+$(MAKE) $(PARALLEL_MAKE_FLAGS) ci-all

ci-all: ci-apps ci-packages
