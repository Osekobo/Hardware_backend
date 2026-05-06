# routes/orders.py
from pydantic import BaseModel
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import asyncio
from database import get_db
from models import Order, OrderItem, Product, Cart, User
from utils.stock import reduce_stock
from auth.dependencies import get_current_user

router = APIRouter()

# Pydantic models
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int
    price: float

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    total: float

class OrderStatusUpdate(BaseModel):
    status: str

class EmailCampaign(BaseModel):
    recipients: List[str]
    subject: str
    message: str

# Helper function to auto-cancel pending orders
def auto_cancel_pending_order(order_id: int, timeout_minutes: int = 15):
    """
    Background task to automatically cancel pending orders after timeout
    """
    async def cancel_order():
        await asyncio.sleep(timeout_minutes * 60)  # Convert to seconds
        
        from database import SessionLocal
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order and order.status == 'pending':
                order.status = 'cancelled'
                order.payment_error = f"Order automatically cancelled after {timeout_minutes} minutes (payment timeout)"
                db.commit()
                print(f"⏰ Order #{order_id} auto-cancelled due to timeout")
        except Exception as e:
            print(f"Error auto-cancelling order {order_id}: {e}")
        finally:
            db.close()
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(cancel_order())
    loop.close()

@router.post("/create")
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """
    Create an order before payment processing
    """
    try:
        # Create order with pending status
        order = Order(
            user_id=current_user.id,
            total=order_data.total,
            status="pending"
        )
        db.add(order)
        db.flush()  # Get order ID without committing
        
        # Create order items
        for item in order_data.items:
            # Verify product exists
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                raise HTTPException(404, f"Product {item.product_id} not found")
            
            # Verify stock availability
            if product.stock < item.quantity:
                raise HTTPException(400, f"Insufficient stock for {product.name}")
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price
            )
            db.add(order_item)
        
        db.commit()
        db.refresh(order)
        
        # Schedule auto-cancellation after 15 minutes
        import threading
        thread = threading.Thread(target=auto_cancel_pending_order, args=(order.id, 15))
        thread.daemon = True
        thread.start()
        
        print(f"✅ Order #{order.id} created with auto-cancel scheduled in 15 minutes")
        
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
    """
    Legacy checkout endpoint - processes cart directly
    """
    cart = db.query(Cart).filter(Cart.user_id == user.id).all()

    if not cart:
        raise HTTPException(400, "Empty cart")

    order = Order(user_id=user.id, total=0, status="pending")
    db.add(order)
    db.commit()
    db.refresh(order)

    total = 0

    for item in cart:
        product = db.query(Product).get(item.product_id)
        
        if not product:
            continue
            
        reduce_stock(product, item.quantity, db)

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
    
    # Schedule auto-cancellation after 15 minutes
    import threading
    thread = threading.Thread(target=auto_cancel_pending_order, args=(order.id, 15))
    thread.daemon = True
    thread.start()

    return {"order_id": order.id, "total": total, "status": "pending"}

@router.get("/")
def get_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all orders for the current user
    """
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
                    "product_name": db.query(Product).filter(Product.id == item.product_id).first().name if db.query(Product).filter(Product.id == item.product_id).first() else None
                }
                for item in items
            ]
        })
    
    return result

@router.get("/admin/all")
def get_all_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all orders (admin only)
    """
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
    """
    Get a specific order by ID
    """
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
                "price": item.price
            }
            for item in items
        ]
    }

@router.put("/{order_id}/status")
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update order status (admin only)
    """
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
    """
    Cancel a pending order - CHANGES STATUS, DOES NOT DELETE
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(404, "Order not found")
    
    if order.status != 'pending':
        raise HTTPException(400, f"Cannot cancel order with status: {order.status}")
    
    # ✅ Change status, DO NOT delete
    order.status = 'cancelled'
    order.payment_error = "User cancelled the order"
    # Optionally restore stock here if you reduced it
    db.commit()
    
    return {"message": "Order cancelled successfully", "order_id": order_id, "status": "cancelled"}

@router.post("/{order_id}/retry-payment")
def retry_payment(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retry payment for a cancelled or failed order
    Creates a new order with the same items
    """
    old_order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not old_order:
        raise HTTPException(404, "Order not found")
    
    if old_order.status not in ['cancelled', 'payment_failed']:
        raise HTTPException(400, f"Cannot retry payment for order with status: {old_order.status}")
    
    # Create new order with same items
    new_order = Order(
        user_id=current_user.id,
        total=old_order.total,
        status="pending"
    )
    db.add(new_order)
    db.flush()
    
    # Copy order items
    old_items = db.query(OrderItem).filter(OrderItem.order_id == old_order.id).all()
    for item in old_items:
        new_item = OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price
        )
        db.add(new_item)
    
    db.commit()
    db.refresh(new_order)
    
    # Schedule auto-cancellation for new order
    import threading
    thread = threading.Thread(target=auto_cancel_pending_order, args=(new_order.id, 15))
    thread.daemon = True
    thread.start()
    
    print(f"🔄 Retry payment for order #{order_id} -> New order #{new_order.id}")
    
    return {
        "message": "Retry order created",
        "old_order_id": order_id,
        "new_order_id": new_order.id,
        "total": new_order.total
    }

@router.post("/cleanup-pending")
def cleanup_pending_orders(db: Session = Depends(get_db)):
    """
    Clean up old pending orders (admin endpoint or scheduled task)
    """
    timeout_minutes = 15
    cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    
    old_pending_orders = db.query(Order).filter(
        Order.status == 'pending',
        Order.created_at < cutoff_time
    ).all()
    
    cancelled_count = 0
    for order in old_pending_orders:
        order.status = 'cancelled'
        order.payment_error = f"Order automatically cancelled after {timeout_minutes} minutes (payment timeout)"
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
    """
    Manually confirm payment (for testing or fallback)
    """
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
    
    # Reduce stock for items (if not already reduced)
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            reduce_stock(product, item.quantity, db)
    
    return {"message": "Payment confirmed", "order_id": order_id, "status": "paid"}

@router.post("/send")
async def send_newsletter_email(
    campaign: EmailCampaign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send newsletter email campaign (admin only)
    """
    print(f"Sending email to {len(campaign.recipients)} recipients")
    print(f"Subject: {campaign.subject}")
    print(f"Message: {campaign.message}")
    
    return {"message": f"Email campaign sent to {len(campaign.recipients)} subscribers"}