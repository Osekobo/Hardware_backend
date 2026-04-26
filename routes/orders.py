# routes/orders.py
from pydantic import BaseModel
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
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


@router.post("/create")
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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

    return {"order_id": order.id, "total": total, "status": "pending"}


@router.get("/")
def get_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all orders for the current user (or all orders if admin)
    """
    # Check if user is admin (you can add an is_admin field to User model)
    # For now, return user's own orders
    orders = db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.created_at.desc()).all()
    
    # Include order items for each order
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
    # TODO: Add admin check
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
    
    # Check if user owns the order or is admin
    if order.user_id != current_user.id:
        # TODO: Add admin check
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
    # TODO: Add admin check
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    order.status = status_data.status
    db.commit()

    return {"message": "Order status updated", "status": order.status}


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
    
    order.status = "paid"
    order.mpesa_receipt = mpesa_receipt
    order.paid_at = datetime.utcnow()
    db.commit()
    
    # Reduce stock for items
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
    # TODO: Add admin check
    
    print(f"Sending email to {len(campaign.recipients)} recipients")
    print(f"Subject: {campaign.subject}")
    print(f"Message: {campaign.message}")

    # TODO: Implement actual email sending using SendGrid, Mailgun, etc.
    
    return {"message": f"Email campaign sent to {len(campaign.recipients)} subscribers"}