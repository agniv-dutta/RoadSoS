from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import delete

from app.database import AsyncSessionLocal
from app.dialogue.session_store import SessionStore
from app.models import SOSLog
from app.services.demo_seed import seed_demo_places

router = APIRouter(prefix='/demo', tags=['demo'])


@router.get('/reset')
async def demo_reset(request: Request):
    """Reset demo state between live runs without restarting the API."""

    async with AsyncSessionLocal() as db:
        deleted = await db.execute(delete(SOSLog))
        await db.commit()

        seeded = await seed_demo_places(db)

    # Reset dialogue sessions so triage state is clean for next demo.
    request.app.state.session_store = SessionStore()

    return {
        'ok': True,
        'sos_logs_cleared': deleted.rowcount or 0,
        'demo_places_seeded': seeded,
        'message': 'Demo reset complete',
    }
