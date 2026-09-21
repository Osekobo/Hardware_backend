import os
import jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("SECRET_KEY", "local-development-secret-change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

def create_token(data: dict, expires: int = None) -> str:
    payload = data.copy()
    expire_minutes = expires if expires is not None else ACCESS_TOKEN_EXPIRE_MINUTES
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expire_minutes)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

def is_token_expired(token: str) -> bool:
    try:
        payload = decode_token(token)
        exp = payload.get("exp")
        if exp:
            return datetime.utcnow() > datetime.fromtimestamp(exp)
        return True
    except jwt.InvalidTokenError:
        return True