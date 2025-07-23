from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class RideStatus(str, enum.Enum):
    requested = "requested"
    offered = "offered"
    accepted = "accepted"
    completed = "completed"
    cancelled = "cancelled"

class Ride(Base):
    __tablename__ = "rides"

    id = Column(Integer, primary_key=True, index=True)
    rider_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Location details
    pickup_location = Column(String)
    pickup_latitude = Column(Float)
    pickup_longitude = Column(Float)
    dropoff_location = Column(String)
    dropoff_latitude = Column(Float)
    dropoff_longitude = Column(Float)
    
    # Ride details
    status = Column(Enum(RideStatus, name="ridestatus", create_type=False), nullable=False)
    estimated_distance = Column(Float)  # in kilometers
    estimated_duration = Column(Integer)  # in minutes
    actual_distance = Column(Float, nullable=True)
    actual_duration = Column(Integer, nullable=True)
    
    # Pricing
    base_fare = Column(Float)
    distance_fare = Column(Float)
    time_fare = Column(Float)
    surge_multiplier = Column(Float, default=1.0)
    total_fare = Column(Float)
    
    # Promo code
    promo_code = Column(String, nullable=True)
    discount_amount = Column(Float, default=0.0)
    
    # Payment
    payment_method = Column(String)  # cash, card, wallet
    payment_status = Column(Boolean, default=False)
    
    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    offered_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    rider = relationship("User", foreign_keys=[rider_id])
    driver = relationship("User", foreign_keys=[driver_id])