import asyncio
import threading
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import get_current_admin_user, get_current_user
from database import get_db
from models import Order, OrderItem, Product, Cart, User
from utils.stock import restore_stock

router = APIRouter()

AUTO_CANCEL_MINUTES = 15


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    price: float = None


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    total: float = None


class OrderStatusUpdate(BaseModel):
    status: str


def auto_cancel_pending_order(order_id: int, timeout_minutes: int = AUTO_CANCEL_MINUTES):
    async def cancel_order():
        await asyncio.sleep(timeout_minutes * 60)

        from database import SessionLocal
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order and order.status == 'pending':
                order.status = 'cancelled'
                order.payment_error = f"Order automatically cancelled after {timeout_minutes} minutes (payment timeout)"
                restore_stock(order, db)
                db.commit()
                print(f"⏰ Order #{order_id} auto-cancelled due to timeout")
        except Exception as e:
            print(f"Error auto-cancelling order {order_id}: {e}")
        finally:
            db.close()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(cancel_order())
    loop.close()


def schedule_auto_cancel(order_id: int):
    thread = threading.Thread(target=auto_cancel_pending_order, args=(order_id, AUTO_CANCEL_MINUTES))
    thread.daemon = True
    thread.start()
    print(f"✅ Order #{order_id} created with auto-cancel scheduled in {AUTO_CANCEL_MINUTES} minutes")


@router.post("/create")
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not order_data.items:
        raise HTTPException(400, "Order must have at least one item")

    try:
        products = {}
        total = 0.0
        for item in order_data.items:
            if item.quantity <= 0:
                raise HTTPException(400, f"Invalid quantity for product {item.product_id}")

            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                raise HTTPException(404, f"Product {item.product_id} not found")
            if product.stock < item.quantity:
                raise HTTPException(400, f"Insufficient stock for {product.name}")

            products[item.product_id] = product
            total += product.price * item.quantity

        order = Order(
            user_id=current_user.id,
            total=total,
            status="pending"
        )
        db.add(order)
        db.flush()

        for item in order_data.items:
            product = products[item.product_id]
            product.stock -= item.quantity
            db.add(OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=product.price
            ))

        db.commit()
        db.refresh(order)

        schedule_auto_cancel(order.id)

        return {
            "success": True,
            "order_id": order.id,
            "total": order.total,
            "status": order.status
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Order creation error: {e}")
        raise HTTPException(500, f"Failed to create order: {str(e)}")


@router.post("/checkout")
def checkout(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cart = db.query(Cart).filter(Cart.user_id == user.id).all()

    if not cart:
        raise HTTPException(400, "Empty cart")

    order = Order(user_id=user.id, total=0, status="pending")
    db.add(order)
    db.flush()

    total = 0

    for item in cart:
        product = db.query(Product).filter(Product.id == item.product_id).first()

        if not product:
            raise HTTPException(404, f"Product {item.product_id} not found")

        if product.stock < item.quantity:
            raise HTTPException(400, f"Insufficient stock for {product.name}")

        product.stock -= item.quantity
        total += product.price * item.quantity

        db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=item.quantity,
            price=product.price
        ))

        db.delete(item)

    order.total = total
    db.commit()

    schedule_auto_cancel(order.id)

    return {"order_id": order.id, "total": total, "status": "pending"}


@router.get("/")
def get_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    orders = db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.created_at.desc()).all()

    result = []
    for order in orders:
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        result.append({
            "id": order.id,
            "user_id": order.user_id,
            "total": order.total,
            "status": order.status,
            "created_at": order.created_at,
            "paid_at": order.paid_at,
            "mpesa_receipt": order.mpesa_receipt,
            "payment_error": order.payment_error,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price": item.price,
                    "product_name": _get_product_name(db, item.product_id)
                }
                for item in items
            ]
        })

    return result


@router.get("/admin/all")
def get_all_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    orders = db.query(Order).order_by(Order.created_at.desc()).all()

    result = []
    for order in orders:
        user = db.query(User).filter(User.id == order.user_id).first()
        items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        result.append({
            "id": order.id,
            "user_id": order.user_id,
            "user_name": user.name if user else None,
            "user_email": user.email if user else None,
            "total": order.total,
            "status": order.status,
            "created_at": order.created_at,
            "paid_at": order.paid_at,
            "mpesa_receipt": order.mpesa_receipt,
            "payment_error": order.payment_error,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price": item.price
                }
                for item in items
            ]
        })

    return result


@router.get("/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(404, "Order not found")

    if order.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()

    return {
        "id": order.id,
        "user_id": order.user_id,
        "total": order.total,
        "status": order.status,
        "created_at": order.created_at,
        "paid_at": order.paid_at,
        "mpesa_receipt": order.mpesa_receipt,
        "payment_error": order.payment_error,
        "items": [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.price,
                "product_name": _get_product_name(db, item.product_id)
            }
            for item in items
        ]
    }


@router.put("/{order_id}/status")
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    valid_statuses = {'pending', 'paid', 'shipped', 'delivered', 'cancelled', 'payment_failed'}
    if status_data.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status: {status_data.status}")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    order.status = status_data.status
    db.commit()

    return {"message": "Order status updated", "status": order.status}


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(404, "Order not found")

    if order.status != 'pending':
        raise HTTPException(400, f"Cannot cancel order with status: {order.status}")

    order.status = 'cancelled'
    order.payment_error = "User cancelled the order"
    restore_stock(order, db)
    db.commit()

    return {"message": "Order cancelled successfully", "order_id": order_id, "status": "cancelled"}


@router.post("/{order_id}/retry-payment")
def retry_payment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    old_order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not old_order:
        raise HTTPException(404, "Order not found")

    if old_order.status not in ['cancelled', 'payment_failed']:
        raise HTTPException(400, f"Cannot retry payment for order with status: {old_order.status}")

    old_items = db.query(OrderItem).filter(OrderItem.order_id == old_order.id).all()

    if not old_items:
        raise HTTPException(400, "Order has no items")

    new_items = []
    total = 0.0
    for item in old_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(404, f"Product {item.product_id} not found")
        if product.stock < item.quantity:
            raise HTTPException(400, f"Insufficient stock for {product.name}")
        new_items.append((product, item))
        total += product.price * item.quantity

    new_order = Order(
        user_id=current_user.id,
        total=total,
        status="pending"
    )
    db.add(new_order)
    db.flush()

    for product, item in new_items:
        product.stock -= item.quantity
        db.add(OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price
        ))

    db.commit()
    db.refresh(new_order)

    schedule_auto_cancel(new_order.id)

    print(f"🔄 Retry payment for order #{order_id} -> New order #{new_order.id}")

    return {
        "message": "Retry order created",
        "old_order_id": order_id,
        "new_order_id": new_order.id,
        "total": new_order.total
    }


@router.post("/cleanup-pending")
def cleanup_pending_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    cutoff_time = datetime.utcnow() - timedelta(minutes=AUTO_CANCEL_MINUTES)

    old_pending_orders = db.query(Order).filter(
        Order.status == 'pending',
        Order.created_at < cutoff_time
    ).all()

    cancelled_count = 0
    for order in old_pending_orders:
        order.status = 'cancelled'
        order.payment_error = f"Order automatically cancelled after {AUTO_CANCEL_MINUTES} minutes (payment timeout)"
        restore_stock(order, db)
        cancelled_count += 1

    db.commit()

    print(f"🧹 Cleaned up {cancelled_count} expired pending orders")

    return {
        "message": f"Cancelled {cancelled_count} expired pending orders",
        "cancelled": cancelled_count
    }


@router.post("/{order_id}/confirm-payment")
def confirm_payment(
    order_id: int,
    mpesa_receipt: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(404, "Order not found")

    if order.user_id != current_user.id:
        raise HTTPException(403, "Access denied")

    if order.status != 'pending':
        raise HTTPException(400, f"Cannot confirm payment for order with status: {order.status}")

    order.status = "paid"
    order.mpesa_receipt = mpesa_receipt
    order.paid_at = datetime.utcnow()
    db.commit()

    return {"message": "Payment confirmed", "order_id": order_id, "status": "paid"}


def _get_product_name(db: Session, product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()
    return product.name if product else None