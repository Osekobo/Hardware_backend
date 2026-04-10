from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth.jwt import decode_token

security = HTTPBearer()

def get_current_user(
    credentials=Depends(security),
    db: Session = Depends(get_db)
):
    try:
        token = credentials.credentials
        payload = decode_token(token)

        user = db.query(User).filter(User.id == payload["user_id"]).first()

        if not user:
            raise HTTPException(401, "Invalid user")

        return user

    except:
        raise HTTPException(401, "Invalid token")