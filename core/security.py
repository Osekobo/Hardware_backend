from passlib.context import CryptContext
import logging

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False
    
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False