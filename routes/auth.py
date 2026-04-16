from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth.jwt import create_token
from core.security import hash_password, verify_password
from pydantic import BaseModel, EmailStr
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

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
        
        logger.info(f"User registered: {data.email}")
        return {"message": "registered successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
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