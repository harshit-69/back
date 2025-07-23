from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Location details
    name = Column(String)  # Custom name or address
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Type of location
    is_home = Column(Boolean, default=False)
    is_work = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    
    # Metadata
    visit_count = Column(Integer, default=1)
    last_visited = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    user = relationship("User", backref="locations")

class DriverLocation(Base):
    __tablename__ = "driver_locations"

    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"))
    
    # Location details
    latitude = Column(Float)
    longitude = Column(Float)
    heading = Column(Float)  # Direction in degrees
    speed = Column(Float)  # Speed in km/h
    
    # Status
    is_online = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    driver = relationship("User", backref="current_location")