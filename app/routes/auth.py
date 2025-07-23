from dotenv import load_dotenv
import os
load_dotenv()
from app.schemas.user import UserInToken, OTPRequest, OTPVerify, OTPLogin
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import firebase_admin
from firebase_admin import auth, credentials
from app.core.config import settings

from app.database import get_db
from app.schemas.user import UserCreate, UserOut, Token, UserLogin
from app.models.user import User, UserStatus
from app.utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)
from app.core.otp import otp_manager

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Initialize Firebase Admin SDK if not already initialized
try:
    firebase_admin.get_app()
except ValueError:
    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS', None) or os.getenv('FIREBASE_CREDENTIALS')
    print(f"[DEBUG] FIREBASE_CREDENTIALS path: {cred_path}")
    if cred_path and os.path.exists(cred_path):
        print(f"[DEBUG] Firebase credentials file exists at: {cred_path}")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        print(f"[ERROR] FIREBASE_CREDENTIALS not set or file does not exist at: {cred_path}")
        raise RuntimeError("FIREBASE_CREDENTIALS environment variable not set or file does not exist.")

@router.post("/firebase-login", response_model=Token)
async def firebase_login(
    firebase_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user using Firebase ID token."""
    try:
        firebase_token = firebase_data.get("firebase_token")
        email = firebase_data.get("email")
        print(f"[DEBUG] Received firebase_token: {firebase_token[:30]}..." if firebase_token else "[DEBUG] No firebase_token received")
        print(f"[DEBUG] Received email: {email}")
        
        if not firebase_token or not email:
            print(f"[ERROR] Firebase token and email are required")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Firebase token and email are required"
            )
        
        # Verify Firebase ID token
        try:
            decoded_token = auth.verify_id_token(firebase_token)
        except Exception as e:
            print(f"[ERROR] Firebase ID token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token"
            )
        firebase_uid = decoded_token.get("uid")
        print(f"[DEBUG] Decoded Firebase UID: {firebase_uid}")
        
        if not firebase_uid:
            print(f"[ERROR] No UID in decoded Firebase token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token"
            )
        
        # Check if user exists in our database
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        
        if not user:
            # Create new user from Firebase data
            user = User(
                email=email,
                firebase_uid=firebase_uid,
                first_name=decoded_token.get("name", "").split()[0] if decoded_token.get("name") else "",
                last_name=" ".join(decoded_token.get("name", "").split()[1:]) if decoded_token.get("name") and len(decoded_token.get("name", "").split()) > 1 else "",
                is_active=True,
                status=UserStatus.ACTIVE,
                is_verified=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            # Update existing user's Firebase UID if not set
            if not user.firebase_uid:
                user.firebase_uid = firebase_uid
                await db.commit()
        
        # Create JWT token
        access_token = create_access_token(data={"sub": user.email})
        
        # Handle role properly whether it's enum or string
        role_value = user.role.value if hasattr(user.role, 'value') else user.role
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "role": role_value,
                "firebase_uid": firebase_uid
            }
        }
        
    except auth.InvalidIdTokenError:
        print(f"[ERROR] InvalidIdTokenError during Firebase login")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase ID token"
        )
    except Exception as e:
        print(f"[ERROR] Firebase login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(
        select(User).where(
            (User.email == user_data.email) | (User.phone == user_data.phone)
        )
    )
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        phone=user_data.phone,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        hashed_password=hashed_password,
        status=UserStatus.PENDING
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return UserOut.from_orm(db_user)  # Explicit conversion

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    
    # Handle role properly whether it's enum or string
    role_value = user.role.value if hasattr(user.role, 'value') else user.role
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": role_value  # Fixed: works with both enum and string
        }
    }

@router.post("/request-otp")
async def request_otp(request: OTPRequest, db: AsyncSession = Depends(get_db)):
    # Find user
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate OTP
    otp, valid_until = otp_manager.generate_otp(request.email)
    
    # Update user with OTP
    user.otp = otp
    user.otp_valid_until = valid_until
    user.otp_verified = False
    
    await db.commit()
    
    # In production, send OTP via email/SMS
    # For development, return OTP in response
    return {"message": "OTP sent successfully", "otp": otp}  # Remove otp in production

@router.post("/verify-otp")
async def verify_otp(verify_data: OTPVerify, db: AsyncSession = Depends(get_db)):
    # Find user
    result = await db.execute(select(User).where(User.email == verify_data.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify OTP
    if not otp_manager.verify_otp(
        verify_data.email,
        user.otp,
        verify_data.otp,
        user.otp_valid_until
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # Update user
    user.otp_verified = True
    user.otp = None  # Clear OTP after successful verification
    user.otp_valid_until = None
    
    await db.commit()
    
    return {"message": "OTP verified successfully"}

@router.post("/login-with-otp", response_model=Token)
async def login_with_otp(login_data: OTPLogin, db: AsyncSession = Depends(get_db)):
    # Find user
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify OTP
    if not otp_manager.verify_otp(
        login_data.email,
        user.otp,
        login_data.otp,
        user.otp_valid_until
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    # Update user
    user.otp_verified = True
    user.otp = None  # Clear OTP after successful login
    user.otp_valid_until = None
    user.last_login = datetime.utcnow()
    
    await db.commit()
    
    # Handle role properly whether it's enum or string
    role_value = user.role.value if hasattr(user.role, 'value') else user.role
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": role_value
        }
    }

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    print(f"User accessing /me: {current_user.email}")  # Add this line
    return current_user

@router.post("/verify-token", response_model=UserOut)
async def verify_token(current_user: User = Depends(get_current_user)):
    return current_user