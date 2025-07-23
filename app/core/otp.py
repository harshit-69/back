import random
import time
from typing import Tuple, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, status

class OTPManager:
    def __init__(self):
        self.OTP_LENGTH = 6
        self.OTP_EXPIRY_MINUTES = 10
        self.MAX_OTP_ATTEMPTS = 3
        self.RESEND_DELAY_SECONDS = 60
        self._otp_attempts = {}
        self._last_sent = {}

    def generate_otp(self, identifier: str) -> Tuple[str, int]:
        """Generate OTP and its expiry timestamp.
        
        Args:
            identifier: User identifier (email or phone)
        
        Returns:
            Tuple containing OTP and its expiry timestamp
        
        Raises:
            HTTPException: If too many attempts or resend too quickly
        """
        current_time = int(time.time())
        
        # Check resend delay
        if identifier in self._last_sent:
            time_since_last = current_time - self._last_sent[identifier]
            if time_since_last < self.RESEND_DELAY_SECONDS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {self.RESEND_DELAY_SECONDS - time_since_last} seconds before requesting new OTP"
                )
        
        # Check attempt limits
        if identifier in self._otp_attempts and self._otp_attempts[identifier] >= self.MAX_OTP_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum OTP attempts reached. Please try again later."
            )
        
        # Generate OTP
        digits = '0123456789'
        otp = ''.join(random.choice(digits) for _ in range(self.OTP_LENGTH))
        valid_until = current_time + (self.OTP_EXPIRY_MINUTES * 60)
        
        # Update tracking
        self._last_sent[identifier] = current_time
        self._otp_attempts[identifier] = self._otp_attempts.get(identifier, 0) + 1
        
        return otp, valid_until

    def verify_otp(self, identifier: str, stored_otp: str, provided_otp: str, valid_until: int) -> bool:
        """Verify if the provided OTP matches and is still valid.
        
        Args:
            identifier: User identifier (email or phone)
            stored_otp: The OTP stored in the database
            provided_otp: The OTP provided by the user
            valid_until: Timestamp until which the OTP is valid
        
        Returns:
            bool: True if OTP is valid and matches, False otherwise
        """
        if not all([stored_otp, provided_otp, valid_until]):
            return False
            
        current_time = int(time.time())
        
        # Check if OTP is expired
        if current_time > valid_until:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one."
            )
        
        # Verify OTP
        is_valid = stored_otp == provided_otp
        
        # Reset attempts on successful verification
        if is_valid and identifier in self._otp_attempts:
            del self._otp_attempts[identifier]
            del self._last_sent[identifier]
        
        return is_valid

    def reset_attempts(self, identifier: str) -> None:
        """Reset OTP attempts for a user.
        
        Args:
            identifier: User identifier (email or phone)
        """
        if identifier in self._otp_attempts:
            del self._otp_attempts[identifier]
        if identifier in self._last_sent:
            del self._last_sent[identifier]

# Create a singleton instance
otp_manager = OTPManager()