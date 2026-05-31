from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import FeedbackReport, Place
from ..schemas import FeedbackRequest, FeedbackResponse

router = APIRouter()


@router.post('/feedback', response_model=FeedbackResponse)
async def submit_feedback(payload: FeedbackRequest, db: AsyncSession = Depends(get_db)) -> FeedbackResponse:
    """Store data-quality feedback for triage and place records."""

    if payload.place_id is not None:
                result = await db.execute(select(Place).where(Place.id == payload.place_id))
                place = result.scalar_one_or_none()
                if place is None:
                        raise HTTPException(status_code=404, detail='Place not found')

    report = FeedbackReport(
        place_id=payload.place_id,
        issue=payload.issue.strip(),
        correct_value=(payload.correct_value or '').strip() or None,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return FeedbackResponse(
        id=report.id,
        message='Thank you — reviewed within 24h.',
        review_eta='24h',
    )
