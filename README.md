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

## Recent development (May 2026)

Since the initial scaffold this repository has received a set of practical integrations and demo-ready improvements intended for hackathon demos and local development. Key additions include:

- Frontend wiring: a centralized API client, a unified `Zustand` store, and an offline cache with a pending-SOS queue so the UI remains responsive when network connectivity is intermittent.
- Demo mode: open the frontend with `?demo=true` to enable fake GPS, canned nearby results, and immediate SOS demo behavior. There is a backend helper endpoint `GET /api/demo/reset` that clears demo SOS logs and reseeds demo places.
- Seeding: a deterministic seed script populates 20 verified demo places for fast local demos. Run `python backend/scripts/seed_mumbai_places.py` or the `make seed` shortcut in the project Makefile.
- Trust signals: places now include a `data_confidence` score and a `verified` flag exposed by the API; the frontend renders a confidence bar, verified badge, and last-updated staleness coloring to help triage decisions.
- Feedback: users can submit a quick "report incorrect info" form from the place detail page — the backend persists these in a `feedback_reports` table and exposes a POST `/api/feedback` endpoint. An Alembic migration was added for the new table.
- NLU warm-up: the backend pre-warms the NLU inference engine at startup and logs a p50 warm-up latency measurement (example log: "NLU engine ready (p50: 42ms)").
- CAP preview: when triage outputs a high-severity (P1) CAP alert, the frontend shows a CAP v1.2 preview in the triage flow so operators can inspect the generated alert before publishing.

## Frontend (quick notes)

- Location: `frontend/` — built with Vite, React, Tailwind CSS, and Zustand.
- Run locally (dev):

```bash
cd frontend
npm install
npm run dev
```

- Build for production:

```bash
cd frontend
npm run build
```

- The frontend includes:
  - A centralized Axios client at `frontend/src/api/index.js` that talks to the backend API and implements a silent cached fallback for `/api/nearby` when upstream calls exceed a short timeout.
  - An offline cache at `frontend/src/utils/offlineCache.js` which queues SOS submissions while offline and syncs them on reconnect.
  - A demo helper (`?demo=true`) that preserves the query param across navigation and enables deterministic demo flows.

## Integrations (Geoapify / Google Places / Twilio)

This project supports multiple provider integrations. Set these in `backend/.env` (or in your environment) as needed:

- `GOOGLE_PLACES_API_KEY` — optional; used by the admin sync tooling to import place data from Google Places.
- `GEOAPIFY_API_KEY` — optional; an alternative mapping/provider that can be used for geocoding or places import depending on admin sync configuration.
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` — optional; enable outbound SMS for SOS notifications (the backend builds phone and WhatsApp links and can send SMS when configured).

Notes:
- Admin import/sync supports Google Places and OSM Overpass; Geoapify can be used as an alternative provider by adjusting the admin sync configuration.
- If you enable Twilio, confirm provider credentials in `backend/.env` and be mindful of usage costs for live SMS during testing.

## Offline / Resilience

- The frontend implements a short (3s) timeout for the live `/api/nearby` call; on slow networks the client falls back silently to a cached nearby result (if available) to avoid blocking the UI.
- SOS submissions performed while offline are queued locally and automatically retried when connectivity is restored. This behavior is handled by `frontend/src/utils/offlineCache.js`.

## Seeding & Demo reset

- To seed demo places (deterministic Mumbai demo dataset):

```bash
python backend/scripts/seed_mumbai_places.py
# or
make seed
```

- To reset demo state (clear demo SOS logs, reset sessions, reseed demo places):

```bash
# GET /api/demo/reset
# Example (from repo root):
curl -X GET "http://localhost:8000/api/demo/reset"
```

## Feedback reports & migrations

- The feedback flow persists reports to the `feedback_reports` table. An Alembic migration was added: run `alembic upgrade head` before relying on the feedback endpoint in an existing database.

```bash
cd backend
alembic upgrade head
```

## Run locally (backend + frontend)

1. Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. Frontend (in a separate shell):

```bash
cd frontend
npm install
npm run dev
# Open the app in your browser, add ?demo=true for demo mode
```

## Docker / Compose

- A development Dockerfile exists for the backend at `backend/Dockerfile` and the frontend has a `frontend/Dockerfile` and an Nginx config for static serving. Use the provided `docker-compose.yml` for local multi-container demos.

## Where to look next / Admin ideas

- The repository now stores `feedback_reports` and basic demo tooling; a small admin UI to review reported feedback and triage CAP alerts would be a natural next step. If you want, I can scaffold an admin review page or an exports endpoint to pull feedback into a Google Sheet.

