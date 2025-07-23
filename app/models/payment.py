from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Enum, JSON, Boolean
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

# --- ENUM CLASSES ---
class PaymentMethodEnum(enum.Enum):
    CASH = "cash"
    CARD = "card"
    WALLET = "wallet"
    UPI = "upi"

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentProvider(enum.Enum):
    RAZORPAY = "razorpay"
    STRIPE = "stripe"

# --- PAYMENT MODEL ---
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    ride_id = Column(Integer, ForeignKey("rides.id"))
    payer_id = Column(Integer, ForeignKey("users.id"))  # Rider
    payee_id = Column(Integer, ForeignKey("users.id"))  # Driver

    amount = Column(Float)
    currency = Column(String, default="INR")
    payment_method = Column(Enum(PaymentMethodEnum))
    payment_provider = Column(Enum(PaymentProvider))
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)

    # Provider-specific details
    provider_payment_id = Column(String, nullable=True)
    provider_order_id = Column(String, nullable=True)
    provider_refund_id = Column(String, nullable=True)
    provider_response = Column(JSON, nullable=True)

    # Optional info
    description = Column(String)
    failure_reason = Column(String, nullable=True)
    refund_reason = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    refunded_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    ride = relationship("Ride", backref="payment")
    payer = relationship("User", foreign_keys=[payer_id])
    payee = relationship("User", foreign_keys=[payee_id])

# --- PAYMENT METHOD MODEL ---
class UserPaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    type = Column(Enum(PaymentMethodEnum))
    provider = Column(Enum(PaymentProvider))
    is_default = Column(Boolean, default=False)

    # Card details (optional)
    card_last4 = Column(String)
    card_brand = Column(String)
    card_exp_month = Column(Integer)
    card_exp_year = Column(Integer)

    # UPI details (optional)
    upi_id = Column(String)

    # Provider-specific
    provider_payment_method_id = Column(String)
    provider_customer_id = Column(String)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship
    user = relationship("User", backref="payment_methods")
