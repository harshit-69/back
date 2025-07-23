from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import List, Optional
from datetime import datetime
import math

from app.database import get_db
from app.models.user import User, UserRole
from app.utils.auth import get_current_user
from app.schemas.location import LocationUpdate, LocationResponse, NearbyDriverResponse

router = APIRouter()

@router.post("/update-location")
async def update_location(
    location_data: LocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user's current location."""
    if current_user.role == UserRole.DRIVER:
        # Update driver location
        stmt = (
            update(User)
            .where(User.id == current_user.id)
            .values(
                current_latitude=location_data.latitude,
                current_longitude=location_data.longitude,
                updated_at=datetime.utcnow()
            )
        )
        await db.execute(stmt)
        await db.commit()
        
        return {
            "message": "Location updated successfully",
            "user_id": current_user.id,
            "latitude": location_data.latitude,
            "longitude": location_data.longitude,
            "timestamp": datetime.utcnow()
        }
    else:
        # For regular users, store in location history
        # This would typically go to a separate location_history table
        return {
            "message": "Location tracked for user",
            "user_id": current_user.id,
            "latitude": location_data.latitude,
            "longitude": location_data.longitude,
            "timestamp": datetime.utcnow()
        }

@router.get("/nearby-drivers")
async def get_nearby_drivers(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: float = Query(5000, description="Search radius in meters"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Find nearby available drivers."""
    # Calculate bounding box for efficient querying
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    
    # Approximate radius of Earth in meters
    earth_radius = 6371000
    
    # Calculate bounding box
    lat_delta = radius / earth_radius
    lon_delta = radius / (earth_radius * math.cos(lat_rad))
    
    min_lat = latitude - math.degrees(lat_delta)
    max_lat = latitude + math.degrees(lat_delta)
    min_lon = longitude - math.degrees(lon_delta)
    max_lon = longitude + math.degrees(lon_delta)
    
    # Query for nearby available drivers
    query = select(User).where(
        User.role == UserRole.DRIVER,
        User.is_available == True,
        User.is_active == True,
        User.status == "active",
        User.current_latitude.isnot(None),
        User.current_longitude.isnot(None),
        User.current_latitude >= min_lat,
        User.current_latitude <= max_lat,
        User.current_longitude >= min_lon,
        User.current_longitude <= max_lon
    )
    
    result = await db.execute(query)
    drivers = result.scalars().all()
    
    # Calculate exact distances and filter by radius
    nearby_drivers = []
    for driver in drivers:
        distance = calculate_distance(
            latitude, longitude,
            driver.current_latitude, driver.current_longitude
        )
        
        if distance <= radius:
            nearby_drivers.append({
                "driver_id": driver.id,
                "name": f"{driver.first_name} {driver.last_name}",
                "vehicle_type": driver.vehicle_type,
                "vehicle_number": driver.vehicle_number,
                "latitude": driver.current_latitude,
                "longitude": driver.current_longitude,
                "distance": round(distance, 2),
                "rating": 4.5  # This would come from a ratings table
            })
    
    # Sort by distance
    nearby_drivers.sort(key=lambda x: x["distance"])
    
    return {
        "drivers": nearby_drivers,
        "total_count": len(nearby_drivers),
        "search_center": {"latitude": latitude, "longitude": longitude},
        "radius": radius
    }

@router.post("/frequent-locations")
async def save_frequent_location(
    name: str,
    latitude: float,
    longitude: float,
    address: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save a frequently used location."""
    # This would typically go to a separate frequent_locations table
    # For now, we'll return a success message
    return {
        "message": "Frequent location saved",
        "location": {
            "name": name,
            "latitude": latitude,
            "longitude": longitude,
            "address": address,
            "user_id": current_user.id
        }
    }

@router.get("/frequent-locations")
async def get_frequent_locations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's frequent locations."""
    # This would query a frequent_locations table
    # For now, return empty list
    return {
        "locations": [],
        "user_id": current_user.id
    }

@router.get("/reverse-geocode")
async def reverse_geocode(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180)
):
    """Convert coordinates to human-readable address."""
    # This would integrate with Google Maps Geocoding API
    # For now, return a mock response
    return {
        "address": "Sample Address",
        "formatted_address": "123 Sample Street, City, State, Country",
        "components": {
            "street_number": "123",
            "route": "Sample Street",
            "locality": "City",
            "administrative_area_level_1": "State",
            "country": "Country"
        },
        "coordinates": {
            "latitude": latitude,
            "longitude": longitude
        }
    }

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
    R = 6371000  # Earth's radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c 