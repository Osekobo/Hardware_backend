from core.celery import celery
from database import SessionLocal
from models import Order

@celery.task
def retry_failed_payments():

    db = SessionLocal()

    pending_orders = db.query(Order).filter(Order.status == "pending").all()

    for order in pending_orders:
        # re-check logic or re-query M-Pesa API
        pass