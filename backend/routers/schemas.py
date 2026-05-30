from pydantic import BaseModel
from typing import List, Optional

class Location(BaseModel):
    latitude: float
    longitude: float

class NearbyQuery(BaseModel):
    service_type: Optional[str] = None
    radius_km: Optional[float] = 5.0
    location: Location

class SOSRequest(BaseModel):
    user_id: str
    location: Location
    emergency_type: str
    description: Optional[str] = None

class TriageRequest(BaseModel):
    incident_id: str
    symptoms: List[str]
    severity: Optional[int] = None

class ReportRequest(BaseModel):
    reporter_id: str
    location: Location
    incident_type: str
    details: Optional[str] = None

class StandardResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None
