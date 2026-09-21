from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
import string
import logging
from database import get_db
from models import User, Order, OrderItem, PasswordResetOTP
from auth.jwt import create_token
from auth.cookies import set_access_token_cookie, clear_access_token_cookie
from core.security import hash_password, verify_password
from utils.email import send_reset_email
from pydantic import BaseModel, EmailStr
import os
import secrets
from auth.dependencies import get_current_admin_user, get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

class AdminCreate(UserCreate):
    pass

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

@router.post("/register")
def register(data: UserCreate, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(User).filter(User.email == data.email).first()
        if existing_user:
            raise HTTPException(400, "Email already registered")

        user = User(
            name=data.name,
            email=data.email,
            phone=data.phone,
            password=hash_password(data.password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_token({
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone or ""
        })

        logger.info(f"User registered: {data.email}")

        response = JSONResponse(content={
            "message": "registered successfully",
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone or ""
            }
        })
        set_access_token_cookie(response, token)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        db.rollback()
        raise HTTPException(500, f"Registration failed: {str(e)}")

@router.post("/register-admin")
def register_admin(
    data: AdminCreate,
    registration_key: str = Header(..., alias="X-Admin-Registration-Key"),
    db: Session = Depends(get_db)
):
    configured_key = os.getenv("ADMIN_REGISTRATION_KEY", "")
    if not configured_key or not secrets.compare_digest(registration_key, configured_key):
        raise HTTPException(403, "Invalid admin registration key")

    if db.query(User).filter(User.is_admin.is_(True)).first():
        raise HTTPException(409, "An administrator already exists; use POST /auth/admins")

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password=hash_password(data.password),
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token({
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone or "",
    })
    return {
        "message": "admin registered successfully",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone or "",
            "is_admin": True,
        },
    }

@router.post("/admins")
def create_admin(
    data: AdminCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password=hash_password(data.password),
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "message": "admin created successfully",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_admin": True,
        },
    }

@router.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == data.email).first()

        if not user:
            logger.warning(f"Login failed: User not found - {data.email}")
            raise HTTPException(401, "Invalid email or password")

        if not verify_password(data.password, user.password):
            logger.warning(f"Login failed: Wrong password - {data.email}")
            raise HTTPException(401, "Invalid email or password")

        token = create_token({
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone or ""
        })

        logger.info(f"User logged in: {data.email}")
        
        response = JSONResponse(content={
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone or ""
            }
        })
        set_access_token_cookie(response, token)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(500, f"Login failed: {str(e)}")

@router.post("/logout")
def logout(response: Response):
    clear_access_token_cookie(response)
    logger.info("User logged out")
    return {"message": "logged out successfully"}


@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    orders = db.query(Order).filter(Order.user_id == current_user.id).all()

    active_statuses = {"pending", "paid", "shipped"}
    purchased_statuses = {"paid", "shipped", "delivered"}

    total_orders = 0
    items_purchased = 0
    active_orders = 0
    for order in orders:
        total_orders += 1
        status = order.status.value if hasattr(order.status, "value") else order.status
        if status in purchased_statuses:
            items_purchased += sum(item.quantity for item in order.items)
        if status in active_statuses:
            active_orders += 1

    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone or "",
        "is_admin": current_user.is_admin,
        "created_at": current_user.created_at,
        "total_orders": total_orders,
        "items_purchased": items_purchased,
        "active_orders": active_orders,
    }


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        return {"success": True, "message": "If email exists, reset code has been sent"}
    
    otp = generate_otp()
    
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    db.query(PasswordResetOTP).filter(
        PasswordResetOTP.email == request.email,
        PasswordResetOTP.is_used == False
    ).delete()
    
    otp_record = PasswordResetOTP(
        email=request.email,
        otp=otp,
        expires_at=expires_at
    )
    db.add(otp_record)
    db.commit()
    
    background_tasks.add_task(send_reset_email, request.email, otp)
    
    return {"success": True, "message": "Reset code sent to your email"}

@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    otp_record = db.query(PasswordResetOTP).filter(
        PasswordResetOTP.email == request.email,
        PasswordResetOTP.otp == request.otp,
        PasswordResetOTP.is_used == False,
        PasswordResetOTP.expires_at > datetime.utcnow()
    ).first()
    
    if not otp_record:
        raise HTTPException(400, "Invalid or expired reset code")
    
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    user.password = hash_password(request.new_password)
    
    otp_record.is_used = True
    
    db.commit()
    
    return {"success": True, "message": "Password reset successfully"}