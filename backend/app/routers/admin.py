from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
from typing import Final

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..models import Place
from ..schemas import AdminSyncRequest, AdminSyncResponse
from ..services.geohash import encode
from ..services.places import ExternalPlace, fetch_google_places, fetch_osm_places
from ..utils.haversine import bounding_box, haversine

router = APIRouter()
MATCH_DISTANCE_KM: Final[float] = 0.2


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


async def _load_existing_places(db: AsyncSession, latitude: float, longitude: float, radius_km: float) -> list[Place]:
    min_lat, max_lat, min_lng, max_lng = bounding_box(latitude, longitude, radius_km)
    statement = select(Place).where(Place.latitude.between(min_lat, max_lat))
    if min_lng <= max_lng:
        statement = statement.where(Place.longitude.between(min_lng, max_lng))
    else:
        statement = statement.where(or_(Place.longitude >= min_lng, Place.longitude <= max_lng))
    result = await db.execute(statement)
    return list(result.scalars().all())


def _find_match(existing_places: list[Place], candidate: ExternalPlace) -> Place | None:
    best_match: Place | None = None
    best_distance: float | None = None
    normalized_candidate_name = _normalize_name(candidate.name)

    for place in existing_places:
        if place.place_type != candidate.place_type:
            continue
        if _normalize_name(place.name) != normalized_candidate_name:
            continue

        distance_km = haversine(candidate.latitude, candidate.longitude, place.latitude, place.longitude)
        if distance_km > MATCH_DISTANCE_KM:
            continue
        if best_distance is None or distance_km < best_distance:
            best_match = place
            best_distance = distance_km

    return best_match


async def _upsert_places(db: AsyncSession, existing_places: list[Place], candidates: list[ExternalPlace]) -> tuple[int, int]:
    inserted = 0
    updated = 0
    now = datetime.now(timezone.utc)

    for candidate in candidates:
        matched_place = _find_match(existing_places, candidate)
        geohash5 = encode(candidate.latitude, candidate.longitude, precision=5)

        if matched_place is None:
            place = Place(
                name=candidate.name,
                place_type=candidate.place_type,
                latitude=candidate.latitude,
                longitude=candidate.longitude,
                phone=candidate.phone,
                address=candidate.address,
                is_verified=False,
                geohash5=geohash5,
                source=candidate.source,
                last_synced=now,
                created_at=now,
            )
            db.add(place)
            existing_places.append(place)
            inserted += 1
            continue

        matched_place.name = candidate.name
        matched_place.place_type = candidate.place_type
        matched_place.latitude = candidate.latitude
        matched_place.longitude = candidate.longitude
        matched_place.phone = candidate.phone
        matched_place.address = candidate.address
        matched_place.geohash5 = geohash5
        matched_place.source = candidate.source
        matched_place.last_synced = now
        updated += 1

    return inserted, updated


@router.post("/admin/sync", response_model=AdminSyncResponse)
async def sync_places(
    payload: AdminSyncRequest,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
) -> AdminSyncResponse:
    """Synchronize cached roadside assistance places from external providers."""

    settings = get_settings()
    if x_admin_key != settings.admin_secret_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin key")

    source_tasks = [
        fetch_google_places(payload.lat, payload.lng, payload.radius_km),
        fetch_osm_places(payload.lat, payload.lng, payload.radius_km),
    ]
    google_places, osm_places = await asyncio.gather(*source_tasks, return_exceptions=True)

    failed = 0
    combined_places: list[ExternalPlace] = []
    source_counts = Counter()

    if isinstance(google_places, Exception):
        failed += 1
    else:
        combined_places.extend(google_places)
        source_counts["google_places"] = len(google_places)

    if isinstance(osm_places, Exception):
        failed += 1
    else:
        combined_places.extend(osm_places)
        source_counts["osm"] = len(osm_places)

    existing_places = await _load_existing_places(db, payload.lat, payload.lng, payload.radius_km)
    inserted, updated = await _upsert_places(db, existing_places, combined_places)
    await db.commit()

    return AdminSyncResponse(
        inserted=inserted,
        updated=updated,
        failed=failed,
        sources=dict(source_counts),
    )
