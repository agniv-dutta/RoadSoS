FROM python:3.11-slim

# Install system deps for building wheels when needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend sources
COPY . /app

# Create venv
RUN python -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# Install pip requirements (use cached wheelhouse when available)
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt || true

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
