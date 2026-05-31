from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import os

from ..config import get_settings
from ..database import AsyncSessionLocal, ping_db, get_db
from ..models import Place, SOSLog
from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Return the service and database health status, including telemetry stats."""

    try:
        # lightweight check: count places
        result = await db.execute(select(func.count(Place.id)))
        place_count = result.scalar()
        db_status = "connected"
    except Exception as e:
        place_count = 0
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="ok",
        db=db_status,
        version="1.0.0",
        places_in_db=place_count,
        model="xlm-roberta-interim",
        timestamp=datetime.utcnow().isoformat(),
        environment=os.getenv("RENDER", "local"),
    )
