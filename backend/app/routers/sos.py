from __future__ import annotations

from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Place, SOSLog, compute_data_confidence
from ..schemas import PlaceResponse, SOSRequest, SOSResponse
from ..services.sms import send_sms
from ..utils.haversine import haversine

router = APIRouter()


def _place_to_response(place: Place, distance_km: float | None = None) -> PlaceResponse:
    return PlaceResponse(
        id=place.id,
        name=place.name,
        place_type=place.place_type,
        latitude=place.latitude,
        longitude=place.longitude,
        phone=place.phone,
        address=place.address,
        is_verified=place.is_verified,
        geohash5=place.geohash5,
        source=place.source,
        data_confidence=compute_data_confidence(
            is_verified=place.is_verified,
            source=place.source,
            last_synced=place.last_synced,
        ),
        last_synced=place.last_synced,
        created_at=place.created_at,
        distance_km=distance_km,
    )


async def _find_nearest_hospital(db: AsyncSession, latitude: float, longitude: float) -> tuple[Place | None, float | None]:
    statement = select(Place).where(Place.place_type == "hospital")
    result = await db.execute(statement)
    hospitals = result.scalars().all()

    nearest_place: Place | None = None
    nearest_distance: float | None = None

    for place in hospitals:
        distance_km = haversine(latitude, longitude, place.latitude, place.longitude)
        if nearest_distance is None or distance_km < nearest_distance:
            nearest_place = place
            nearest_distance = distance_km

    return nearest_place, nearest_distance


@router.post("/sos", response_model=SOSResponse)
async def create_sos(request: SOSRequest, http_request: Request, db: AsyncSession = Depends(get_db)) -> SOSResponse:
    """Log an SOS event, find the nearest hospital, and optionally send SMS."""

    nearest_hospital, distance_km = await _find_nearest_hospital(db, request.latitude, request.longitude)
    user_agent = http_request.headers.get("user-agent")

    log_entry = SOSLog(
        latitude=request.latitude,
        longitude=request.longitude,
        user_agent=user_agent,
        sms_sent=False,
        whatsapp_sent=False,
        nearest_hospital_id=nearest_hospital.id if nearest_hospital else None,
    )
    db.add(log_entry)
    await db.flush()

    google_maps_link = f"https://www.google.com/maps/search/?api=1&query={request.latitude},{request.longitude}"
    whatsapp_message = "Emergency assistance requested. "
    if nearest_hospital is not None:
        google_maps_link = f"https://www.google.com/maps/search/?api=1&query={nearest_hospital.latitude},{nearest_hospital.longitude}"
        whatsapp_message = (
            f"Emergency! Nearest hospital: {nearest_hospital.name}. "
            f"Maps: {google_maps_link}."
        )
    whatsapp_link = f"https://wa.me/?text={quote_plus(whatsapp_message)}"

    sms_sent = False
    if request.phone and nearest_hospital is not None:
        sms_body = (
            f"RoadSoS emergency alert. Nearest hospital: {nearest_hospital.name}. "
            f"Maps: {google_maps_link}"
        )
        sms_sent = await send_sms(request.phone, sms_body)

    log_entry.sms_sent = sms_sent
    log_entry.whatsapp_sent = False
    await db.commit()
    await db.refresh(log_entry)

    nearest_hospital_response = None
    if nearest_hospital is not None:
        nearest_hospital_response = _place_to_response(nearest_hospital, distance_km=distance_km)

    return SOSResponse(
        sos_id=log_entry.id,
        nearest_hospital=nearest_hospital_response,
        google_maps_link=google_maps_link,
        whatsapp_link=whatsapp_link,
        sms_sent=sms_sent,
    )
