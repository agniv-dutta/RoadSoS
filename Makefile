PYTHON ?= python
UVICORN_HOST ?= 127.0.0.1
UVICORN_PORT ?= 8000
FRONTEND_PORT ?= 5173
ADMIN_SECRET_KEY ?= roadsos_admin_2026
COMPOSE ?= docker compose

.PHONY: dev build up down test adversarial bench seed

dev:
	@echo "Starting backend (uvicorn --reload) and frontend (vite)"
	@cd backend && $(PYTHON) -m uvicorn app.main:app --reload --host $(UVICORN_HOST) --port $(UVICORN_PORT) > ../.backend_dev.log 2>&1 & \
	BACK_PID=$$!; \
	cd ../frontend && npm run dev -- --host 0.0.0.0 --port $(FRONTEND_PORT); \
	kill $$BACK_PID >/dev/null 2>&1 || true

build:
	@$(COMPOSE) build

up:
	@$(COMPOSE) up -d

down:
	@$(COMPOSE) down

test:
	@echo "Running backend pytest suite"
	@cd backend && PYTHONPATH=. $(PYTHON) -m pytest ../backend/tests -q
	@echo "Running frontend vitest suite"
	@cd frontend && npm run test -- --run

adversarial:
	@cd backend && $(PYTHON) -m uvicorn app.main:app --host $(UVICORN_HOST) --port $(UVICORN_PORT) > ../tests/adversarial/.adversarial_server.log 2>&1 & \
	SERVER_PID=$$!; \
	trap 'kill $$SERVER_PID >/dev/null 2>&1 || true' EXIT; \
	$(PYTHON) tests/adversarial/run_adversarial.py --base-url http://$(UVICORN_HOST):$(UVICORN_PORT)

bench:
	@cd backend && PYTHONPATH=. $(PYTHON) -m app.nlu.latency_benchmark

seed:
	@echo "Seeding Mumbai and Delhi places via /api/admin/sync"
	@curl -sS -X POST "http://$(UVICORN_HOST):$(UVICORN_PORT)/api/admin/sync" \
		-H "Content-Type: application/json" \
		-H "X-Admin-Key: $(ADMIN_SECRET_KEY)" \
		-d '{"lat":19.0760,"lng":72.8777,"radius_km":12}'
	@curl -sS -X POST "http://$(UVICORN_HOST):$(UVICORN_PORT)/api/admin/sync" \
		-H "Content-Type: application/json" \
		-H "X-Admin-Key: $(ADMIN_SECRET_KEY)" \
		-d '{"lat":28.6139,"lng":77.2090,"radius_km":12}'