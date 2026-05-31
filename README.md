# RoadSoS

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-1f425f?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![httpx](https://img.shields.io/badge/httpx-async-2D2D2D?logo=python&logoColor=white)](https://www.python-httpx.org/)
[![Alembic](https://img.shields.io/badge/Alembic-migrations-8A2BE2)](https://alembic.sqlalchemy.org/)

Emergency road assistance API for the Road Safety Hackathon 2026.

## Overview

RoadSoS is a FastAPI backend for emergency road assistance and nearby-services lookup. It uses async SQLAlchemy sessions, SQLite for development, MySQL for production, and external provider integrations for map and rescue data.

## Tech Stack

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy 2.0 async ORM
- SQLite for development, MySQL for production
- Pydantic v2
- httpx for external API calls
- python-dotenv for environment loading
- Alembic for migrations

## Project Structure

```text
backend/
  app/
    main.py
    config.py
    database.py
    models.py
    schemas.py
    routers/
    services/
    utils/
  .env.example
  requirements.txt
  alembic.ini
  alembic/
```

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

## What is implemented (current)

- Core FastAPI backend with async SQLAlchemy wiring and Alembic scaffold.
- NLU pipeline (regex baseline + optional zero-shot intent classifier) and utilities.
- CAP v1.2 exporter: deterministic transformer that converts NLU output into a standards-compliant CAP JSON packet (build, validate, serialize).
- Dialogue finite-state machine (FSM) using `transitions` with per-session Machines, multilingual follow-up questions, session store with expiry, and a session-aware endpoint `POST /api/triage/parse-message`.
- Integration of CAP exporter into the triage response (attached as `cap_alert` when valid, with `cap_validation_errors` otherwise).
- Unit and integration tests covering CAP exporter, state machine, and triage endpoints. Run with pytest (see below).
- Colab notebook for GPU/remote runs: `backend/app/nlu/colab_train.ipynb` (sanity training + evaluation).
- Server run helper script: `backend/app/nlu/run_server_training.sh` (creates venv, installs deps, runs training/eval).

## Running tests

Activate the project venv and run pytest from the repo root (ensure PYTHONPATH points to `backend` so the `app` package imports work):

Windows PowerShell:

```powershell
& ".venv\Scripts\Activate.ps1"
$env:PYTHONPATH = "backend"
.venv\Scripts\python.exe -m pytest backend/tests -q
```

This repository includes unit tests for the CAP exporter and dialogue FSM, plus integration tests for the triage endpoints. The full suite is green in the development environment used for this work.

## Environment

There are no mandatory third-party free APIs required for local development. The backend works with the default SQLite database and local NLU fallback.

Optional integrations you can enable in `backend/.env`:

- `GOOGLE_PLACES_API_KEY` for live Google Places sync in the admin endpoint.
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` for outbound SMS.
- `DATABASE_URL` if you want MySQL instead of the default SQLite file.

## Docker (optional)

A minimal Dockerfile is provided to run the backend in a container. It is intended for development and smoke tests only (not optimized for production):

```bash
docker build -t roadsos-backend:latest -f backend/Dockerfile backend
docker run --rm -p 8000:8000 --env-file backend/.env roadsos-backend:latest
```

The container starts Uvicorn serving `app.main:app` on port 8000.

## Notes / Next steps

- The NLU training scripts and the production joint XLM-R + CRF model are included under `backend/app/nlu/` (training requires GPUs for reasonable speed). Use the Colab notebook for quick GPU runs.
- The FSM can export a DOT-format graph for audit (call `TriageStateMachine.export_graph(session_id)` from admin tooling).
- If you want I can add a systemd unit, Kubernetes manifest, or CI workflow for tests and linting.

## Migrations

```bash
cd backend
alembic current
alembic upgrade head
```

## API Endpoints

- `GET /api/health`
- `GET /api/nearby`
- `POST /api/sos`
- `POST /api/admin/sync`

## Configuration

Use `backend/.env.example` as the template for local environment variables.

- `DATABASE_URL` switches between SQLite and MySQL.
- `GOOGLE_PLACES_API_KEY` enables external place synchronization.
- `TWILIO_*` settings enable optional SMS delivery.
- `ADMIN_SECRET_KEY` protects the admin sync endpoint.
- `CORS_ORIGINS` controls allowed frontend origins.

## Notes

- `/api/nearby` uses a fast bounding-box SQL prefilter followed by precise haversine distance sorting.
- `/api/sos` logs the event, finds the nearest hospital, and builds Google Maps and WhatsApp links.
- `/api/admin/sync` imports places from Google Places and OSM Overpass, then upserts them into the cache.
