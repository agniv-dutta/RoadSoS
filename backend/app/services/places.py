from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from ..config import get_settings
from ..utils.haversine import bounding_box

logger = logging.getLogger(__name__)

GEOAPIFY_BASE = "https://api.geoapify.com/v2/places"
GEOAPIFY_CATEGORY_MAP = {
    "hospital": "healthcare.hospital",
    "police": "service.police",
    "ambulance": "healthcare.emergency",
    "fuel": "service.fuel",
    "towing": "service.vehicle.breakdown",
    "fire_station": "service.fire_brigade",
}
OSM_TYPE_MAP = {
    ("amenity", "hospital"): "hospital",
    ("amenity", "police"): "police",
    ("amenity", "fuel"): "fuel",
    ("emergency", "ambulance_station"): "ambulance",
}
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


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


async def fetch_geoapify_places(lat: float, lng: float, radius_m: int, place_type: str) -> list[ExternalPlace]:
    settings = get_settings()
    if not settings.geoapify_api_key:
        logger.warning("GEOAPIFY_API_KEY is not configured; skipping Geoapify sync")
        return []

    category = GEOAPIFY_CATEGORY_MAP.get(place_type, "healthcare.hospital")
    params = {
        "categories": category,
        "filter": f"circle:{lng},{lat},{radius_m}",
        "bias": f"proximity:{lng},{lat}",
        "limit": 20,
        "apiKey": settings.geoapify_api_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(GEOAPIFY_BASE, params=params)
        response.raise_for_status()
        data = response.json()

    results: list[ExternalPlace] = []
    for feature in data.get("features", []):
        properties = feature.get("properties", {})
        coordinates = feature.get("geometry", {}).get("coordinates", [None, None])
        longitude = coordinates[0] if len(coordinates) > 0 else None
        latitude = coordinates[1] if len(coordinates) > 1 else None
        if latitude is None or longitude is None:
            continue

        contact = properties.get("contact") or {}
        results.append(
            ExternalPlace(
                name=properties.get("name") or "Unknown",
                place_type=place_type,
                latitude=float(latitude),
                longitude=float(longitude),
                phone=contact.get("phone") or properties.get("phone"),
                address=properties.get("formatted"),
                source="geoapify",
                raw=feature,
            )
        )

    return results


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
