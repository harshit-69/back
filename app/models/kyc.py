from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class KYCStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class DocumentType(str, enum.Enum):
    AADHAR_CARD = "aadhar_card"
    PAN_CARD = "pan_card"
    DRIVING_LICENSE = "driving_license"
    VEHICLE_REGISTRATION = "vehicle_registration"
    INSURANCE_DOCUMENT = "insurance_document"
    PROFILE_PICTURE = "profile_picture"
    ADDRESS_PROOF = "address_proof"

class KYCDocument(Base):
    __tablename__ = "kyc_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Document Information
    document_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    mime_type = Column(String, nullable=False)
    
    # Verification Status
    status = Column(String, default=KYCStatus.PENDING.value)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Metadata
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="kyc_documents")
    verifier = relationship("User", foreign_keys=[verified_by])

class KYCApplication(Base):
    __tablename__ = "kyc_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Application Status
    status = Column(String, default=KYCStatus.PENDING.value)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Personal Information
    full_name = Column(String, nullable=False)
    date_of_birth = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    pincode = Column(String, nullable=False)
    
    # Contact Information
    emergency_contact_name = Column(String, nullable=False)
    emergency_contact_phone = Column(String, nullable=False)
    emergency_contact_relation = Column(String, nullable=False)
    
    # Driver Specific (if applicable)
    driving_license_number = Column(String, nullable=True)
    vehicle_number = Column(String, nullable=True)
    vehicle_type = Column(String, nullable=True)
    vehicle_model = Column(String, nullable=True)
    vehicle_year = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="kyc_applications")
    reviewer = relationship("User", foreign_keys=[reviewed_by]) 