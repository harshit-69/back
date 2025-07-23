from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.models.ride import Ride, RideStatus
from app.utils.auth import get_current_user, check_admin_access
from app.schemas.admin import (
    DriverApprovalRequest, DriverApprovalResponse, 
    UserBanRequest, RideAnalytics, AdminDashboard
)
from app.models.kyc import KYCApplication, KYCDocument, KYCStatus

router = APIRouter()

@router.get("/dashboard", response_model=AdminDashboard)
async def get_admin_dashboard(
    current_user: User = Depends(check_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard statistics."""
    # Get total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()
    
    # Get total drivers
    total_drivers_result = await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.DRIVER)
    )
    total_drivers = total_drivers_result.scalar()
    
    # Get pending driver approvals
    pending_drivers_result = await db.execute(
        select(func.count(User.id)).where(
            and_(User.role == UserRole.DRIVER, User.status == UserStatus.PENDING)
        )
    )
    pending_drivers = pending_drivers_result.scalar()
    
    # Get total rides
    total_rides_result = await db.execute(select(func.count(Ride.id)))
    total_rides = total_rides_result.scalar()
    
    # Get completed rides today
    today = datetime.utcnow().date()
    completed_rides_today_result = await db.execute(
        select(func.count(Ride.id)).where(
            and_(
                Ride.status == RideStatus.completed,
                func.date(Ride.completed_at) == today
            )
        )
    )
    completed_rides_today = completed_rides_today_result.scalar()
    
    # Get total revenue today
    revenue_today_result = await db.execute(
        select(func.sum(Ride.total_fare)).where(
            and_(
                Ride.status == RideStatus.completed,
                func.date(Ride.completed_at) == today
            )
        )
    )
    revenue_today = revenue_today_result.scalar() or 0
    
    # Get pending KYC applications
    pending_kyc_result = await db.execute(
        select(func.count(KYCApplication.id)).where(KYCApplication.status == KYCStatus.PENDING.value)
    )
    pending_kyc = pending_kyc_result.scalar()
    
    # Get pending KYC documents
    pending_docs_result = await db.execute(
        select(func.count(KYCDocument.id)).where(KYCDocument.status == KYCStatus.PENDING.value)
    )
    pending_docs = pending_docs_result.scalar()
    
    return AdminDashboard(
        total_users=total_users,
        total_drivers=total_drivers,
        pending_driver_approvals=pending_drivers,
        pending_kyc_applications=pending_kyc,
        pending_kyc_documents=pending_docs,
        total_rides=total_rides,
        completed_rides_today=completed_rides_today,
        revenue_today=revenue_today
    )

@router.get("/drivers/pending")
async def get_pending_drivers(
    current_user: User = Depends(check_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Get list of drivers pending approval."""
    query = select(User).where(
        and_(User.role == UserRole.DRIVER, User.status == UserStatus.PENDING)
    ).order_by(User.created_at.desc())
    
    result = await db.execute(query)
    drivers = result.scalars().all()
    
    return [
        DriverApprovalResponse(
            id=driver.id,
            email=driver.email,
            first_name=driver.first_name,
            last_name=driver.last_name,
            phone=driver.phone,
            driving_license=driver.driving_license,
            vehicle_number=driver.vehicle_number,
            vehicle_type=driver.vehicle_type,
            created_at=driver.created_at,
            status=driver.status
        ) for driver in drivers
    ]

@router.post("/drivers/{driver_id}/approve")
async def approve_driver(
    driver_id: int,
    approval_data: DriverApprovalRequest,
    current_user: User = Depends(check_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject a driver."""
    # Get driver
    result = await db.execute(select(User).where(User.id == driver_id))
    driver = result.scalars().first()
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    if driver.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a driver"
        )
    
    if driver.status != UserStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver is not pending approval"
        )
    
    # Update driver status
    new_status = UserStatus.ACTIVE if approval_data.approved else UserStatus.SUSPENDED
    stmt = (
        update(User)
        .where(User.id == driver_id)
        .values(
            status=new_status,
            is_verified=approval_data.approved,
            updated_at=datetime.utcnow()
        )
    )
    await db.execute(stmt)
    await db.commit()
    
    return {
        "message": f"Driver {'approved' if approval_data.approved else 'rejected'} successfully",
        "driver_id": driver_id,
        "status": new_status,
        "reason": approval_data.reason
    }

@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: int,
    ban_data: UserBanRequest,
    current_user: User = Depends(check_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Ban a user."""
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot ban yourself"
        )
    
    # Update user status
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(
            status=UserStatus.SUSPENDED,
            is_active=False,
            updated_at=datetime.utcnow()
        )
    )
    await db.execute(stmt)
    await db.commit()
    
    return {
        "message": "User banned successfully",
        "user_id": user_id,
        "reason": ban_data.reason
    }

@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: int,
    current_user: User = Depends(check_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Unban a user."""
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user status
    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(
            status=UserStatus.ACTIVE,
            is_active=True,
            updated_at=datetime.utcnow()
        )
    )
    await db.execute(stmt)
    await db.commit()
    
    return {
        "message": "User unbanned successfully",
        "user_id": user_id
    }

@router.get("/analytics/rides")
async def get_ride_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(check_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Get ride analytics."""
    # Parse dates
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_dt = datetime.utcnow() - timedelta(days=30)
    
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_dt = datetime.utcnow()
    
    # Get ride statistics
    total_rides_result = await db.execute(
        select(func.count(Ride.id)).where(
            and_(
                Ride.requested_at >= start_dt,
                Ride.requested_at <= end_dt
            )
        )
    )
    total_rides = total_rides_result.scalar()
    
    completed_rides_result = await db.execute(
        select(func.count(Ride.id)).where(
            and_(
                Ride.status == RideStatus.completed,
                Ride.requested_at >= start_dt,
                Ride.requested_at <= end_dt
            )
        )
    )
    completed_rides = completed_rides_result.scalar()
    
    cancelled_rides_result = await db.execute(
        select(func.count(Ride.id)).where(
            and_(
                Ride.status == RideStatus.cancelled,
                Ride.requested_at >= start_dt,
                Ride.requested_at <= end_dt
            )
        )
    )
    cancelled_rides = cancelled_rides_result.scalar()
    
    total_revenue_result = await db.execute(
        select(func.sum(Ride.total_fare)).where(
            and_(
                Ride.status == RideStatus.completed,
                Ride.requested_at >= start_dt,
                Ride.requested_at <= end_dt
            )
        )
    )
    total_revenue = total_revenue_result.scalar() or 0
    
    return RideAnalytics(
        total_rides=total_rides,
        completed_rides=completed_rides,
        cancelled_rides=cancelled_rides,
        total_revenue=total_revenue,
        start_date=start_dt,
        end_date=end_dt
    )

@router.post("/rides/{ride_id}/assign")
async def manually_assign_ride(
    ride_id: int,
    driver_id: int,
    current_user: User = Depends(check_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Manually assign a ride to a driver."""
    # Get ride
    ride_result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = ride_result.scalars().first()
    
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ride not found"
        )
    
    if ride.status != RideStatus.REQUESTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ride is not in requested status"
        )
    
    # Get driver
    driver_result = await db.execute(select(User).where(User.id == driver_id))
    driver = driver_result.scalars().first()
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    if driver.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a driver"
        )
    
    if not driver.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver is not available"
        )
    
    # Update ride
    stmt = (
        update(Ride)
        .where(Ride.id == ride_id)
        .values(
            driver_id=driver_id,
            status=RideStatus.ACCEPTED,
            accepted_at=datetime.utcnow()
        )
    )
    await db.execute(stmt)
    
    # Update driver availability
    driver_stmt = (
        update(User)
        .where(User.id == driver_id)
        .values(is_available=False)
    )
    await db.execute(driver_stmt)
    
    await db.commit()
    
    return {
        "message": "Ride assigned successfully",
        "ride_id": ride_id,
        "driver_id": driver_id
    } 