from fastapi import APIRouter
from .schemas import TriageRequest
from .utils import standard_response

router = APIRouter()


@router.post("/triage")
async def assess_triage(request: TriageRequest):
    priority = "high" if request.severity and request.severity >= 7 else "medium"
    return standard_response(
        "Triage assessment completed",
        {
            "incident_id": request.incident_id,
            "triage_priority": priority,
            "recommendation": "Dispatch emergency crew" if priority == "high" else "Monitor and advise transport",
        },
    )
