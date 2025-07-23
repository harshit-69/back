from app.core.config import settings

async def send_sms(phone_number: str, message: str):
    """Send SMS using SMS service provider."""
    # This would integrate with SMS service like Twilio, AWS SNS, etc.
    # For now, just log the SMS
    print(f"SMS to {phone_number}: {message}")

async def send_otp_sms(phone_number: str, otp: str):
    """Send OTP via SMS."""
    message = f"Your {settings.PROJECT_NAME} OTP is: {otp}. Valid for 10 minutes."
    await send_sms(phone_number, message)

async def send_ride_confirmation_sms(phone_number: str, driver_name: str, vehicle_info: str):
    """Send ride confirmation SMS."""
    message = f"Your ride has been confirmed! Driver: {driver_name}, Vehicle: {vehicle_info}"
    await send_sms(phone_number, message)

async def send_emergency_sms(phone_number: str, emergency_type: str, location: str):
    """Send emergency SMS."""
    message = f"EMERGENCY: {emergency_type} at {location}. Please contact support immediately."
    await send_sms(phone_number, message) 