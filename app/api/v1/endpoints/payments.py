from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.utils.auth import get_current_user
from app.schemas.payment import (
    PaymentMethodCreate,
    PaymentMethodUpdate,
    PaymentMethodResponse,
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentList
)
from app.services.payment import PaymentService

router = APIRouter()

@router.post("/methods", response_model=PaymentMethodResponse)
async def create_payment_method(
    *,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    payment_method_in: PaymentMethodCreate
) -> PaymentMethodResponse:
    """Create a new payment method for the current user."""
    payment_service = PaymentService(db)
    return await payment_service.create_payment_method(current_user.id, payment_method_in)

@router.get("/methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[PaymentMethodResponse]:
    """Get all payment methods for the current user."""
    payment_service = PaymentService(db)
    return await payment_service.get_user_payment_methods(current_user.id)

@router.put("/methods/{method_id}", response_model=PaymentMethodResponse)
async def update_payment_method(
    *,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    method_id: int,
    payment_method_in: PaymentMethodUpdate
) -> PaymentMethodResponse:
    """Update a payment method."""
    payment_service = PaymentService(db)
    return await payment_service.update_payment_method(current_user.id, method_id, payment_method_in)

@router.delete("/methods/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_method(
    *,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    method_id: int
):
    """Delete a payment method."""
    payment_service = PaymentService(db)
    await payment_service.delete_payment_method(current_user.id, method_id)

@router.post("/initiate", response_model=PaymentResponse)
async def initiate_payment(
    *,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    payment_in: PaymentCreate
) -> PaymentResponse:
    """Initiate a new payment."""
    payment_service = PaymentService(db)
    return await payment_service.initiate_payment(current_user.id, payment_in)

@router.post("/webhook/{provider}")
async def payment_webhook(
    *,
    db: AsyncSession = Depends(get_db),
    provider: str,
    payload: dict
):
    """Handle payment gateway webhooks."""
    payment_service = PaymentService(db)
    await payment_service.handle_webhook(provider, payload)
    return {"status": "success"}

@router.get("/history", response_model=PaymentList)
async def get_payment_history(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    page: int = 1,
    size: int = 10
) -> PaymentList:
    """Get payment history for the current user."""
    payment_service = PaymentService(db)
    return await payment_service.get_user_payments(current_user.id, page, size)

@router.post("/refund/{payment_id}", response_model=PaymentResponse)
async def refund_payment(
    *,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    payment_id: int,
    reason: str
) -> PaymentResponse:
    """Initiate a refund for a payment."""
    payment_service = PaymentService(db)
    return await payment_service.refund_payment(current_user.id, payment_id, reason)