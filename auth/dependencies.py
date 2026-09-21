from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt

from database import get_db
from models import User
from auth.cookies import ACCESS_TOKEN_COOKIE_NAME
from auth.jwt import decode_token

security = HTTPBearer(auto_error=False)

UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


def get_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    access_token: str | None = Cookie(None, alias=ACCESS_TOKEN_COOKIE_NAME),
) -> str | None:
    if credentials is not None:
        return credentials.credentials
    return access_token


def get_current_user(
    token: str | None = Depends(get_access_token),
    db: Session = Depends(get_db),
):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers=UNAUTHORIZED_HEADERS,
        )

    try:
        payload = decode_token(token)
        user_id = payload["user_id"]
    except (jwt.InvalidTokenError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers=UNAUTHORIZED_HEADERS,
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user",
            headers=UNAUTHORIZED_HEADERS,
        )

    return user


def get_current_admin_user(user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user