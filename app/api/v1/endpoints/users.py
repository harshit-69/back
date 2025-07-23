from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
import os
import shutil
from datetime import datetime

from app.database import get_db
from app.schemas.user import UserUpdate, DriverUpdate, UserOut
from app.models.user import User, UserRole, UserStatus
from app.utils.auth import get_current_user
from app.core.config import settings

router = APIRouter()

@router.put("/profile", response_model=UserOut)
async def update_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile information."""
    # Update user fields
    update_data = user_data.dict(exclude_unset=True)
    
    if update_data:
        stmt = (
            update(User)
            .where(User.id == current_user.id)
            .values(**update_data, updated_at=datetime.utcnow())
        )
        await db.execute(stmt)
        await db.commit()
        
        # Refresh user data
        result = await db.execute(select(User).where(User.id == current_user.id))
        updated_user = result.scalars().first()
        return UserOut.from_orm(updated_user)
    
    return UserOut.from_orm(current_user)

@router.put("/driver-profile", response_model=UserOut)
async def update_driver_profile(
    driver_data: DriverUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update driver-specific profile information."""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can update driver profile"
        )
    
    # Update driver fields
    update_data = driver_data.dict(exclude_unset=True)
    
    if update_data:
        stmt = (
            update(User)
            .where(User.id == current_user.id)
            .values(**update_data, updated_at=datetime.utcnow())
        )
        await db.execute(stmt)
        await db.commit()
        
        # Refresh user data
        result = await db.execute(select(User).where(User.id == current_user.id))
        updated_user = result.scalars().first()
        return UserOut.from_orm(updated_user)
    
    return UserOut.from_orm(current_user)

@router.post("/upload-document")
async def upload_document(
    document_type: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload driver documents (Aadhar, License, etc.)."""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can upload documents"
        )
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG, PNG, and PDF are allowed."
        )
    
    # Validate file size
    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size too large. Maximum size is {settings.MAX_FILE_SIZE} bytes."
        )
    
    # Create upload directory if it doesn't exist
    upload_dir = os.path.join(settings.UPLOAD_FOLDER, "documents", str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{document_type}_{timestamp}{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update user document field based on type
    document_field = None
    if document_type == "driving_license":
        document_field = "driving_license"
    elif document_type == "aadhar":
        document_field = "aadhar_card"
    elif document_type == "vehicle_registration":
        document_field = "vehicle_registration"
    
    if document_field:
        stmt = (
            update(User)
            .where(User.id == current_user.id)
            .values(**{document_field: file_path}, updated_at=datetime.utcnow())
        )
        await db.execute(stmt)
        await db.commit()
    
    return {
        "message": "Document uploaded successfully",
        "document_type": document_type,
        "file_path": file_path
    }

@router.get("/driver-kyc-status")
async def get_driver_kyc_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get driver KYC verification status."""
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can check KYC status"
        )
    
    return {
        "user_id": current_user.id,
        "status": current_user.status,
        "is_verified": current_user.is_verified,
        "documents": {
            "driving_license": current_user.driving_license is not None,
            "vehicle_number": current_user.vehicle_number is not None,
            "vehicle_type": current_user.vehicle_type is not None
        }
    }

@router.get("/profile", response_model=UserOut)
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile."""
    return UserOut.from_orm(current_user) 