import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from typing import List, Optional
from datetime import datetime
import aiofiles

from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.models.kyc import KYCDocument, KYCApplication, KYCStatus, DocumentType
from app.utils.auth import get_current_user, check_admin_access
from app.schemas.kyc import (
    KYCDocumentResponse, KYCApplicationCreate, KYCApplicationResponse,
    KYCReviewRequest, KYCStatusResponse, AdminKYCListResponse
)

router = APIRouter()

# File upload configuration
UPLOAD_DIR = "uploads/kyc"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-document")
async def upload_kyc_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a KYC document."""
    
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Validate document type
    if document_type not in [dt.value for dt in DocumentType]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document type. Allowed types: {[dt.value for dt in DocumentType]}"
        )
    
    # Generate unique filename
    unique_filename = f"{current_user.id}_{document_type}_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    # Create database record
    kyc_document = KYCDocument(
        user_id=current_user.id,
        document_type=document_type,
        file_path=file_path,
        file_name=file.filename,
        file_size=len(file_content),
        mime_type=file.content_type or "application/octet-stream"
    )
    
    db.add(kyc_document)
    await db.commit()
    await db.refresh(kyc_document)
    
    return {
        "message": "Document uploaded successfully",
        "document_id": kyc_document.id,
        "file_path": file_path
    }

@router.get("/documents", response_model=List[KYCDocumentResponse])
async def get_user_kyc_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all KYC documents for the current user."""
    query = select(KYCDocument).where(KYCDocument.user_id == current_user.id)
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return [
        KYCDocumentResponse(
            id=doc.id,
            user_id=doc.user_id,
            document_type=doc.document_type,
            file_path=doc.file_path,
            file_name=doc.file_name,
            file_size=doc.file_size,
            mime_type=doc.mime_type,
            status=doc.status,
            uploaded_at=doc.uploaded_at,
            verified_at=doc.verified_at,
            rejection_reason=doc.rejection_reason
        ) for doc in documents
    ]

@router.get("/document/{document_id}")
async def download_kyc_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download a KYC document."""
    query = select(KYCDocument).where(
        and_(KYCDocument.id == document_id, KYCDocument.user_id == current_user.id)
    )
    result = await db.execute(query)
    document = result.scalars().first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if not os.path.exists(document.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on server"
        )
    
    return FileResponse(
        document.file_path,
        filename=document.file_name,
        media_type=document.mime_type
    )

@router.post("/application", response_model=KYCApplicationResponse)
async def submit_kyc_application(
    application_data: KYCApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit a KYC application."""
    
    # Check if user already has a pending application
    existing_query = select(KYCApplication).where(
        and_(
            KYCApplication.user_id == current_user.id,
            KYCApplication.status == KYCStatus.PENDING.value
        )
    )
    existing_result = await db.execute(existing_query)
    existing_application = existing_result.scalars().first()
    
    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending KYC application"
        )
    
    # Create new application
    kyc_application = KYCApplication(
        user_id=current_user.id,
        full_name=application_data.full_name,
        date_of_birth=application_data.date_of_birth,
        gender=application_data.gender,
        address=application_data.address,
        city=application_data.city,
        state=application_data.state,
        pincode=application_data.pincode,
        emergency_contact_name=application_data.emergency_contact_name,
        emergency_contact_phone=application_data.emergency_contact_phone,
        emergency_contact_relation=application_data.emergency_contact_relation,
        driving_license_number=application_data.driving_license_number,
        vehicle_number=application_data.vehicle_number,
        vehicle_type=application_data.vehicle_type,
        vehicle_model=application_data.vehicle_model,
        vehicle_year=application_data.vehicle_year
    )
    
    db.add(kyc_application)
    await db.commit()
    await db.refresh(kyc_application)
    
    return KYCApplicationResponse(
        id=kyc_application.id,
        user_id=kyc_application.user_id,
        status=kyc_application.status,
        submitted_at=kyc_application.submitted_at,
        reviewed_at=kyc_application.reviewed_at,
        review_notes=kyc_application.review_notes,
        full_name=kyc_application.full_name,
        date_of_birth=kyc_application.date_of_birth,
        gender=kyc_application.gender,
        address=kyc_application.address,
        city=kyc_application.city,
        state=kyc_application.state,
        pincode=kyc_application.pincode,
        emergency_contact_name=kyc_application.emergency_contact_name,
        emergency_contact_phone=kyc_application.emergency_contact_phone,
        emergency_contact_relation=kyc_application.emergency_contact_relation,
        driving_license_number=kyc_application.driving_license_number,
        vehicle_number=kyc_application.vehicle_number,
        vehicle_type=kyc_application.vehicle_type,
        vehicle_model=kyc_application.vehicle_model,
        vehicle_year=kyc_application.vehicle_year
    )

@router.get("/application", response_model=Optional[KYCApplicationResponse])
async def get_user_kyc_application(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current user's KYC application."""
    query = select(KYCApplication).where(KYCApplication.user_id == current_user.id)
    result = await db.execute(query)
    application = result.scalars().first()
    
    if not application:
        return None
    
    return KYCApplicationResponse(
        id=application.id,
        user_id=application.user_id,
        status=application.status,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
        review_notes=application.review_notes,
        full_name=application.full_name,
        date_of_birth=application.date_of_birth,
        gender=application.gender,
        address=application.address,
        city=application.city,
        state=application.state,
        pincode=application.pincode,
        emergency_contact_name=application.emergency_contact_name,
        emergency_contact_phone=application.emergency_contact_phone,
        emergency_contact_relation=application.emergency_contact_relation,
        driving_license_number=application.driving_license_number,
        vehicle_number=application.vehicle_number,
        vehicle_type=application.vehicle_type,
        vehicle_model=application.vehicle_model,
        vehicle_year=application.vehicle_year
    )

@router.get("/status", response_model=KYCStatusResponse)
async def get_kyc_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get KYC status for the current user."""
    
    # Get application
    app_query = select(KYCApplication).where(KYCApplication.user_id == current_user.id)
    app_result = await db.execute(app_query)
    application = app_result.scalars().first()
    
    # Get documents
    doc_query = select(KYCDocument).where(KYCDocument.user_id == current_user.id)
    doc_result = await db.execute(doc_query)
    documents = doc_result.scalars().all()
    
    # Calculate status
    application_status = application.status if application else "not_submitted"
    approved_docs = sum(1 for doc in documents if doc.status == KYCStatus.APPROVED.value)
    pending_docs = sum(1 for doc in documents if doc.status == KYCStatus.PENDING.value)
    
    # Determine missing documents
    required_docs = ["aadhar_card", "pan_card"]
    if current_user.role == UserRole.DRIVER.value:
        required_docs.extend(["driving_license", "vehicle_registration", "insurance_document"])
    
    uploaded_doc_types = [doc.document_type for doc in documents]
    missing_documents = [doc_type for doc_type in required_docs if doc_type not in uploaded_doc_types]
    
    is_complete = (
        application and 
        application.status == KYCStatus.APPROVED.value and
        len(missing_documents) == 0 and
        pending_docs == 0
    )
    is_complete = bool(is_complete)
    
    return KYCStatusResponse(
        application_status=application_status,
        documents_status=[
            KYCDocumentResponse(
                id=doc.id,
                user_id=doc.user_id,
                document_type=doc.document_type,
                file_path=doc.file_path,
                file_name=doc.file_name,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                status=doc.status,
                uploaded_at=doc.uploaded_at,
                verified_at=doc.verified_at,
                rejection_reason=doc.rejection_reason
            ) for doc in documents
        ],
        application=KYCApplicationResponse(
            id=application.id,
            user_id=application.user_id,
            status=application.status,
            submitted_at=application.submitted_at,
            reviewed_at=application.reviewed_at,
            review_notes=application.review_notes,
            full_name=application.full_name,
            date_of_birth=application.date_of_birth,
            gender=application.gender,
            address=application.address,
            city=application.city,
            state=application.state,
            pincode=application.pincode,
            emergency_contact_name=application.emergency_contact_name,
            emergency_contact_phone=application.emergency_contact_phone,
            emergency_contact_relation=application.emergency_contact_relation,
            driving_license_number=application.driving_license_number,
            vehicle_number=application.vehicle_number,
            vehicle_type=application.vehicle_type,
            vehicle_model=application.vehicle_model,
            vehicle_year=application.vehicle_year
        ) if application else None,
        is_complete=is_complete,
        missing_documents=missing_documents
    )

# Admin endpoints
@router.get("/admin/applications", response_model=List[AdminKYCListResponse])
async def get_all_kyc_applications(
    status_filter: Optional[str] = None,
    current_user: User = Depends(check_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Get all KYC applications for admin review."""
    
    query = select(KYCApplication, User).join(User, KYCApplication.user_id == User.id)
    
    if status_filter:
        query = query.where(KYCApplication.status == status_filter)
    
    query = query.order_by(KYCApplication.submitted_at.desc())
    
    result = await db.execute(query)
    applications = result.all()
    
    response_list = []
    for app, user in applications:
        # Count documents
        doc_query = select(func.count(KYCDocument.id)).where(KYCDocument.user_id == user.id)
        doc_result = await db.execute(doc_query)
        total_docs = doc_result.scalar()
        
        approved_docs_query = select(func.count(KYCDocument.id)).where(
            and_(KYCDocument.user_id == user.id, KYCDocument.status == KYCStatus.APPROVED.value)
        )
        approved_docs_result = await db.execute(approved_docs_query)
        approved_docs = approved_docs_result.scalar()
        
        pending_docs_query = select(func.count(KYCDocument.id)).where(
            and_(KYCDocument.user_id == user.id, KYCDocument.status == KYCStatus.PENDING.value)
        )
        pending_docs_result = await db.execute(pending_docs_query)
        pending_docs = pending_docs_result.scalar()
        
        response_list.append(AdminKYCListResponse(
            id=app.id,
            user_id=app.user_id,
            user_email=user.email,
            user_name=f"{user.first_name} {user.last_name}",
            status=app.status,
            submitted_at=app.submitted_at,
            document_count=total_docs,
            approved_documents=approved_docs,
            pending_documents=pending_docs
        ))
    
    return response_list

@router.get("/admin/application/{application_id}", response_model=KYCApplicationResponse)
async def get_kyc_application_details(
    application_id: int,
    current_user: User = Depends(check_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed KYC application for admin review."""
    query = select(KYCApplication).where(KYCApplication.id == application_id)
    result = await db.execute(query)
    application = result.scalars().first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    return KYCApplicationResponse(
        id=application.id,
        user_id=application.user_id,
        status=application.status,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
        review_notes=application.review_notes,
        full_name=application.full_name,
        date_of_birth=application.date_of_birth,
        gender=application.gender,
        address=application.address,
        city=application.city,
        state=application.state,
        pincode=application.pincode,
        emergency_contact_name=application.emergency_contact_name,
        emergency_contact_phone=application.emergency_contact_phone,
        emergency_contact_relation=application.emergency_contact_relation,
        driving_license_number=application.driving_license_number,
        vehicle_number=application.vehicle_number,
        vehicle_type=application.vehicle_type,
        vehicle_model=application.vehicle_model,
        vehicle_year=application.vehicle_year
    )

@router.post("/admin/application/{application_id}/review")
async def review_kyc_application(
    application_id: int,
    review_data: KYCReviewRequest,
    current_user: User = Depends(check_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Review and approve/reject a KYC application."""
    
    # Get application
    query = select(KYCApplication).where(KYCApplication.id == application_id)
    result = await db.execute(query)
    application = result.scalars().first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != KYCStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application is not pending review"
        )
    
    # Update application status
    new_status = KYCStatus.APPROVED.value if review_data.approved else KYCStatus.REJECTED.value
    
    stmt = (
        update(KYCApplication)
        .where(KYCApplication.id == application_id)
        .values(
            status=new_status,
            reviewed_by=current_user.id,
            reviewed_at=datetime.utcnow(),
            review_notes=review_data.review_notes
        )
    )
    await db.execute(stmt)
    
    # If approved, update user status
    if review_data.approved:
        user_stmt = (
            update(User)
            .where(User.id == application.user_id)
            .values(
                status=UserStatus.ACTIVE.value,
                is_verified=True,
                updated_at=datetime.utcnow()
            )
        )
        await db.execute(user_stmt)
    
    await db.commit()
    
    return {
        "message": f"Application {'approved' if review_data.approved else 'rejected'} successfully",
        "application_id": application_id,
        "status": new_status,
        "reviewed_by": current_user.id,
        "reviewed_at": datetime.utcnow()
    }

@router.post("/admin/document/{document_id}/verify")
async def verify_kyc_document(
    document_id: int,
    approved: bool = Form(...),
    rejection_reason: Optional[str] = Form(None),
    current_user: User = Depends(check_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Verify a KYC document."""
    
    # Get document
    query = select(KYCDocument).where(KYCDocument.id == document_id)
    result = await db.execute(query)
    document = result.scalars().first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.status != KYCStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is not pending verification"
        )
    
    # Update document status
    new_status = KYCStatus.APPROVED.value if approved else KYCStatus.REJECTED.value
    
    stmt = (
        update(KYCDocument)
        .where(KYCDocument.id == document_id)
        .values(
            status=new_status,
            verified_by=current_user.id,
            verified_at=datetime.utcnow(),
            rejection_reason=rejection_reason if not approved else None
        )
    )
    await db.execute(stmt)
    await db.commit()
    
    return {
        "message": f"Document {'approved' if approved else 'rejected'} successfully",
        "document_id": document_id,
        "status": new_status,
        "verified_by": current_user.id,
        "verified_at": datetime.utcnow()
    } 