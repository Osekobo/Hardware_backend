from sqlalchemy.orm import Session
import hmac
from models import Order
import hashlib
from fastapi import Request, HTTPException

SAFARICOM_IPS = [
    "196.201.214.200",
    "196.201.214.206",
    "196.201.213.114"
]


def verify_ip(request: Request):
    ip = request.client.host

    if ip not in SAFARICOM_IPS:
        raise HTTPException(403, "Invalid IP")


MPESA_SECRET = "your_shared_secret"


def verify_signature(raw_body: str, signature: str):
    computed = hmac.new(
        MPESA_SECRET.encode(),
        raw_body.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


def is_duplicate_receipt(db: Session, receipt: str):
    return db.query(Order).filter(Order.mpesa_receipt == receipt).first()
