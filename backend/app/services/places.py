from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from ..config import get_settings
from ..utils.haversine import bounding_box

logger = logging.getLogger(__name__)

GOOGLE_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
GOOGLE_REQUEST_TYPES = ("hospital", "police", "fire_station", "gas_station")
GOOGLE_TO_INTERNAL_TYPE = {
    "hospital": "hospital",
    "police": "police",
    "fire_station": "fire_station",
    "gas_station": "fuel",
}
OSM_TYPE_MAP = {
    ("amenity", "hospital"): "hospital",
    ("amenity", "police"): "police",
    ("amenity", "fuel"): "fuel",
    ("emergency", "ambulance_station"): "ambulance",
}


@dataclass(slots=True)
class ExternalPlace:
    """Normalized place payload returned by external providers."""

    name: str
    place_type: str
    latitude: float
    longitude: float
    phone: str | None = None
    address: str | None = None
    source: str = "manual"
    raw: dict[str, Any] | None = None


async def fetch_google_places(latitude: float, longitude: float, radius_km: float) -> list[ExternalPlace]:
    """Fetch nearby places from the Google Places API."""

    settings = get_settings()
    if not settings.google_places_api_key:
        logger.warning("GOOGLE_PLACES_API_KEY is not configured; skipping Google Places sync")
        return []

    radius_meters = int(radius_km * 1000)
    collected: list[ExternalPlace] = []

    async with httpx.AsyncClient(timeout=25.0) as client:
        for request_type in GOOGLE_REQUEST_TYPES:
            collected.extend(
                await _fetch_google_places_for_type(client, settings.google_places_api_key, latitude, longitude, radius_meters, request_type)
            )

    return collected


async def _fetch_google_places_for_type(
    client: httpx.AsyncClient,
    api_key: str,
    latitude: float,
    longitude: float,
    radius_meters: int,
    request_type: str,
) -> list[ExternalPlace]:
    results: list[ExternalPlace] = []
    page_token: str | None = None

    for _ in range(3):
        params: dict[str, Any] = {
            "key": api_key,
            "location": f"{latitude},{longitude}",
            "radius": radius_meters,
            "type": request_type,
        }
        if page_token:
            params["pagetoken"] = page_token

        response = await client.get(GOOGLE_NEARBY_URL, params=params)
        response.raise_for_status()
        payload = response.json()

        if payload.get("status") not in {"OK", "ZERO_RESULTS"}:
            logger.warning("Google Places returned status %s for type %s", payload.get("status"), request_type)

        for item in payload.get("results", []):
            place = _normalize_google_result(item, request_type)
            if place is not None:
                results.append(place)

        page_token = payload.get("next_page_token")
        if not page_token:
            break

        await asyncio.sleep(2.0)

    return results


def _normalize_google_result(item: dict[str, Any], request_type: str) -> ExternalPlace | None:
    geometry = item.get("geometry", {}).get("location", {})
    latitude = geometry.get("lat")
    longitude = geometry.get("lng")
    name = item.get("name")

    if latitude is None or longitude is None or not name:
        return None

    internal_type = GOOGLE_TO_INTERNAL_TYPE.get(request_type, request_type)
    address = item.get("vicinity") or item.get("formatted_address")

    return ExternalPlace(
        name=name,
        place_type=internal_type,
        latitude=float(latitude),
        longitude=float(longitude),
        phone=None,
        address=address,
        source="google_places",
        raw=item,
    )


async def fetch_osm_places(latitude: float, longitude: float, radius_km: float) -> list[ExternalPlace]:
    """Fetch nearby places from the OpenStreetMap Overpass API."""

    min_lat, max_lat, min_lng, max_lng = bounding_box(latitude, longitude, radius_km)
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="hospital"]({min_lat},{min_lng},{max_lat},{max_lng});
      way["amenity"="hospital"]({min_lat},{min_lng},{max_lat},{max_lng});
      node["amenity"="police"]({min_lat},{min_lng},{max_lat},{max_lng});
      way["amenity"="police"]({min_lat},{min_lng},{max_lat},{max_lng});
      node["amenity"="fuel"]({min_lat},{min_lng},{max_lat},{max_lng});
      way["amenity"="fuel"]({min_lat},{min_lng},{max_lat},{max_lng});
      node["emergency"="ambulance_station"]({min_lat},{min_lng},{max_lat},{max_lng});
      way["emergency"="ambulance_station"]({min_lat},{min_lng},{max_lat},{max_lng});
    );
    out center tags;
    """

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(OVERPASS_URL, data={"data": query})
        response.raise_for_status()
        payload = response.json()

    results: list[ExternalPlace] = []
    for element in payload.get("elements", []):
        normalized = _normalize_osm_element(element)
        if normalized is not None:
            results.append(normalized)

    return results


def _normalize_osm_element(element: dict[str, Any]) -> ExternalPlace | None:
    tags = element.get("tags", {})
    place_type = None
    for tag_key, tag_value in OSM_TYPE_MAP:
        if tags.get(tag_key) == tag_value:
            place_type = OSM_TYPE_MAP[(tag_key, tag_value)]
            break

    if place_type is None:
        return None

    name = tags.get("name") or tags.get("brand") or tags.get("operator")
    if not name:
        return None

    if element.get("type") == "node":
        latitude = element.get("lat")
        longitude = element.get("lon")
    else:
        center = element.get("center", {})
        latitude = center.get("lat")
        longitude = center.get("lon")

    if latitude is None or longitude is None:
        return None

    phone = tags.get("contact:phone") or tags.get("phone")
    address = _build_address(tags)

    return ExternalPlace(
        name=name,
        place_type=place_type,
        latitude=float(latitude),
        longitude=float(longitude),
        phone=phone,
        address=address,
        source="osm",
        raw=element,
    )


def _build_address(tags: dict[str, Any]) -> str | None:
    parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:city"),
        tags.get("addr:state"),
        tags.get("addr:postcode"),
    ]
    values = [part for part in parts if part]
    if values:
        return ", ".join(values)
    return tags.get("addr:full")
