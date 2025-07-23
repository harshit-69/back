from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class KYCDocumentUpload(BaseModel):
    document_type: str
    file_name: str
    file_size: int
    mime_type: str

class KYCDocumentResponse(BaseModel):
    id: int
    user_id: int
    document_type: str
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    status: str
    uploaded_at: datetime
    verified_at: Optional[datetime]
    rejection_reason: Optional[str]

class KYCApplicationCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    date_of_birth: str = Field(..., min_length=10, max_length=10)
    gender: str = Field(..., min_length=1, max_length=10)
    address: str = Field(..., min_length=10, max_length=500)
    city: str = Field(..., min_length=2, max_length=50)
    state: str = Field(..., min_length=2, max_length=50)
    pincode: str = Field(..., min_length=6, max_length=6)
    emergency_contact_name: str = Field(..., min_length=2, max_length=100)
    emergency_contact_phone: str = Field(..., min_length=10, max_length=15)
    emergency_contact_relation: str = Field(..., min_length=2, max_length=50)
    
    # Driver specific fields (optional)
    driving_license_number: Optional[str] = Field(None, min_length=5, max_length=20)
    vehicle_number: Optional[str] = Field(None, min_length=5, max_length=20)
    vehicle_type: Optional[str] = Field(None, min_length=2, max_length=50)
    vehicle_model: Optional[str] = Field(None, min_length=2, max_length=50)
    vehicle_year: Optional[str] = Field(None, min_length=4, max_length=4)

class KYCApplicationResponse(BaseModel):
    id: int
    user_id: int
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    
    # Personal Information
    full_name: str
    date_of_birth: str
    gender: str
    address: str
    city: str
    state: str
    pincode: str
    
    # Contact Information
    emergency_contact_name: str
    emergency_contact_phone: str
    emergency_contact_relation: str
    
    # Driver Specific
    driving_license_number: Optional[str]
    vehicle_number: Optional[str]
    vehicle_type: Optional[str]
    vehicle_model: Optional[str]
    vehicle_year: Optional[str]

class KYCReviewRequest(BaseModel):
    approved: bool
    review_notes: Optional[str] = Field(None, max_length=1000)

class KYCStatusResponse(BaseModel):
    application_status: str
    documents_status: List[KYCDocumentResponse]
    application: Optional[KYCApplicationResponse]
    is_complete: bool
    missing_documents: List[str]

class AdminKYCListResponse(BaseModel):
    id: int
    user_id: int
    user_email: str
    user_name: str
    status: str
    submitted_at: datetime
    document_count: int
    approved_documents: int
    pending_documents: int 