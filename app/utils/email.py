import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

async def send_email(to_email: str, subject: str, body: str, html_body: str = None):
    """Send email using SMTP."""
    if not all([settings.MAIL_USERNAME, settings.MAIL_PASSWORD, settings.MAIL_FROM]):
        print(f"Email configuration incomplete. Would send to {to_email}: {subject}")
        return
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings.MAIL_FROM
        msg['To'] = to_email
        
        # Add text and HTML parts
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)
        
        if html_body:
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)
            
        print(f"Email sent successfully to {to_email}")
        
    except Exception as e:
        print(f"Failed to send email to {to_email}: {str(e)}")

async def send_welcome_email(email: str, first_name: str):
    """Send welcome email to new users."""
    subject = f"Welcome to {settings.PROJECT_NAME}!"
    body = f"""
    Dear {first_name},
    
    Welcome to {settings.PROJECT_NAME}! We're excited to have you on board.
    
    You can now:
    - Book rides easily
    - Track your rides in real-time
    - Manage your payments securely
    
    If you have any questions, feel free to contact our support team.
    
    Best regards,
    {settings.PROJECT_NAME} Team
    """
    
    await send_email(email, subject, body)

async def send_verification_email(email: str, verification_code: str):
    """Send email verification code."""
    subject = f"Verify your {settings.PROJECT_NAME} account"
    body = f"""
    Hello,
    
    Please use the following verification code to complete your account setup:
    
    Verification Code: {verification_code}
    
    This code will expire in 10 minutes.
    
    If you didn't request this code, please ignore this email.
    
    Best regards,
    {settings.PROJECT_NAME} Team
    """
    
    await send_email(email, subject, body)

async def send_password_reset_email(email: str, reset_token: str):
    """Send password reset email."""
    subject = f"Reset your {settings.PROJECT_NAME} password"
    body = f"""
    Hello,
    
    You requested a password reset for your {settings.PROJECT_NAME} account.
    
    Click the following link to reset your password:
    {settings.PROJECT_NAME}/reset-password?token={reset_token}
    
    This link will expire in 1 hour.
    
    If you didn't request this reset, please ignore this email.
    
    Best regards,
    {settings.PROJECT_NAME} Team
    """
    
    await send_email(email, subject, body)