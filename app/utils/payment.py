import razorpay
import stripe
from typing import Dict, Any
from fastapi import HTTPException, status
from app.schemas.payment import PaymentMethodCreate
from app.models.payment import Payment, PaymentMethodEnum

class RazorpayClient:
    def __init__(self, key_id: str, key_secret: str):
        self.client = razorpay.Client(auth=(key_id, key_secret))

    async def create_payment_method(self, payment_method: PaymentMethodCreate) -> Dict[str, Any]:
        """Create a payment method token with Razorpay."""
        try:
            if payment_method.type == "card":
                # Create a token for the card
                token_data = {
                    "card": {
                        "number": payment_method.card_number,
                        "expiry_month": payment_method.card_exp_month,
                        "expiry_year": payment_method.card_exp_year,
                        "cvv": payment_method.card_cvv
                    }
                }
                token = self.client.token.create(data=token_data)
                return {
                    "id": token["id"],
                    "customer_id": token["customer_id"],
                    "card_brand": token["card"]["network"]
                }
            elif payment_method.type == "upi":
                # Validate UPI ID
                vpa_data = {
                    "vpa": payment_method.upi_id
                }
                validation = self.client.payment.validateVpa(vpa_data)
                if not validation["success"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid UPI ID"
                    )
                return {
                    "id": payment_method.upi_id,
                    "customer_id": None,
                    "type": "upi"
                }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create payment method: {str(e)}"
            )

    async def create_payment(self, payment: Payment) -> Dict[str, Any]:
        """Create a payment order with Razorpay."""
        try:
            # Create order
            order_data = {
                "amount": int(payment.amount * 100),  # Convert to paise
                "currency": payment.currency,
                "receipt": f"ride_{payment.ride_id}",
                "notes": {
                    "ride_id": payment.ride_id,
                    "payer_id": payment.payer_id,
                    "payee_id": payment.payee_id
                }
            }
            order = self.client.order.create(data=order_data)

            return {
                "id": order["id"],
                "order_id": order["id"],
                "amount": order["amount"] / 100,  # Convert back to rupees
                "currency": order["currency"],
                "status": order["status"]
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create payment: {str(e)}"
            )

    async def process_webhook(self, payload: Dict[str, Any]) -> str:
        """Process Razorpay webhook payload."""
        try:
            # Verify webhook signature
            # self.client.utility.verify_webhook_signature(str(payload), signature, webhook_secret)

            # Extract payment ID from payload
            if payload["event"] == "payment.captured":
                return payload["payload"]["payment"]["entity"]["order_id"]
            return None
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process webhook: {str(e)}"
            )

    async def refund_payment(self, payment_id: str) -> Dict[str, Any]:
        """Initiate refund for a payment."""
        try:
            refund = self.client.payment.refund(payment_id)
            return {
                "id": refund["id"],
                "amount": refund["amount"] / 100,
                "status": refund["status"]
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process refund: {str(e)}"
            )

class StripeClient:
    def __init__(self, api_key: str):
        stripe.api_key = api_key

    async def create_payment_method(self, payment_method: PaymentMethodCreate) -> Dict[str, Any]:
        """Create a payment method with Stripe."""
        try:
            if payment_method.type == "card":
                # Create payment method
                stripe_payment_method = stripe.PaymentMethod.create(
                    type="card",
                    card={
                        "number": payment_method.card_number,
                        "exp_month": payment_method.card_exp_month,
                        "exp_year": payment_method.card_exp_year,
                        "cvc": payment_method.card_cvv
                    }
                )
                return {
                    "id": stripe_payment_method.id,
                    "customer_id": stripe_payment_method.customer,
                    "card_brand": stripe_payment_method.card.brand
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Payment method type not supported by Stripe"
                )
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create payment method: {str(e)}"
            )

    async def create_payment(self, payment: Payment) -> Dict[str, Any]:
        """Create a payment intent with Stripe."""
        try:
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(payment.amount * 100),  # Convert to cents
                currency=payment.currency.lower(),
                payment_method_types=[payment.payment_method.name],
                metadata={
                    "ride_id": payment.ride_id,
                    "payer_id": payment.payer_id,
                    "payee_id": payment.payee_id
                }
            )

            return {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "amount": intent.amount / 100,  # Convert back to dollars
                "currency": intent.currency,
                "status": intent.status
            }
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create payment: {str(e)}"
            )

    async def process_webhook(self, payload: Dict[str, Any]) -> str:
        """Process Stripe webhook payload."""
        try:
            event = stripe.Event.construct_from(payload, stripe.api_key)

            if event.type == "payment_intent.succeeded":
                return event.data.object.id
            return None
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process webhook: {str(e)}"
            )

    async def refund_payment(self, payment_intent_id: str) -> Dict[str, Any]:
        """Initiate refund for a payment."""
        try:
            refund = stripe.Refund.create(payment_intent=payment_intent_id)
            return {
                "id": refund.id,
                "amount": refund.amount / 100,
                "status": refund.status
            }
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process refund: {str(e)}"
            )