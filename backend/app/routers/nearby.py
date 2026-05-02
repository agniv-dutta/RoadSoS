from __future__ import annotations

from typing import Final

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Place
from ..schemas import Center, NearbyResponse, PlaceResponse
from ..utils.haversine import bounding_box, haversine

router = APIRouter()
ALLOWED_PLACE_TYPES: Final[set[str]] = {
    "hospital",
    "police",
    "ambulance",
    "towing",
    "fuel",
    "trauma_center",
    "fire_station",
}


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
        last_synced=place.last_synced,
        created_at=place.created_at,
        distance_km=distance_km,
    )


@router.get("/nearby", response_model=NearbyResponse)
async def get_nearby_places(
    lat: float,
    lng: float,
    radius_km: float = Query(default=10.0, ge=0.1, le=50.0),
    type: str = Query(default="all", alias="type"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> NearbyResponse:
    """Return nearby cached places ordered by precise distance."""

    if type != "all" and type not in ALLOWED_PLACE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid place type: {type}")

    min_lat, max_lat, min_lng, max_lng = bounding_box(lat, lng, radius_km)
    statement = select(Place).where(Place.latitude.between(min_lat, max_lat))

    if min_lng <= max_lng:
        statement = statement.where(Place.longitude.between(min_lng, max_lng))
    else:
        statement = statement.where(or_(Place.longitude >= min_lng, Place.longitude <= max_lng))

    if type != "all":
        statement = statement.where(Place.place_type == type)

    statement = statement.order_by(Place.name.asc())
    result = await db.execute(statement)
    candidates = result.scalars().all()

    matched: list[tuple[float, Place]] = []
    for place in candidates:
        distance_km = haversine(lat, lng, place.latitude, place.longitude)
        if distance_km <= radius_km:
            matched.append((distance_km, place))

    matched.sort(key=lambda item: item[0])
    limited_results = matched[:limit]

    return NearbyResponse(
        results=[_place_to_response(place, distance_km=distance_km) for distance_km, place in limited_results],
        count=len(limited_results),
        center=Center(lat=lat, lng=lng),
        radius_km=radius_km,
        cached=True,
    )
