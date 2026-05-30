from fastapi import APIRouter
from .schemas import ReportRequest
from .utils import standard_response

router = APIRouter()


@router.post("/report")
async def submit_report(request: ReportRequest):
    return standard_response(
        "Incident reported successfully",
        {
            "report_id": "report-5678",
            "incident_type": request.incident_type,
            "reported_at": "2026-05-30T00:00:00Z",
        },
    )
