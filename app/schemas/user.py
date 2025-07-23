from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Annotated
from datetime import datetime
from app.models.user import UserRole, UserStatus

class UserInToken(BaseModel):
    id: int
    email: str
    role: str  # Always expect string role
    
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr
    phone: str = Field(pattern=r'^\+?1?\d{9,15}$')
    first_name: str = Field(min_length=2, max_length=50)
    last_name: str = Field(min_length=2, max_length=50)

class UserCreate(UserBase):
    password: str = Field(min_length=8)
    confirm_password: str

    @field_validator('confirm_password')
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None

class DriverUpdate(BaseModel):
    driving_license: Optional[str] = None
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    is_available: Optional[bool] = None
    current_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    current_longitude: Optional[float] = Field(default=None, ge=-180, le=180)

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

class OTPLogin(BaseModel):
    email: EmailStr
    otp: str

class UserOut(UserBase):
    id: int
    role: UserRole
    status: UserStatus
    is_active: bool
    is_verified: bool
    profile_picture: Optional[str] = None
    wallet_balance: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    otp_verified: Optional[bool] = None

    class Config:
        from_attributes = True  # Required for SQLAlchemy model conversion

class DriverOut(UserOut):
    driving_license: Optional[str] = None
    vehicle_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    is_available: bool
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInToken

class TokenData(BaseModel):
    email: str
    role: Optional[UserRole] = None