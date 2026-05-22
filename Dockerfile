# ─── RoadSoS — PS #9 Backend ──────────────────────────────────────────────────
# Multi-stage build: keeps final image lean (~1.8 GB with torch CPU wheels)
# Build: docker build -t roadsos . && docker run -p 8000:8000 roadsos
# ──────────────────────────────────────────────────────────────────────────────

# Stage 1 — dependency builder
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps needed to compile some Python wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .

# Install into a prefix so we can copy cleanly to final stage
RUN pip install --upgrade pip \
    && pip install --prefix=/install --no-cache-dir -r requirements.txt

# Download spaCy English model (small — 12 MB)
RUN /install/bin/python -m spacy download en_core_web_sm --target /install/lib/python3.11/site-packages


# Stage 2 — runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY backend/ .

# Pre-download the zero-shot model weights at build time
# so the container starts instantly (no cold download on first request)
RUN python - <<'EOF'
from transformers import pipeline
pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
print("Model cached.")
EOF

# Non-root user for security
RUN useradd --create-home --shell /bin/bash roadsos
USER roadsos

EXPOSE 8000

# Alembic migration + server startup
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
