.PHONY: install install-ci lint typecheck test test-coverage build ci e2e

install:
	npm install

install-ci:
	npm ci

lint:
	npm run lint

typecheck:
	npm run typecheck

test:
	npm run test

test-coverage:
	npm run test:coverage

build:
	npm run build

ci:
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test-coverage
	$(MAKE) build

e2e:
	npm run test:e2e
