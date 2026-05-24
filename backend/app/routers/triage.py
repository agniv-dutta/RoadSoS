"""
POST /api/triage  — Core PS #9 endpoint.

Accepts a raw emergency message string.
Returns a structured CAP v1.2 JSON incident report
with extracted slots, triage level, and follow-up question.
"""

import uuid
from datetime import datetime, timezone
from time import perf_counter

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.nlu.pipeline import run_nlu_pipeline
from app.nlu.cap_exporter import CAPv12Exporter
from app.nlu.latency_benchmark import run_latency_benchmark
from app.dialogue.state_machine import TriageStateMachine
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
    runtime_mode:     str | None = None
    follow_up:        str | None
    missing_slots:    list[str]
    info:             CAPInfo
    cap_alert:        dict | None = None
    cap_validation_errors: list[str] | None = None
    session_id:        str | None = None
    turn:              int | None = None
    follow_up_question: str | None = None
    session_state:     str | None = None


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

    resp = TriageResponse(
        identifier    = str(uuid.uuid4()),
        sender        = "roadsos-nlu-v1",
        sent          = datetime.now(timezone.utc).isoformat(),
        status        = "Actual",
        msg_type      = "Alert",
        scope         = "Public",
        triage_level  = triage_level.value,
        intent        = intent,
        confidence    = nlu["confidence"],
        runtime_mode  = nlu.get("runtime_mode"),
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

    # Build and validate CAP v1.2 JSON
    exporter = CAPv12Exporter()
    try:
        cap_alert = exporter.build_alert({
            "intent": nlu.get("intent"),
            "triage": nlu.get("triage_level") or nlu.get("triage"),
            "confidence": nlu.get("confidence"),
            "slots": nlu.get("slots"),
            "language": nlu.get("language"),
            "raw_text": nlu.get("raw_text") or message,
        }, sender=resp.sender, source_message=message)
        valid, errors = exporter.validate_cap(cap_alert)
        if valid:
            resp.cap_alert = cap_alert
            resp.cap_validation_errors = None
        else:
            resp.cap_alert = None
            resp.cap_validation_errors = errors
    except Exception as e:
        resp.cap_alert = None
        resp.cap_validation_errors = [str(e)]

    return resp


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

    # Backwards-compatible single-turn endpoint: route through state machine with a generated session
    from app.dialogue.session_store import SessionStore
    from app.dialogue.state_machine import TriageStateMachine
    # use internal ephemeral session
    session_id = str(uuid.uuid4())
    store = SessionStore()
    sm = TriageStateMachine(store)
    result = sm.process_turn(session_id=session_id, message=req.message, language_hint=None)
    # Build triage response from NLU and attach session info
    triage_resp = _build_cap_response(req.message, nlu_result)
    triage_resp.cap_alert = result.get("cap_alert")
    triage_resp.cap_validation_errors = result.get("cap_validation_errors")
    # expose session id and turn info in headers? for backward compat we include in body
    out = triage_resp.model_dump()
    out["session_id"] = result.get("session_id")
    out["turn"] = 1
    out["follow_up_question"] = result.get("follow_up_question")
    out["session_state"] = result.get("state")
    out["runtime_mode"] = nlu_result.get("runtime_mode")
    return out


@router.get("/triage/health", summary="NLU pipeline health check")
async def triage_health():
    """Warmup check — loads the classifier if not already loaded."""
    from app.nlu.pipeline import load_classifier
    try:
        engine = load_classifier()
        return {"status": "ok", "model": "onnx_int8" if getattr(engine, "available", False) else "fallback"}
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


@router.get("/triage/latency", summary="Run the latency benchmark and return a JSON report")
async def triage_latency(sample_count: int = 200):
    if sample_count < 1 or sample_count > 1000:
        raise HTTPException(status_code=400, detail="sample_count must be between 1 and 1000")
    try:
        return run_latency_benchmark(sample_count=sample_count)
    except AssertionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class ParseMessageRequest(BaseModel):
    text: str
    session_id: str | None = None
    language_hint: str | None = None


@router.post("/triage/parse-message", summary="Session-aware parse message for dialogue slot collection")
async def parse_message(req: ParseMessageRequest, response: Response):
    started = perf_counter()
    # session management via app.state.session_store
    from fastapi import Request
    # create or fetch session store from app state
    # we can't access app here directly; import via global settings: use singleton in main
    try:
        from app.main import app as _app
        store = _app.state.session_store
    except Exception:
        # fallback ephemeral store
        from app.dialogue.session_store import SessionStore
        store = SessionStore()

    sm = TriageStateMachine(store)

    session_id = req.session_id or str(uuid.uuid4())
    result = sm.process_turn(session_id=session_id, message=req.text, language_hint=req.language_hint)
    response.headers["X-Latency-Ms"] = f"{(perf_counter() - started) * 1000.0:.2f}"
    return result
