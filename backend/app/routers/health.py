from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..config import get_settings
from ..database import ping_db
from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return the service and database health status."""

    try:
        await ping_db()
    except Exception as exc:  # pragma: no cover - defensive route guard
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    settings = get_settings()
    return HealthResponse(status="ok", db="connected", version=settings.version)
