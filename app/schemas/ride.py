from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.ride import RideStatus

class RideRequest(BaseModel):
    pickup_location: str = Field(..., min_length=1, max_length=500)
    pickup_latitude: float = Field(..., ge=-90, le=90)
    pickup_longitude: float = Field(..., ge=-180, le=180)
    dropoff_location: str = Field(..., min_length=1, max_length=500)
    dropoff_latitude: float = Field(..., ge=-90, le=90)
    dropoff_longitude: float = Field(..., ge=-180, le=180)
    payment_method: str = Field(..., description="cash, card, wallet")

class OfferRideRequest(BaseModel):
    pickup_location: str = Field(..., min_length=1, max_length=500)
    pickup_latitude: float = Field(..., ge=-90, le=90)
    pickup_longitude: float = Field(..., ge=-180, le=180)
    dropoff_location: str = Field(..., min_length=1, max_length=500)
    dropoff_latitude: float = Field(..., ge=-90, le=90)
    dropoff_longitude: float = Field(..., ge=-180, le=180)
    payment_method: str = Field(..., description="cash, card, wallet")

class OfferRideResponse(BaseModel):
    ride_id: int
    driver_id: int
    pickup_location: str
    dropoff_location: str
    estimated_distance: float
    estimated_duration: int
    total_fare: float
    status: str
    message: str

class RideResponse(BaseModel):
    id: int
    rider_id: Optional[int] = None
    driver_id: Optional[int]
    pickup_location: str
    pickup_latitude: float
    pickup_longitude: float
    dropoff_location: str
    dropoff_latitude: float
    dropoff_longitude: float
    status: RideStatus
    estimated_distance: float
    estimated_duration: int
    actual_distance: Optional[float]
    actual_duration: Optional[int]
    base_fare: float
    distance_fare: float
    time_fare: float
    surge_multiplier: float
    total_fare: float
    promo_code: Optional[str]
    discount_amount: float
    payment_method: str
    payment_status: bool
    requested_at: datetime
    accepted_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    cancelled_at: Optional[datetime]

    class Config:
        from_attributes = True

class RideStatusUpdate(BaseModel):
    status: RideStatus
    reason: Optional[str] = None

class RideCancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)

class DriverAcceptRequest(BaseModel):
    estimated_arrival_time: Optional[int] = Field(None, ge=1, description="Estimated arrival time in minutes")

class FareEstimate(BaseModel):
    estimated_distance: float
    estimated_duration: int
    base_fare: float
    distance_fare: float
    time_fare: float
    surge_multiplier: float = 1.0
    total_fare: float

class RideHistoryResponse(BaseModel):
    rides: List[RideResponse]
    total_count: int
    page: int
    size: int

class RideStatistics(BaseModel):
    total_rides: int
    completed_rides: int
    cancelled_rides: int
    total_earnings: float
    average_rating: float