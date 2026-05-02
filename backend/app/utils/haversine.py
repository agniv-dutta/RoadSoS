from __future__ import annotations

from math import asin, cos, degrees, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the great-circle distance between two points in kilometers."""

    lat1_rad = radians(lat1)
    lng1_rad = radians(lng1)
    lat2_rad = radians(lat2)
    lng2_rad = radians(lng2)

    delta_lat = lat2_rad - lat1_rad
    delta_lng = lng2_rad - lng1_rad

    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(min(1.0, sqrt(a)))


def bounding_box(lat: float, lng: float, radius_km: float) -> tuple[float, float, float, float]:
    """Return a latitude/longitude bounding box for the given radius."""

    angular_distance = radius_km / EARTH_RADIUS_KM
    lat_rad = radians(lat)
    min_lat = max(-90.0, lat - degrees(angular_distance))
    max_lat = min(90.0, lat + degrees(angular_distance))

    if abs(cos(lat_rad)) < 1e-12:
        min_lng = -180.0
        max_lng = 180.0
    else:
        delta_lng = degrees(asin(min(1.0, sin(angular_distance) / abs(cos(lat_rad)))))
        min_lng = max(-180.0, lng - delta_lng)
        max_lng = min(180.0, lng + delta_lng)

    return min_lat, max_lat, min_lng, max_lng
