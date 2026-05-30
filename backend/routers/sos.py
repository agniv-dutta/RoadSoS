from fastapi import APIRouter
from .schemas import SOSRequest
from .utils import standard_response

router = APIRouter()


@router.post("/sos")
async def send_sos_alert(request: SOSRequest):
    return standard_response(
        "SOS alert received",
        {
            "alert_id": "sos-1234",
            "assigned_team": "Ambulance Unit 7",
            "location": request.location.dict(),
        },
    )
