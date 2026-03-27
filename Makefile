.PHONY: help install backend-install frontend-install dev lint typecheck test build backend-ci frontend-ci ci

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make install         Install backend and frontend dependencies' \
		'  make backend-install Install backend dependencies' \
		'  make frontend-install Install frontend dependencies' \
		'  make dev             Start backend API, backend worker, and frontend dev server' \
		'  make lint            Run backend and frontend lint checks' \
		'  make typecheck       Run backend and frontend type checks' \
		'  make test            Run backend and frontend tests' \
		'  make build           Run frontend production build' \
		'  make backend-ci      Run backend CI checks' \
		'  make frontend-ci     Run frontend CI checks' \
		'  make ci              Run backend and frontend CI checks'

install: backend-install frontend-install

backend-install:
	$(MAKE) -C backend install

frontend-install:
	npm --prefix frontend install

dev:
	@set -e; \
	api_pid=''; \
	worker_pid=''; \
	frontend_pid=''; \
	cleanup() { \
		status=$$?; \
		for pid in "$$api_pid" "$$worker_pid" "$$frontend_pid"; do \
			if [ -n "$$pid" ]; then \
				kill "$$pid" 2>/dev/null || true; \
			fi; \
		done; \
		for pid in "$$api_pid" "$$worker_pid" "$$frontend_pid"; do \
			if [ -n "$$pid" ]; then \
				wait "$$pid" 2>/dev/null || true; \
			fi; \
		done; \
		exit "$$status"; \
	}; \
	trap cleanup INT TERM EXIT; \
	printf '%s\n' \
		'Starting backend API on http://127.0.0.1:8000' \
		'Starting backend worker' \
		'Starting frontend on http://127.0.0.1:3000'; \
	$(MAKE) -C backend run-api & \
	api_pid=$$!; \
	$(MAKE) -C backend run-worker & \
	worker_pid=$$!; \
	NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm --prefix frontend run dev -- --hostname 127.0.0.1 --port 3000 & \
	frontend_pid=$$!; \
	while \
		kill -0 "$$api_pid" 2>/dev/null && \
		kill -0 "$$worker_pid" 2>/dev/null && \
		kill -0 "$$frontend_pid" 2>/dev/null; \
	do \
		sleep 1; \
	done; \
	status=0; \
	set +e; \
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
	$(MAKE) -C backend lint
	npm --prefix frontend run lint

typecheck:
	$(MAKE) -C backend typecheck
	npm --prefix frontend run typecheck

test:
	$(MAKE) -C backend test
	npm --prefix frontend run test

build:
	npm --prefix frontend run build

backend-ci:
	$(MAKE) -C backend ci

frontend-ci:
	npm --prefix frontend run ci

ci: backend-ci frontend-ci
