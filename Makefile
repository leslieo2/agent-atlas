.PHONY: help install backend-install frontend-install lint typecheck test build backend-ci frontend-ci ci

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make install         Install backend and frontend dependencies' \
		'  make backend-install Install backend dependencies' \
		'  make frontend-install Install frontend dependencies' \
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
