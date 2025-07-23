from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base
from enum import Enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DRIVER = "driver"
    USER = "user"

class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    firebase_uid = Column(String, unique=True, nullable=True)
    
    # Personal Information
    first_name = Column(String)
    last_name = Column(String)
    profile_picture = Column(String, nullable=True)
    
    # Role and Status
    role = Column(String, default=UserRole.USER.value)
    status = Column(String, default=UserStatus.PENDING.value)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Driver Specific Fields
    driving_license = Column(String, nullable=True)
    vehicle_number = Column(String, nullable=True)
    vehicle_type = Column(String, nullable=True)
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    is_available = Column(Boolean, default=False)
    
    # KYC Documents
    aadhar_card = Column(String, nullable=True)
    vehicle_registration = Column(String, nullable=True)
    insurance_document = Column(String, nullable=True)
    
    # Wallet
    wallet_balance = Column(Float, default=0.0)
    
    # OTP Fields
    otp = Column(String, nullable=True)
    otp_valid_until = Column(Integer, nullable=True)
    otp_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships can be added here for rides, reviews, etc.
    # rides_as_driver = relationship("Ride", back_populates="driver")
    # rides_as_passenger = relationship("Ride", back_populates="passenger")
    
    # KYC Relationships
    from app.models.kyc import KYCDocument, KYCApplication
    kyc_documents = relationship(
        "KYCDocument",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="KYCDocument.user_id"
    )
    kyc_applications = relationship(
        "KYCApplication",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="KYCApplication.user_id"
    )
