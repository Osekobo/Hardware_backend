from core.celery import celery
from database import SessionLocal
from models import Order
from utils.audit import log_event
from services.notifications import send_email, send_sms
from services.fraud import run_fraud_checks

@celery.task
def process_mpesa_callback(data):

    db = SessionLocal()

    result = data["Body"]["stkCallback"]

    if result["ResultCode"] != 0:
        log_event("payment_failed", data)
        return

    metadata = result["CallbackMetadata"]["Item"]

    receipt = next(i["Value"] for i in metadata if i["Name"] == "MpesaReceiptNumber")
    amount = next(i["Value"] for i in metadata if i["Name"] == "Amount")
    order_id = result["AccountReference"]

    order = db.query(Order).filter(Order.id == order_id).first()

    # FRAUD CHECK
    if not run_fraud_checks(order, amount, receipt):
        log_event("fraud_blocked", data)
        return

    order.status = "paid"
    order.mpesa_receipt = receipt

    db.commit()

    log_event("payment_success", data)

    send_email(order.user.email, "Payment Received", "Thank you!")
    send_sms(order.user.phone, "Payment successful")