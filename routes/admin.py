from fastapi import APIRouter, Depends
from database import get_db
from models import Order, AuditLog
from auth.dependencies import get_current_admin_user

router = APIRouter()

@router.get("/orders")
def get_orders(db=Depends(get_db), user=Depends(get_current_admin_user)):
    return db.query(Order).all()


@router.get("/payments")
def payments(db=Depends(get_db), user=Depends(get_current_admin_user)):
    return db.query(Order).filter(Order.status == "paid").all()


@router.get("/logs")
def logs(db=Depends(get_db), user=Depends(get_current_admin_user)):
    return db.query(AuditLog).all()