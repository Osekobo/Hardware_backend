import base64
import json
import logging
import math
import os
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from requests.auth import HTTPBasicAuth
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import Order, User
from utils.stock import restore_stock

router = APIRouter()
logger = logging.getLogger(__name__)

CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
SHORT_CODE = os.getenv("MPESA_SHORTCODE", "")
PASS_KEY = os.getenv("MPESA_PASSKEY", "")
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "")

MPESA_API_BASE_URL = os.getenv("MPESA_API_BASE_URL", "https://sandbox.safaricom.co.ke").rstrip("/")
SAF_API_URL = f"{MPESA_API_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
SAF_STK_PUSH_URL = f"{MPESA_API_BASE_URL}/mpesa/stkpush/v1/processrequest"


class MpesaPaymentRequest(BaseModel):
    amount: float
    phone_number: str
    order_id: int


def normalize_phone_number(phone: str) -> str:
    if not phone:
        raise HTTPException(400, "Phone number is required")

    phone = re.sub(r"[\s\-\(\)]", "", phone.strip())

    if phone.startswith("+"):
        phone = phone[1:]

    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("254") and len(phone) == 12:
        pass
    elif phone.startswith("7") or phone.startswith("1"):
        phone = "254" + phone
    else:
        raise HTTPException(400, "Invalid phone number format")

    if not re.fullmatch(r"254[17]\d{8}", phone):
        raise HTTPException(400, "Invalid Kenyan phone number")

    return phone


def ensure_mpesa_configured():
    missing = [
        name
        for name, value in (
            ("MPESA_CONSUMER_KEY", CONSUMER_KEY),
            ("MPESA_CONSUMER_SECRET", CONSUMER_SECRET),
            ("MPESA_SHORTCODE", SHORT_CODE),
            ("MPESA_PASSKEY", PASS_KEY),
            ("MPESA_CALLBACK_URL", CALLBACK_URL),
        )
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"M-Pesa is not configured. Missing: {', '.join(missing)}",
        )


def get_mpesa_access_token():
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        raise HTTPException(503, "M-Pesa credentials are not configured")

    try:
        response = requests.get(
            SAF_API_URL,
            auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET),
            timeout=10,
        )
        response.raise_for_status()
        token = response.json().get('access_token')
        if not token:
            raise HTTPException(500, "Failed to get access token")
        return token
    except HTTPException:
        raise
    except requests.exceptions.RequestException as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        body = getattr(getattr(e, "response", None), "text", None)
        logger.error(f"M-Pesa authentication failed: {e}")
        raise HTTPException(500, f"M-Pesa authentication failed (HTTP {status}): {body or e}")
    except Exception as e:
        logger.error(f"M-Pesa authentication failed: {e}")
        raise HTTPException(500, "M-Pesa authentication failed")


def generate_password(short_code, pass_key, timestamp):
    password_str = short_code + pass_key + timestamp
    password_bytes = password_str.encode('utf-8')
    return base64.b64encode(password_bytes).decode('utf-8')


@router.post("/stkpush")
async def initiate_payment(
    payment: MpesaPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ensure_mpesa_configured()

    order = db.query(Order).filter(
        Order.id == payment.order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(404, "Order not found")

    if order.status == 'paid':
        raise HTTPException(400, "Order is already paid")

    if order.status != 'pending':
        raise HTTPException(400, f"Cannot request payment for order with status: {order.status}")

    order_total = float(order.total) if isinstance(order.total, Decimal) else order.total
    payment_amount = float(payment.amount)

    if abs(order_total - payment_amount) > 0.01:
        raise HTTPException(400, f"Amount does not match order total. Expected: {order_total}, Got: {payment_amount}")

    phone_number = normalize_phone_number(payment.phone_number)

    access_token = get_mpesa_access_token()

    # FIX 1: Generate timestamp in East Africa Time (UTC+3)
    eat_tz = timezone(timedelta(hours=3))
    timestamp = datetime.now(eat_tz).strftime("%Y%m%d%H%M%S")
    
    password = generate_password(SHORT_CODE, PASS_KEY, timestamp)

    stk_data = {
        "BusinessShortCode": SHORT_CODE,
        "Password": password,
        "Timestamp": timestamp, # This MUST match the timestamp used for the password
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(math.ceil(payment_amount)),
        "PartyA": phone_number,
        "PartyB": SHORT_CODE,
        "PhoneNumber": phone_number,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": f"ORDER{order.id}",
        "TransactionDesc": f"Payment for Order #{order.id}"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(SAF_STK_PUSH_URL, json=stk_data, headers=headers, timeout=15)
        response.raise_for_status()
        response_data = response.json()
    # FIX 2: Catch HTTP errors specifically to log Safaricom's exact response
    except requests.exceptions.HTTPError as e:
        error_details = e.response.text
        logger.error(f"Safaricom API Error: {e.response.status_code} - {error_details}")
        raise HTTPException(502, f"M-Pesa API Error: {error_details}")
    except Exception as e:
        logger.error(f"STK push request failed: {e}")
        raise HTTPException(502, "Failed to reach M-Pesa API")

    if response_data.get('ResponseCode') == '0':
        order.mpesa_checkout_request_id = response_data.get('CheckoutRequestID')
        order.payment_error = None
        db.commit()

        return {
            "success": True,
            "message": "STK push sent successfully",
            "checkout_request_id": response_data.get('CheckoutRequestID'),
            "response_code": response_data.get('ResponseCode'),
            "response_description": response_data.get('ResponseDescription')
        }
    else:
        return {
            "success": False,
            "message": response_data.get('ResponseDescription', 'STK push failed'),
            "response_code": response_data.get('ResponseCode'),
            "response_description": response_data.get('ResponseDescription')
        }


@router.post("/callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    allowed_ips = [ip.strip() for ip in os.getenv("MPESA_ALLOWED_IPS", "").split(",") if ip.strip()]
    if allowed_ips:
        forwarded = request.headers.get("x-forwarded-for")
        client_ip = (forwarded.split(",")[0].strip() if forwarded else request.client.host) if request.client else None
        if client_ip not in allowed_ips:
            logger.warning(f"Rejected M-Pesa callback from unauthorized IP: {client_ip}")
            raise HTTPException(403, "Forbidden")

    try:
        raw_body = await request.body()
        if not raw_body:
            return {"ResultCode": 1, "ResultDesc": "Empty payload"}

        callback_data = json.loads(raw_body)

        body = callback_data.get('Body', {})
        stk_callback = body.get('stkCallback', {})

        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        checkout_request_id = stk_callback.get('CheckoutRequestID')

        if not checkout_request_id:
            return {"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID"}

        order = db.query(Order).filter(
            Order.mpesa_checkout_request_id == checkout_request_id
        ).first()

        if not order:
            return {"ResultCode": 1, "ResultDesc": "Order not found"}

        if order.status == 'paid':
            return {"ResultCode": 0, "ResultDesc": "Success"}

        callback_metadata = stk_callback.get('CallbackMetadata', {}) or {}
        items = callback_metadata.get('Item', []) or []
        metadata = {item.get('Name'): item.get('Value') for item in items if isinstance(item, dict)}

        if result_code == 0:
            mpesa_receipt = metadata.get('MpesaReceiptNumber')
            amount_paid = metadata.get('Amount')

            order_total = float(order.total) if isinstance(order.total, Decimal) else order.total
            if amount_paid is None or abs(float(amount_paid) - order_total) > 0.01:
                order.status = 'payment_failed'
                order.payment_error = f"Amount mismatch: expected {order_total}, received {amount_paid}"
                db.commit()
                restore_stock(order, db)
                return {"ResultCode": 1, "ResultDesc": "Amount mismatch"}

            if mpesa_receipt:
                existing = db.query(Order).filter(
                    Order.mpesa_receipt == mpesa_receipt,
                    Order.id != order.id
                ).first()
                if existing:
                    order.status = 'payment_failed'
                    order.payment_error = "Duplicate M-Pesa receipt detected"
                    db.commit()
                    restore_stock(order, db)
                    return {"ResultCode": 1, "ResultDesc": "Duplicate receipt"}

            order.status = 'paid'
            order.mpesa_receipt = mpesa_receipt
            order.paid_at = datetime.now()
            order.payment_error = None
            db.commit()

            logger.info(f"Order #{order.id} marked as paid (receipt {mpesa_receipt})")

            return {"ResultCode": 0, "ResultDesc": "Success"}
        else:
            order.status = 'payment_failed'
            order.payment_error = result_desc
            db.commit()
            restore_stock(order, db)

            return {"ResultCode": result_code, "ResultDesc": result_desc}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("M-Pesa callback error")
        return {"ResultCode": 1, "ResultDesc": "Processing error"}


@router.get("/status/{checkout_request_id}")
async def check_payment_status(
    checkout_request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(
        Order.mpesa_checkout_request_id == checkout_request_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(404, "Order not found")

    return {
        "order_id": order.id,
        "status": order.status,
        "paid_at": order.paid_at,
        "mpesa_receipt": order.mpesa_receipt
    }