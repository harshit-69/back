from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.payment import PaymentMethodEnum, PaymentStatus, PaymentProvider

class PaymentMethodCreate(BaseModel):
    type: PaymentMethodEnum
    provider: PaymentProvider
    card_number: Optional[str] = Field(None, min_length=16, max_length=16)
    card_exp_month: Optional[int] = Field(None, ge=1, le=12)
    card_exp_year: Optional[int] = Field(None, ge=2024)
    card_cvv: Optional[str] = Field(None, min_length=3, max_length=4)
    upi_id: Optional[str] = None
    is_default: bool = False

class PaymentMethodUpdate(BaseModel):
    is_default: bool

class PaymentMethodResponse(BaseModel):
    id: int
    type: PaymentMethodEnum
    provider: PaymentProvider
    is_default: bool
    card_last4: Optional[str]
    card_brand: Optional[str]
    card_exp_month: Optional[int]
    card_exp_year: Optional[int]
    upi_id: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

class PaymentCreate(BaseModel):
    ride_id: int
    payment_method: PaymentMethodEnum
    payment_provider: PaymentProvider
    amount: float = Field(..., gt=0)
    currency: str = "INR"
    description: str

class PaymentUpdate(BaseModel):
    status: PaymentStatus
    provider_payment_id: Optional[str]
    provider_order_id: Optional[str]
    provider_refund_id: Optional[str]
    provider_response: Optional[dict]
    failure_reason: Optional[str]
    refund_reason: Optional[str]

class PaymentResponse(BaseModel):
    id: int
    ride_id: int
    payer_id: int
    payee_id: int
    amount: float
    currency: str
    payment_method: PaymentMethodEnum
    payment_provider: PaymentProvider
    status: PaymentStatus
    provider_payment_id: Optional[str]
    provider_order_id: Optional[str]
    provider_refund_id: Optional[str]
    description: str
    failure_reason: Optional[str]
    refund_reason: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    refunded_at: Optional[datetime]

    class Config:
        orm_mode = True

class PaymentList(BaseModel):
    payments: List[PaymentResponse]
    total: int
    page: int
    size: int