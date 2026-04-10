from fastapi import APIRouter, Depends
from database import get_db
from models import Order, AuditLog
from auth.dependencies import get_current_user

router = APIRouter()

# ONLY ADMIN (you can extend roles later)
def is_admin(user):
    return True  # replace later with real role check


@router.get("/orders")
def get_orders(db=Depends(get_db), user=Depends(get_current_user)):
    return db.query(Order).all()


@router.get("/payments")
def payments(db=Depends(get_db), user=Depends(get_current_user)):
    return db.query(Order).filter(Order.status == "paid").all()


@router.get("/logs")
def logs(db=Depends(get_db), user=Depends(get_current_user)):
    return db.query(AuditLog).all()