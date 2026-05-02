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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

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
