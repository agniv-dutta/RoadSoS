PYTHON ?= python
UVICORN_HOST ?= 127.0.0.1
UVICORN_PORT ?= 8000

.PHONY: adversarial

adversarial:
	@cd backend && $(PYTHON) -m uvicorn app.main:app --host $(UVICORN_HOST) --port $(UVICORN_PORT) > ../tests/adversarial/.adversarial_server.log 2>&1 & \
	SERVER_PID=$$!; \
	trap 'kill $$SERVER_PID >/dev/null 2>&1 || true' EXIT; \
	$(PYTHON) tests/adversarial/run_adversarial.py --base-url http://$(UVICORN_HOST):$(UVICORN_PORT)