from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth.jwt import create_token
from core.security import hash_password, verify_password

router = APIRouter()

@router.post("/register")
def register(data, db: Session = Depends(get_db)):
    user = User(
        name=data.name,
        email=data.email,
        password=hash_password(data.password)
    )
    db.add(user)
    db.commit()
    return {"message": "registered"}


@router.post("/login")
def login(data, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password):
        raise HTTPException(401)

    token = create_token({"user_id": user.id})
    return {"access_token": token}