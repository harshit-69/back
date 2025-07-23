from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from fastapi import HTTPException, status

from app.models.user import User
from app.core.config import settings
from app.utils.email import send_email
from app.utils.sms import send_sms

class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_ride_request_notification(self, ride_id: int, driver_ids: List[int]):
        """Send notification to drivers about new ride request."""
        # Get ride details
        # This would typically query the ride table
        ride_details = {
            "id": ride_id,
            "pickup_location": "Sample Location",
            "dropoff_location": "Sample Destination",
            "estimated_fare": 150.0
        }
        
        # Send push notification to drivers
        for driver_id in driver_ids:
            await self._send_push_notification(
                user_id=driver_id,
                title="New Ride Request",
                body=f"Ride from {ride_details['pickup_location']} to {ride_details['dropoff_location']}",
                data={"ride_id": ride_id, "type": "ride_request"}
            )

    async def send_ride_accepted_notification(self, ride_id: int, rider_id: int, driver_id: int):
        """Send notification to rider when driver accepts ride."""
        # Get driver details
        result = await self.db.execute(select(User).where(User.id == driver_id))
        driver = result.scalars().first()
        
        if driver:
            driver_name = f"{driver.first_name} {driver.last_name}"
            vehicle_info = f"{driver.vehicle_type} - {driver.vehicle_number}"
            
            # Send notification to rider
            await self._send_push_notification(
                user_id=rider_id,
                title="Driver Found!",
                body=f"{driver_name} ({vehicle_info}) is on the way",
                data={"ride_id": ride_id, "type": "ride_accepted"}
            )
            
            # Send SMS to rider
            await self._send_sms_notification(
                user_id=rider_id,
                message=f"Your ride has been accepted by {driver_name}. Vehicle: {vehicle_info}"
            )

    async def send_ride_started_notification(self, ride_id: int, rider_id: int):
        """Send notification when ride starts."""
        await self._send_push_notification(
            user_id=rider_id,
            title="Ride Started",
            body="Your ride has started. Enjoy your journey!",
            data={"ride_id": ride_id, "type": "ride_started"}
        )

    async def send_ride_completed_notification(self, ride_id: int, rider_id: int, driver_id: int):
        """Send notification when ride is completed."""
        # Send to rider
        await self._send_push_notification(
            user_id=rider_id,
            title="Ride Completed",
            body="Your ride has been completed. Please rate your experience.",
            data={"ride_id": ride_id, "type": "ride_completed"}
        )
        
        # Send to driver
        await self._send_push_notification(
            user_id=driver_id,
            title="Ride Completed",
            body="Ride completed successfully. Payment will be processed shortly.",
            data={"ride_id": ride_id, "type": "ride_completed"}
        )

    async def send_payment_notification(self, user_id: int, amount: float, status: str):
        """Send payment notification."""
        status_text = "successful" if status == "completed" else "failed"
        
        await self._send_push_notification(
            user_id=user_id,
            title="Payment Update",
            body=f"Payment of ₹{amount} was {status_text}",
            data={"type": "payment", "status": status, "amount": amount}
        )

    async def send_driver_approval_notification(self, driver_id: int, approved: bool):
        """Send driver approval notification."""
        status_text = "approved" if approved else "rejected"
        
        await self._send_push_notification(
            user_id=driver_id,
            title="Driver Application Update",
            body=f"Your driver application has been {status_text}",
            data={"type": "driver_approval", "approved": approved}
        )
        
        # Send email notification
        result = await self.db.execute(select(User).where(User.id == driver_id))
        driver = result.scalars().first()
        
        if driver:
            subject = f"Driver Application {status_text.title()}"
            body = f"""
            Dear {driver.first_name},
            
            Your driver application has been {status_text}.
            
            {f'Reason: {approved}' if not approved else 'You can now start accepting rides!'}
            
            Best regards,
            {settings.PROJECT_NAME} Team
            """
            
            await self._send_email_notification(
                email=driver.email,
                subject=subject,
                body=body
            )

    async def _send_push_notification(self, user_id: int, title: str, body: str, data: Dict[str, Any]):
        """Send push notification to user."""
        # This would integrate with Firebase Cloud Messaging or similar
        # For now, just log the notification
        print(f"Push notification to user {user_id}: {title} - {body}")
        print(f"Data: {data}")

    async def _send_sms_notification(self, user_id: int, message: str):
        """Send SMS notification to user."""
        # Get user phone number
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        
        if user and user.phone:
            # This would integrate with SMS service like Twilio
            print(f"SMS to {user.phone}: {message}")

    async def _send_email_notification(self, email: str, subject: str, body: str):
        """Send email notification."""
        # This would use the email service
        print(f"Email to {email}: {subject}")
        print(f"Body: {body}")

    async def send_emergency_notification(self, user_id: int, emergency_type: str, location: str):
        """Send emergency notification."""
        await self._send_push_notification(
            user_id=user_id,
            title="Emergency Alert",
            body=f"Emergency: {emergency_type} at {location}",
            data={"type": "emergency", "emergency_type": emergency_type, "location": location}
        )
        
        # Also send SMS for critical emergencies
        await self._send_sms_notification(
            user_id=user_id,
            message=f"EMERGENCY: {emergency_type} at {location}. Please contact support immediately."
        ) 