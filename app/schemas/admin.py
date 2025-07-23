from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DriverApprovalRequest(BaseModel):
    approved: bool
    reason: Optional[str] = Field(None, max_length=500)

class DriverApprovalResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone: str
    driving_license: Optional[str]
    vehicle_number: Optional[str]
    vehicle_type: Optional[str]
    created_at: datetime
    status: str

class UserBanRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)

class RideAnalytics(BaseModel):
    total_rides: int
    completed_rides: int
    cancelled_rides: int
    total_revenue: float
    start_date: datetime
    end_date: datetime

class AdminDashboard(BaseModel):
    total_users: int
    total_drivers: int
    pending_driver_approvals: int
    pending_kyc_applications: int
    pending_kyc_documents: int
    total_rides: int
    completed_rides_today: int
    revenue_today: float

class UserManagementResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    status: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

class SystemSettings(BaseModel):
    base_fare: float
    distance_rate: float
    time_rate: float
    surge_multiplier: float
    max_wait_time: int
    cancellation_fee: float 