from fastapi import APIRouter, Query
from .schemas import Location
from .utils import mock_service_list, standard_response

router = APIRouter()


@router.get("/nearby")
async def get_nearby_services(
    service_type: str = Query("hospital", description="Type of nearby service"),
    latitude: float = Query(..., description="Current latitude"),
    longitude: float = Query(..., description="Current longitude"),
):
    results = mock_service_list(service_type, {"latitude": latitude, "longitude": longitude})
    return standard_response("Nearby services retrieved", {"services": results})
