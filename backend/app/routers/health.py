from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from ..config import get_settings
from ..database import AsyncSessionLocal, ping_db
from ..models import Place, SOSLog
from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return the service and database health status, including telemetry stats."""

    try:
        await ping_db()
    except Exception as exc:  # pragma: no cover - defensive route guard
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    settings = get_settings()

    # Collect extended stats for Telemetry panel
    places_count: int | None = None
    sos_today: int | None = None
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(func.count()).select_from(Place))
            places_count = result.scalar_one()

            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            sos_result = await db.execute(
                select(func.count())
                .select_from(SOSLog)
                .where(SOSLog.created_at >= today_start)
            )
            sos_today = sos_result.scalar_one()
    except Exception:  # pragma: no cover - non-critical stats
        pass

    return HealthResponse(
        status="ok",
        db="connected",
        version=settings.version,
        places_count=places_count,
        sos_today=sos_today,
        nlu_model="XLM-RoBERTa (interim) · BART fallback active",
    )
