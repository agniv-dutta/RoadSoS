from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Center(BaseModel):
    """Center point for search responses."""

    lat: float
    lng: float


class PlaceResponse(BaseModel):
    """API response representation of a place."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    place_type: str
    latitude: float
    longitude: float
    phone: str | None = None
    address: str | None = None
    is_verified: bool
    geohash5: str
    source: str
    data_confidence: float = Field(ge=0.0, le=1.0)
    last_synced: datetime
    created_at: datetime
    distance_km: float | None = None


class NearbyResponse(BaseModel):
    """Nearby places search response."""

    results: list[PlaceResponse]
    count: int
    center: Center
    radius_km: float
    cached: bool


class SOSRequest(BaseModel):
    """Incoming SOS request payload."""

    latitude: float
    longitude: float
    phone: str | None = None


class SOSResponse(BaseModel):
    """SOS endpoint response payload."""

    sos_id: int
    nearest_hospital: PlaceResponse | None
    google_maps_link: str
    whatsapp_link: str
    sms_sent: bool


class AdminSyncRequest(BaseModel):
    """Admin sync request payload."""

    lat: float
    lng: float
    radius_km: float = Field(default=20.0, gt=0, le=50.0)


class AdminSyncResponse(BaseModel):
    """Admin sync summary payload."""

    inserted: int
    updated: int
    failed: int
    sources: dict[str, int]


class HealthResponse(BaseModel):
    """Health check response payload."""
    status: str
    db: str
    version: str
    # Extended stats for Telemetry panel
    places_in_db: int | None = None
    model: str | None = None
    timestamp: str | None = None
    environment: str | None = None


class FeedbackRequest(BaseModel):
    """Feedback submission for incorrect place information."""

    place_id: int | None = None
    issue: str = Field(min_length=3, max_length=512)
    correct_value: str | None = Field(default=None, max_length=512)


class FeedbackResponse(BaseModel):
    """Acknowledgement payload for submitted feedback."""

    id: int
    message: str
    review_eta: str
