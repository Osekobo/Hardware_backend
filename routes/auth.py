# routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import string
import logging
from database import get_db
from models import User, PasswordResetOTP
from auth.jwt import create_token
from core.security import hash_password, verify_password
from utils.email import send_reset_email
from pydantic import BaseModel, EmailStr

router = APIRouter()
logger = logging.getLogger(__name__)

# ========== Pydantic Models ==========
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

# ========== Helper Functions ==========
def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

# ========== Authentication Routes ==========
@router.post("/register")
def register(data: UserCreate, db: Session = Depends(get_db)):
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.email == data.email).first()
        if existing_user:
            raise HTTPException(400, "Email already registered")

        # Create new user
        user = User(
            name=data.name,
            email=data.email,
            password=hash_password(data.password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create token immediately
        token = create_token({
            "user_id": user.id,
            "name": user.name,
            "email": user.email
        })

        logger.info(f"User registered: {data.email}")

        # Return token with registration response
        return {
            "message": "registered successfully",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        db.rollback()
        raise HTTPException(500, f"Registration failed: {str(e)}")

@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    try:
        # Find user
        user = db.query(User).filter(User.email == data.email).first()

        if not user:
            logger.warning(f"Login failed: User not found - {data.email}")
            raise HTTPException(401, "Invalid email or password")

        # Verify password
        if not verify_password(data.password, user.password):
            logger.warning(f"Login failed: Wrong password - {data.email}")
            raise HTTPException(401, "Invalid email or password")

        # Create token
        token = create_token({
            "user_id": user.id,
            "name": user.name,
            "email": user.email
        })

        logger.info(f"User logged in: {data.email}")
        return {"access_token": token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(500, f"Login failed: {str(e)}")

# ========== Password Reset Routes ==========
@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request password reset - sends OTP to user's email
    """
    # Check if user exists
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # For security, don't reveal that email doesn't exist
        return {"success": True, "message": "If email exists, reset code has been sent"}
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP in database
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Delete any existing unused OTPs for this email
    db.query(PasswordResetOTP).filter(
        PasswordResetOTP.email == request.email,
        PasswordResetOTP.is_used == False
    ).delete()
    
    # Create new OTP record
    otp_record = PasswordResetOTP(
        email=request.email,
        otp=otp,
        expires_at=expires_at
    )
    db.add(otp_record)
    db.commit()
    
    # Send email in background
    background_tasks.add_task(send_reset_email, request.email, otp)
    
    return {"success": True, "message": "Reset code sent to your email"}

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using OTP verification
    """
    # Find valid OTP
    otp_record = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.email == request.email,
        PasswordResetOTP.otp == request.otp,
        PasswordResetOTP.is_used == False,
        PasswordResetOTP.expires_at > datetime.utcnow()
    ).first()
    
    if not otp_record:
        raise HTTPException(400, "Invalid or expired reset code")
    
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    # Update password
    user.password = hash_password(request.new_password)
    
    # Mark OTP as used
    otp_record.is_used = True
    
    db.commit()
    
    return {"success": True, "message": "Password reset successfully"}