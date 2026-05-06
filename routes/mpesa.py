# routes/mpesa.py
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import base64
import math
import os
from sqlalchemy.orm import Session
from database import get_db
from models import Order, User
from auth.dependencies import get_current_user

router = APIRouter()

# M-Pesa Configuration
CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "kIM7nhs5kDq6YfzbN15kl2LMOX7zlEZ8lZAiA2lM9I0SKcIe")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "cOByOXYGzn7CAQtjNWTZH71XwKV9c777ssXbaJbrmngzUMAkLY2uNkGvaLW4qU5o")
SHORT_CODE = os.getenv("MPESA_SHORTCODE", "174379")
PASS_KEY = os.getenv("MPESA_PASSKEY", "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919")
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "https://your-backend-url.com/mpesa/callback")

# API URLs
SAF_API_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
SAF_STK_PUSH_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

class MpesaPaymentRequest(BaseModel):
    amount: float
    phone_number: str
    order_id: int

def get_mpesa_access_token():
    """Get M-Pesa access token"""
    try:
        response = requests.get(
            SAF_API_URL,
            auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET),
        )
        response.raise_for_status()
        token = response.json().get('access_token')
        if not token:
            raise HTTPException(500, "Failed to get access token")
        return token
    except Exception as e:
        raise HTTPException(500, f"M-Pesa authentication failed: {str(e)}")

def generate_password(short_code, pass_key, timestamp):
    """Generate password for STK push"""
    password_str = short_code + pass_key + timestamp
    password_bytes = password_str.encode('utf-8')
    return base64.b64encode(password_bytes).decode('utf-8')

@router.post("/stkpush")
async def initiate_payment(
    payment: MpesaPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initiate M-Pesa STK Push payment"""
    # Get order
    order = db.query(Order).filter(
        Order.id == payment.order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(404, "Order not found")
    
    # Verify amount matches order total
    if abs(order.total - payment.amount) > 0.01:
        raise HTTPException(400, "Amount does not match order total")
    
    # Format phone number
    phone_number = payment.phone_number.strip()
    if phone_number.startswith('0'):
        phone_number = '254' + phone_number[1:]
    elif phone_number.startswith('+'):
        phone_number = phone_number[1:]
    
    # Get access token
    access_token = get_mpesa_access_token()
    
    # Generate timestamp and password
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = generate_password(SHORT_CODE, PASS_KEY, timestamp)
    
    # Prepare STK push data
    stk_data = {
        "BusinessShortCode": SHORT_CODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(math.ceil(payment.amount)),
        "PartyA": phone_number,
        "PartyB": SHORT_CODE,
        "PhoneNumber": phone_number,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": f"ORDER{payment.order_id}",
        "TransactionDesc": f"Payment for Order #{payment.order_id}"
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Make STK push request
    response = requests.post(
        SAF_STK_PUSH_URL,
        json=stk_data,
        headers=headers
    )
    
    response_data = response.json()
    
    # Update order with M-Pesa request ID
    if response_data.get('ResponseCode') == '0':
        order.mpesa_checkout_request_id = response_data.get('CheckoutRequestID')
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
    """Handle M-Pesa callback after payment"""
    try:
        callback_data = await request.json()
        
        # Extract callback data
        body = callback_data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        
        # Find order by checkout request ID
        order = db.query(Order).filter(
            Order.mpesa_checkout_request_id == checkout_request_id
        ).first()
        
        if not order:
            return {"ResultCode": 1, "ResultDesc": "Order not found"}
        
        if result_code == 0:  # Payment successful
            # Extract payment details
            callback_metadata = stk_callback.get('CallbackMetadata', {})
            items = callback_metadata.get('Item', [])
            
            mpesa_receipt = None
            for item in items:
                if item.get('Name') == 'MpesaReceiptNumber':
                    mpesa_receipt = item.get('Value')
                    break
            
            # Update order status
            order.status = 'paid'
            order.mpesa_receipt = mpesa_receipt
            order.paid_at = datetime.now()
            db.commit()
            
            return {"ResultCode": 0, "ResultDesc": "Success"}
        else:  # Payment failed
            order.status = 'payment_failed'
            order.payment_error = result_desc
            db.commit()
            
            return {"ResultCode": result_code, "ResultDesc": result_desc}
            
    except Exception as e:
        print(f"Callback error: {e}")
        return {"ResultCode": 1, "ResultDesc": f"Processing error: {str(e)}"}

@router.get("/status/{checkout_request_id}")
async def check_payment_status(
    checkout_request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check payment status for a checkout request"""
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