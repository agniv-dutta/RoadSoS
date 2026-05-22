"""
POST /api/triage  — Core PS #9 endpoint.

Accepts a raw emergency message string.
Returns a structured CAP v1.2 JSON incident report
with extracted slots, triage level, and follow-up question.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.nlu.pipeline import run_nlu_pipeline
from app.nlu.slots import (
    TRIAGE_TO_CAP_SEVERITY,
    TRIAGE_TO_CAP_URGENCY,
    TriageLevel,
)

router = APIRouter(prefix="/api", tags=["triage"])


# ─── Request / Response Models ─────────────────────────────────────────────────

class TriageRequest(BaseModel):
    message:     str  = Field(..., min_length=1, max_length=1000,
                               example="accident hua 3 log phanse hain petrol leak jaldi aao")
    session_id:  str  = Field(default="", description="Optional multi-turn session ID")


class SlotPayload(BaseModel):
    casualties:       int | None
    entrapment:       bool
    hazard_type:      str
    child_involved:   bool
    location_mention: str | None


class CAPInfo(BaseModel):
    """CAP v1.2 <info> block — https://docs.oasis-open.org/emergency/cap/v1.2/"""
    category:    str
    event:       str
    urgency:     str
    severity:    str
    certainty:   str
    description: str
    slots:       SlotPayload


class TriageResponse(BaseModel):
    """Full CAP v1.2 envelope."""
    identifier:       str
    sender:           str
    sent:             str
    status:           str
    msg_type:         str
    scope:            str
    triage_level:     str
    intent:           str
    confidence:       float
    follow_up:        str | None
    missing_slots:    list[str]
    info:             CAPInfo


# ─── Helper ────────────────────────────────────────────────────────────────────

_INTENT_TO_CAP_EVENT = {
    "emergency_crash":    "Road Traffic Accident",
    "fire_hazard":        "Vehicle Fire / Fuel Hazard",
    "medical_emergency":  "Medical Emergency — Road Incident",
    "vehicle_assistance": "Vehicle Breakdown",
    "general_help":       "General Distress Call",
    "unknown":            "Unclassified Emergency",
}


def _build_cap_response(message: str, nlu: dict) -> TriageResponse:
    triage_level = TriageLevel(nlu["triage_level"])
    intent       = nlu["intent"]

    return TriageResponse(
        identifier    = str(uuid.uuid4()),
        sender        = "roadsos-nlu-v1",
        sent          = datetime.now(timezone.utc).isoformat(),
        status        = "Actual",
        msg_type      = "Alert",
        scope         = "Public",
        triage_level  = triage_level.value,
        intent        = intent,
        confidence    = nlu["confidence"],
        follow_up     = nlu["follow_up_question"],
        missing_slots = nlu["missing_slots"],
        info          = CAPInfo(
            category    = "Transport",
            event       = _INTENT_TO_CAP_EVENT.get(intent, "Unknown"),
            urgency     = TRIAGE_TO_CAP_URGENCY[triage_level],
            severity    = TRIAGE_TO_CAP_SEVERITY[triage_level],
            certainty   = "Observed",
            description = message,
            slots       = SlotPayload(**nlu["slots"]),
        ),
    )


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/triage", response_model=TriageResponse, summary="Parse emergency message → CAP v1.2 triage report")
async def triage_message(req: TriageRequest):
    """
    Core PS #9 endpoint.

    - Classifies emergency intent (zero-shot, no GPU needed)
    - Extracts critical slots: casualties, entrapment, hazard, child, location
    - Assigns IAED triage priority: P1 / P2 / P3
    - Returns a CAP v1.2 structured incident report
    - Provides the most critical missing-slot follow-up question for multi-turn dialogue
    """
    try:
        nlu_result = run_nlu_pipeline(req.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NLU pipeline error: {str(e)}")

    return _build_cap_response(req.message, nlu_result)


@router.get("/triage/health", summary="NLU pipeline health check")
async def triage_health():
    """Warmup check — loads the classifier if not already loaded."""
    from app.nlu.pipeline import load_classifier
    try:
        load_classifier()
        return {"status": "ok", "model": "facebook/bart-large-mnli"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/triage/batch", summary="Batch evaluate multiple messages (for benchmarking)")
async def triage_batch(messages: list[str]):
    """
    Run NLU on a list of messages.
    Used by judges to batch-test the 50-message evaluation set.
    Returns list of CAP v1.2 responses.
    """
    if len(messages) > 100:
        raise HTTPException(status_code=400, detail="Batch limit is 100 messages.")
    results = []
    for msg in messages:
        try:
            nlu = run_nlu_pipeline(msg)
            results.append(_build_cap_response(msg, nlu).model_dump())
        except Exception as e:
            results.append({"error": str(e), "message": msg})
    return results
