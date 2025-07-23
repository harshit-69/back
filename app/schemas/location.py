from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class LocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    accuracy: Optional[float] = Field(None, ge=0, description="Location accuracy in meters")
    heading: Optional[float] = Field(None, ge=0, le=360, description="Direction heading in degrees")
    speed: Optional[float] = Field(None, ge=0, description="Speed in meters per second")

class LocationResponse(BaseModel):
    user_id: int
    latitude: float
    longitude: float
    accuracy: Optional[float]
    heading: Optional[float]
    speed: Optional[float]
    timestamp: datetime

class NearbyDriverResponse(BaseModel):
    driver_id: int
    name: str
    vehicle_type: Optional[str]
    vehicle_number: Optional[str]
    latitude: float
    longitude: float
    distance: float
    rating: float
    is_available: bool

class FrequentLocation(BaseModel):
    id: int
    user_id: int
    name: str
    latitude: float
    longitude: float
    address: str
    created_at: datetime

class FrequentLocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str = Field(..., min_length=1, max_length=500)

class GeocodingResponse(BaseModel):
    address: str
    formatted_address: str
    components: dict
    coordinates: dict 