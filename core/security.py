from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", pbkdf2_sha256__default_rounds=260000)


def hash_password(password: str) -> str:
    """Hash a password - handles any length safely"""
    if not password:
        raise ValueError("Password cannot be empty")
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    if not password or not hashed:
        return False

    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False
