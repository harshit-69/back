from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.orm import joinedload
from typing import List, Optional
from datetime import datetime
import math

from app.database import get_db
from app.models.user import User, UserRole
from app.models.ride import Ride, RideStatus
from app.utils.auth import get_current_user
from app.schemas.ride import (
    RideRequest, RideResponse, RideStatusUpdate, 
    RideCancelRequest, FareEstimate, DriverAcceptRequest,
    OfferRideRequest, OfferRideResponse
)

router = APIRouter()

# Move /available-offers endpoint to the top
@router.get("/available-offers")
async def get_available_ride_offers(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: float = Query(5000, description="Search radius in meters"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available ride offers from drivers."""
    # Calculate bounding box for efficient querying
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    earth_radius = 6371000
    lat_delta = radius / earth_radius
    lon_delta = radius / (earth_radius * math.cos(lat_rad))
    min_lat = latitude - math.degrees(lat_delta)
    max_lat = latitude + math.degrees(lat_delta)
    min_lon = longitude - math.degrees(lon_delta)
    max_lon = longitude + math.degrees(lon_delta)

    # Query for available ride offers with driver details using a JOIN
    query = (
        select(Ride)
        .options(joinedload(Ride.driver))
        .where(
            Ride.status == RideStatus.offered,
            Ride.pickup_latitude >= min_lat,
            Ride.pickup_latitude <= max_lat,
            Ride.pickup_longitude >= min_lon,
            Ride.pickup_longitude <= max_lon
        )
    )
    result = await db.execute(query)
    offers = result.scalars().all()

    # Calculate exact distances and filter by radius
    available_offers = []
    for offer in offers:
        distance = calculate_distance(
            latitude, longitude,
            offer.pickup_latitude, offer.pickup_longitude
        )
        if distance <= radius and offer.driver:
            driver = offer.driver
            available_offers.append({
                "ride_id": int(offer.id),
                "driver_id": offer.driver_id,
                "driver_name": f"{driver.first_name} {driver.last_name}",
                "vehicle_type": driver.vehicle_type,
                "vehicle_number": driver.vehicle_number,
                "pickup_location": offer.pickup_location,
                "dropoff_location": offer.dropoff_location,
                "pickup_latitude": offer.pickup_latitude,
                "pickup_longitude": offer.pickup_longitude,
                "dropoff_latitude": offer.dropoff_latitude,
                "dropoff_longitude": offer.dropoff_longitude,
                "estimated_distance": offer.estimated_distance,
                "estimated_duration": offer.estimated_duration,
                "total_fare": offer.total_fare,
                "distance_from_user": round(distance, 2),
                "offered_at": offer.offered_at.isoformat() if offer.offered_at else None
            })

    # Sort by distance from user
    available_offers.sort(key=lambda x: x["distance_from_user"])
    
    # Apply pagination
    paginated_offers = available_offers[skip : skip + limit]

    return {
        "offers": paginated_offers,
        "total_count": len(available_offers),
        "skip": skip,
        "limit": limit,
        "search_center": {"latitude": latitude, "longitude": longitude},
        "radius": radius
    }

@router.post("/request", response_model=RideResponse)
async def request_ride(
    ride_data: RideRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Request a new ride."""
    if current_user.role == UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Drivers cannot request rides"
        )
    
    # Calculate estimated distance and duration
    distance = calculate_distance(
        ride_data.pickup_latitude, ride_data.pickup_longitude,
        ride_data.dropoff_latitude, ride_data.dropoff_longitude
    )
    
    # Estimate duration (assuming average speed of 30 km/h)
    estimated_duration = int((distance / 1000) * 2)  # minutes
    
    # Calculate fare
    base_fare = 50  # Base fare in INR
    distance_fare = distance * 0.15  # 15 paise per meter
    time_fare = estimated_duration * 1  # 1 rupee per minute
    total_fare = base_fare + distance_fare + time_fare
    
    # Create ride record
    db_ride = Ride(
        rider_id=current_user.id,
        pickup_location=ride_data.pickup_location,
        pickup_latitude=ride_data.pickup_latitude,
        pickup_longitude=ride_data.pickup_longitude,
        dropoff_location=ride_data.dropoff_location,
        dropoff_latitude=ride_data.dropoff_latitude,
        dropoff_longitude=ride_data.dropoff_longitude,
        estimated_distance=distance,
        estimated_duration=estimated_duration,
        base_fare=base_fare,
        distance_fare=distance_fare,
        time_fare=time_fare,
        total_fare=total_fare,
        payment_method=ride_data.payment_method,
        status=RideStatus.requested
    )
    
    db.add(db_ride)
    await db.commit()
    await db.refresh(db_ride)
    
    return RideResponse.from_orm(db_ride)

@router.get("/nearby-drivers")
async def get_nearby_drivers_for_ride(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: float = Query(5000, description="Search radius in meters"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Find nearby available drivers for ride request."""
    # Calculate bounding box for efficient querying
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    
    earth_radius = 6371000
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
    
    # Apply pagination
    paginated_drivers = nearby_drivers[skip : skip + limit]
    
    return {
        "drivers": paginated_drivers,
        "total_count": len(nearby_drivers),
        "skip": skip,
        "limit": limit,
        "search_center": {"latitude": latitude, "longitude": longitude},
        "radius": radius
    }

@router.post("/{ride_id}/accept")
async def accept_ride(
    ride_id: int,
    accept_data: DriverAcceptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Driver accepts a ride request."""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can accept rides"
        )
    
    # Get ride
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalars().first()
    
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride not found"
        )
    
    if ride.status != RideStatus.requested:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ride is not in requested status"
        )
    
    # Update ride
    stmt = (
        update(Ride)
        .where(Ride.id == ride_id)
        .values(
            driver_id=current_user.id,
            status=RideStatus.accepted,
            accepted_at=datetime.utcnow()
        )
    )
    await db.execute(stmt)
    
    # Update driver availability
    driver_stmt = (
        update(User)
        .where(User.id == current_user.id)
        .values(is_available=False)
    )
    await db.execute(driver_stmt)
    
    await db.commit()
    
    return {
        "message": "Ride accepted successfully",
        "ride_id": ride_id,
        "driver_id": current_user.id
    }

@router.post("/{ride_id}/start")
async def start_ride(
    ride_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a ride (driver picks up passenger)."""
    # Get ride
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalars().first()
    
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride not found"
        )
    
    if ride.status != RideStatus.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ride is not in accepted status"
        )
    
    # Update ride status
    stmt = (
        update(Ride)
        .where(Ride.id == ride_id)
        .values(
            status=RideStatus.started,
            started_at=datetime.utcnow()
        )
    )
    await db.execute(stmt)
    await db.commit()
    
    return {
        "message": "Ride started successfully",
        "ride_id": ride_id
    }

@router.post("/{ride_id}/complete")
async def complete_ride(
    ride_id: int,
    actual_distance: Optional[float] = None,
    actual_duration: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Complete a ride."""
    # Get ride
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalars().first()
    
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride not found"
        )
    
    if ride.status != RideStatus.started:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ride is not in started status"
        )
    
    # Update ride
    update_data = {
        "status": RideStatus.completed,
        "completed_at": datetime.utcnow()
    }
    
    if actual_distance:
        update_data["actual_distance"] = actual_distance
    if actual_duration:
        update_data["actual_duration"] = actual_duration
    
    stmt = (
        update(Ride)
        .where(Ride.id == ride_id)
        .values(**update_data)
    )
    await db.execute(stmt)
    
    # Make driver available again
    driver_stmt = (
        update(User)
        .where(User.id == ride.driver_id)
        .values(is_available=True)
    )
    await db.execute(driver_stmt)
    
    await db.commit()
    
    return {
        "message": "Ride completed successfully",
        "ride_id": ride_id
    }

@router.post("/{ride_id}/cancel")
async def cancel_ride(
    ride_id: int,
    cancel_data: RideCancelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a ride."""
    # Get ride
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalars().first()
    
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride not found"
        )
    
    # Check if user can cancel this ride
    if current_user.id != ride.rider_id and current_user.id != ride.driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own rides"
        )
    
    if ride.status in [RideStatus.completed, RideStatus.cancelled]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ride cannot be cancelled"
        )
    
    # Update ride
    stmt = (
        update(Ride)
        .where(Ride.id == ride_id)
        .values(
            status=RideStatus.cancelled,
            cancelled_at=datetime.utcnow()
        )
    )
    await db.execute(stmt)
    
    # Make driver available again if ride was accepted
    if ride.driver_id and ride.status == RideStatus.accepted:
        driver_stmt = (
            update(User)
            .where(User.id == ride.driver_id)
            .values(is_available=True)
        )
        await db.execute(driver_stmt)
    
    await db.commit()
    
    return {
        "message": "Ride cancelled successfully",
        "ride_id": ride_id,
        "reason": cancel_data.reason
    }

@router.get("/estimate-fare")
async def estimate_fare(
    pickup_latitude: float = Query(..., ge=-90, le=90),
    pickup_longitude: float = Query(..., ge=-180, le=180),
    dropoff_latitude: float = Query(..., ge=-90, le=90),
    dropoff_longitude: float = Query(..., ge=-180, le=180),
    current_user: User = Depends(get_current_user)
):
    """Estimate fare for a ride."""
    # Calculate distance
    distance = calculate_distance(
        pickup_latitude, pickup_longitude,
        dropoff_latitude, dropoff_longitude
    )
    
    # Estimate duration
    estimated_duration = int((distance / 1000) * 2)  # minutes
    
    # Calculate fare
    base_fare = 50
    distance_fare = distance * 0.15
    time_fare = estimated_duration * 1
    total_fare = base_fare + distance_fare + time_fare
    
    return FareEstimate(
        estimated_distance=distance,
        estimated_duration=estimated_duration,
        base_fare=base_fare,
        distance_fare=distance_fare,
        time_fare=time_fare,
        total_fare=total_fare
    )

@router.get("/my-rides")
async def get_my_rides(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's ride history."""
    query = select(Ride).where(
        (Ride.rider_id == current_user.id) | (Ride.driver_id == current_user.id)
    )
    
    if status:
        query = query.where(Ride.status == status)
    
    query = query.order_by(Ride.requested_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    rides = result.scalars().all()
    
    return [RideResponse.from_orm(ride) for ride in rides]

@router.get("/{ride_id}", response_model=RideResponse)
async def get_ride_details(
    ride_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific ride."""
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalars().first()
    
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride not found"
        )
    
    # Check if user has access to this ride
    if current_user.id != ride.rider_id and current_user.id != ride.driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return RideResponse.from_orm(ride)

@router.post("/offer", response_model=OfferRideResponse)
async def offer_ride(
    offer_data: OfferRideRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Driver offers a ride to nearby riders."""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can offer rides"
        )
    
    if not current_user.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver is not available"
        )
    
    # Calculate estimated distance and duration
    distance = calculate_distance(
        offer_data.pickup_latitude, offer_data.pickup_longitude,
        offer_data.dropoff_latitude, offer_data.dropoff_longitude
    )
    
    # Estimate duration (assuming average speed of 30 km/h)
    estimated_duration = int((distance / 1000) * 2)  # minutes
    
    # Calculate fare
    base_fare = 50  # Base fare in INR
    distance_fare = distance * 0.15  # 15 paise per meter
    time_fare = estimated_duration * 1  # 1 rupee per minute
    total_fare = base_fare + distance_fare + time_fare
    
    # Create ride offer record
    db_ride = Ride(
        driver_id=current_user.id,
        pickup_location=offer_data.pickup_location,
        pickup_latitude=offer_data.pickup_latitude,
        pickup_longitude=offer_data.pickup_longitude,
        dropoff_location=offer_data.dropoff_location,
        dropoff_latitude=offer_data.dropoff_latitude,
        dropoff_longitude=offer_data.dropoff_longitude,
        estimated_distance=distance,
        estimated_duration=estimated_duration,
        base_fare=base_fare,
        distance_fare=distance_fare,
        time_fare=time_fare,
        total_fare=total_fare,
        payment_method=offer_data.payment_method,
        status=RideStatus.offered,
        offered_at=datetime.utcnow()
    )
    
    db.add(db_ride)
    await db.commit()
    await db.refresh(db_ride)
    
    # Update driver availability
    stmt = (
        update(User)
        .where(User.id == current_user.id)
        .values(is_available=False)
    )
    await db.execute(stmt)
    await db.commit()
    
    return OfferRideResponse(
        ride_id=db_ride.id,
        driver_id=current_user.id,
        pickup_location=offer_data.pickup_location,
        dropoff_location=offer_data.dropoff_location,
        estimated_distance=distance,
        estimated_duration=estimated_duration,
        total_fare=total_fare,
        status="offered",
        message="Ride offer created successfully"
    )

@router.post("/{ride_id}/accept-offer")
async def accept_ride_offer(
    ride_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rider accepts a ride offer from driver."""
    if current_user.role == UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Drivers cannot accept ride offers"
        )
    
    # Get ride offer
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalars().first()
    
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride offer not found"
        )
    
    if ride.status != RideStatus.offered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ride is not in offered status"
        )
    
    # Update ride
    stmt = (
        update(Ride)
        .where(Ride.id == ride_id)
        .values(
            rider_id=current_user.id,
            status=RideStatus.accepted,
            accepted_at=datetime.utcnow()
        )
    )
    await db.execute(stmt)
    await db.commit()
    
    return {
        "message": "Ride offer accepted successfully",
        "ride_id": ride_id,
        "rider_id": current_user.id,
        "driver_id": ride.driver_id
    }

@router.post("/{ride_id}/cancel-offer")
async def cancel_ride_offer(
    ride_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a ride offer (driver can cancel before rider accepts)."""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can cancel ride offers"
        )

    # Get ride offer
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalars().first()
    
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride offer not found"
        )
    
    if ride.status != RideStatus.offered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ride is not in offered status"
        )
    
    # Only the driver who created the offer can cancel it
    if current_user.id != ride.driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own offers"
        )
    
    # Update ride
    stmt = (
        update(Ride)
        .where(Ride.id == ride_id)
        .values(
            status=RideStatus.cancelled,
            cancelled_at=datetime.utcnow()
        )
    )
    await db.execute(stmt)
    
    # Make driver available again
    driver_stmt = (
        update(User)
        .where(User.id == current_user.id)
        .values(is_available=True)
    )
    await db.execute(driver_stmt)
    
    await db.commit()
    
    return {
        "message": "Ride offer cancelled successfully",
        "ride_id": ride_id
    }

@router.post("/drivers/set-available")
async def set_driver_available(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Only drivers can set availability.")
    stmt = (
        update(User)
        .where(User.id == current_user.id)
        .values(is_available=True)
    )
    await db.execute(stmt)
    await db.commit()
    return {"message": "Driver is now available."}

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