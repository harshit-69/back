from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class TransactionType(enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    user = relationship("User", backref="wallet")
    transactions = relationship("Transaction", back_populates="wallet")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id"))
    ride_id = Column(Integer, ForeignKey("rides.id"), nullable=True)
    
    amount = Column(Float)
    type = Column(Enum(TransactionType))
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    
    # Payment details
    payment_method = Column(String)  # card, bank_transfer, etc.
    payment_id = Column(String, nullable=True)  # External payment gateway ID
    
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    wallet = relationship("Wallet", back_populates="transactions")
    ride = relationship("Ride", backref="transactions")