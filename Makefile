# Coin Designer — one entry point for both apps.
#
#   make dev        run backend + frontend with hot reload (docker compose)
#   make test       backend pytest + frontend vitest
#   make lint       ruff + eslint/oxlint/prettier + vue-tsc
#   make helm-lint  lint and render both Helm umbrella charts
#   make images     build both container images locally
#   make types      OpenAPI → backend/openapi.json + frontend/src/types/api.d.ts
#   make coin ARGS="build default out.stl"   run the engine CLI
#   make filaments-snapshot   refresh backend/data/filaments.snapshot.json
#
# Targets are phony: they run commands, they do not build files.

.DEFAULT_GOAL := help
SHELL := /bin/bash
UV ?= uv
NPM ?= npm --prefix frontend

.PHONY: help dev dev-backend dev-frontend install test test-backend test-frontend \
        lint lint-backend lint-frontend format helm-lint images types clean \
        coin filaments-snapshot

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install backend and frontend dependencies
	cd backend && $(UV) sync
	$(NPM) ci --no-audit --no-fund

dev: ## Run the local stack with hot reload (docker compose)
	docker compose up --build

dev-backend: ## Run only the backend on :8000 (no docker)
	cd backend && $(UV) run python main.py

dev-frontend: ## Run only the frontend on :5173 (no docker)
	$(NPM) run dev

test: test-backend test-frontend ## Run all tests

test-backend: ## Backend: pytest
	cd backend && $(UV) run pytest -q -W error

test-frontend: ## Frontend: vitest
	$(NPM) run test:unit -- --run

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Backend: ruff check + format check
	cd backend && $(UV) run ruff check . && $(UV) run ruff format --check .

lint-frontend: ## Frontend: oxlint, eslint, prettier check, type-check
	cd frontend && npx oxlint .
	cd frontend && npx eslint .
	cd frontend && npx prettier --check --experimental-cli src/
	$(NPM) run type-check

format: ## Auto-format both apps
	cd backend && $(UV) run ruff check --fix . && $(UV) run ruff format .
	$(NPM) run lint
	$(NPM) run format

helm-lint: ## Lint and render both umbrella charts
	for chart in preview prod; do \
		helm dependency build deploy/$$chart && \
		helm lint deploy/$$chart --set host=pr-0.coins.example && \
		helm template test deploy/$$chart --set host=pr-0.coins.example > /dev/null; \
	done

images: ## Build both container images locally
	docker build -t coin-generator-backend:dev backend
	docker build -t coin-generator-frontend:dev frontend

types: ## Regenerate backend/openapi.json and frontend/src/types/api.d.ts from the app
	cd backend && $(UV) run python -m src.cli openapi > openapi.json
	cd frontend && npx --yes openapi-typescript@7.13.0 ../backend/openapi.json -o src/types/api.d.ts

coin: ## Engine CLI, e.g. make coin ARGS="build default out.stl" (paths relative to backend/)
	cd backend && $(UV) run python -m src.cli $(ARGS)

filaments-snapshot: ## Refresh the committed filamentcolors.xyz snapshot
	cd backend && $(UV) run python -m src.cli filaments-snapshot

clean: ## Remove build artefacts and caches
	rm -rf backend/.venv backend/.pytest_cache backend/.ruff_cache frontend/node_modules frontend/dist deploy/*/charts
