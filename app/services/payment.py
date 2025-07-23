from typing import List, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.payment import Payment, UserPaymentMethod, PaymentStatus, PaymentMethodEnum
from app.models.ride import Ride
from app.schemas.payment import (
    PaymentMethodCreate,
    PaymentMethodUpdate,
    PaymentCreate,
    PaymentList
)
from app.core.config import settings
from app.utils.payment import RazorpayClient, StripeClient

class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.razorpay = RazorpayClient(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET
        )
        self.stripe = StripeClient(settings.STRIPE_API_KEY)

    async def create_payment_method(self, user_id: int, payment_method_in: PaymentMethodCreate) -> UserPaymentMethod:
        """Create a new payment method for a user."""
        # Validate payment method data based on type
        if payment_method_in.type == "card":
            if not all([payment_method_in.card_number, payment_method_in.card_exp_month,
                       payment_method_in.card_exp_year, payment_method_in.card_cvv]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Card details are required for card payment method"
                )
        elif payment_method_in.type == "upi" and not payment_method_in.upi_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="UPI ID is required for UPI payment method"
            )

        # Create payment method with provider
        provider_payment_method = None
        if payment_method_in.provider == "stripe":
            provider_payment_method = await self.stripe.create_payment_method(
                payment_method_in
            )
        elif payment_method_in.provider == "razorpay":
            provider_payment_method = await self.razorpay.create_payment_method(
                payment_method_in
            )

        # Create payment method in database
        db_payment_method = UserPaymentMethod(
            user_id=user_id,
            type=payment_method_in.type,
            provider=payment_method_in.provider,
            is_default=payment_method_in.is_default,
            provider_payment_method_id=provider_payment_method["id"],
            provider_customer_id=provider_payment_method["customer_id"]
        )

        if payment_method_in.type == "card":
            db_payment_method.card_last4 = payment_method_in.card_number[-4:]
            db_payment_method.card_brand = provider_payment_method["card_brand"]
            db_payment_method.card_exp_month = payment_method_in.card_exp_month
            db_payment_method.card_exp_year = payment_method_in.card_exp_year
        elif payment_method_in.type == "upi":
            db_payment_method.upi_id = payment_method_in.upi_id

        # If this is the default method, unset other default methods
        if payment_method_in.is_default:
            query = select(PaymentMethod).where(
                PaymentMethod.user_id == user_id,
                PaymentMethod.is_default == True
            )
            result = await self.db.execute(query)
            existing_default = result.scalars().first()
            if existing_default:
                existing_default.is_default = False

        self.db.add(db_payment_method)
        await self.db.commit()
        await self.db.refresh(db_payment_method)

        return db_payment_method

    async def get_user_payment_methods(self, user_id: int) -> List[UserPaymentMethod]:
        """Get all payment methods for a user."""
        query = select(UserPaymentMethod).where(UserPaymentMethod.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_payment_method(self, user_id: int, method_id: int,
                                  payment_method_in: PaymentMethodUpdate) -> UserPaymentMethod:
        """Update a payment method."""
        query = select(UserPaymentMethod).where(
            UserPaymentMethod.id == method_id,
            UserPaymentMethod.user_id == user_id
        )
        result = await self.db.execute(query)
        payment_method = result.scalars().first()

        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment method not found"
            )

        # Update default status
        if payment_method_in.is_default and not payment_method.is_default:
            # Unset other default methods
            query = select(UserPaymentMethod).where(
                UserPaymentMethod.user_id == user_id,
                UserPaymentMethod.is_default == True
            )
            result = await self.db.execute(query)
            existing_default = result.scalars().first()
            if existing_default:
                existing_default.is_default = False

        payment_method.is_default = payment_method_in.is_default
        await self.db.commit()
        await self.db.refresh(payment_method)

        return payment_method

    async def delete_payment_method(self, user_id: int, method_id: int) -> None:
        """Delete a payment method."""
        query = select(UserPaymentMethod).where(
            UserPaymentMethod.id == method_id,
            UserPaymentMethod.user_id == user_id
        )
        result = await self.db.execute(query)
        payment_method = result.scalars().first()

        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment method not found"
            )

        # Delete from payment provider
        if payment_method.provider == "stripe":
            await self.stripe.delete_payment_method(payment_method.provider_payment_method_id)
        elif payment_method.provider == "razorpay":
            await self.razorpay.delete_payment_method(payment_method.provider_payment_method_id)

        await self.db.delete(payment_method)
        await self.db.commit()

    async def initiate_payment(self, user_id: int, payment_in: PaymentCreate) -> Payment:
        """Initiate a new payment."""
        # Get ride details
        query = select(Ride).where(Ride.id == payment_in.ride_id)
        result = await self.db.execute(query)
        ride = result.scalars().first()

        if not ride:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ride not found"
            )

        # Create payment in database
        db_payment = Payment(
            ride_id=payment_in.ride_id,
            payer_id=user_id,
            payee_id=ride.driver_id,
            amount=payment_in.amount,
            currency=payment_in.currency,
            payment_method=payment_in.payment_method,
            payment_provider=payment_in.payment_provider,
            description=payment_in.description,
            status=PaymentStatus.PENDING
        )

        self.db.add(db_payment)
        await self.db.commit()
        await self.db.refresh(db_payment)

        # Initiate payment with provider
        try:
            if payment_in.payment_provider == "stripe":
                provider_payment = await self.stripe.create_payment(db_payment)
            elif payment_in.payment_provider == "razorpay":
                provider_payment = await self.razorpay.create_payment(db_payment)

            # Update payment with provider details
            db_payment.provider_payment_id = provider_payment["id"]
            db_payment.provider_order_id = provider_payment.get("order_id")
            db_payment.provider_response = provider_payment
            db_payment.status = PaymentStatus.PROCESSING

            await self.db.commit()
            await self.db.refresh(db_payment)

        except Exception as e:
            db_payment.status = PaymentStatus.FAILED
            db_payment.failure_reason = str(e)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment initiation failed: {str(e)}"
            )

        return db_payment

    async def handle_webhook(self, provider: str, payload: dict) -> None:
        """Handle payment gateway webhooks."""
        try:
            if provider == "stripe":
                payment_id = await self.stripe.process_webhook(payload)
            elif provider == "razorpay":
                payment_id = await self.razorpay.process_webhook(payload)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid payment provider"
                )

            # Update payment status
            query = select(Payment).where(Payment.provider_payment_id == payment_id)
            result = await self.db.execute(query)
            payment = result.scalars().first()

            if payment:
                payment.status = PaymentStatus.COMPLETED
                payment.completed_at = datetime.utcnow()
                await self.db.commit()

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook processing failed: {str(e)}"
            )

    async def get_user_payments(self, user_id: int, page: int = 1, size: int = 10) -> PaymentList:
        """Get paginated payment history for a user."""
        # Get total count
        count_query = select(Payment).where(
            (Payment.payer_id == user_id) | (Payment.payee_id == user_id)
        )
        total = len((await self.db.execute(count_query)).scalars().all())

        # Get paginated payments
        query = select(Payment).where(
            (Payment.payer_id == user_id) | (Payment.payee_id == user_id)
        ).offset((page - 1) * size).limit(size)
        result = await self.db.execute(query)
        payments = result.scalars().all()

        return PaymentList(
            payments=payments,
            total=total,
            page=page,
            size=size
        )

    async def refund_payment(self, user_id: int, payment_id: int, reason: str) -> Payment:
        """Initiate a refund for a payment."""
        # Get payment details
        query = select(Payment).where(
            Payment.id == payment_id,
            Payment.status == PaymentStatus.COMPLETED
        )
        result = await self.db.execute(query)
        payment = result.scalars().first()

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Completed payment not found"
            )

        # Verify user is either payer or payee
        if payment.payer_id != user_id and payment.payee_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to refund this payment"
            )

        try:
            # Process refund with provider
            if payment.payment_provider == "stripe":
                refund = await self.stripe.refund_payment(payment.provider_payment_id)
            elif payment.payment_provider == "razorpay":
                refund = await self.razorpay.refund_payment(payment.provider_payment_id)

            # Update payment status
            payment.status = PaymentStatus.REFUNDED
            payment.provider_refund_id = refund["id"]
            payment.refund_reason = reason
            payment.refunded_at = datetime.utcnow()

            await self.db.commit()
            await self.db.refresh(payment)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Refund failed: {str(e)}"
            )

        return payment