import requests
import base64
from datetime import datetime

CONSUMER_KEY = "key"
CONSUMER_SECRET = "secret"
SHORTCODE = "174379"
PASSKEY = "passkey"


def get_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return r.json()["access_token"]


def stk_push(phone, amount, order_id):
    token = get_token()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password = base64.b64encode(
        (SHORTCODE + PASSKEY + timestamp).encode()
    ).decode()

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": "https://yourdomain.com/mpesa/callback",
        "AccountReference": str(order_id),
        "TransactionDesc": "Order Payment"
    }

    headers = {"Authorization": f"Bearer {token}"}

    return requests.post(url, json=payload, headers=headers).json()