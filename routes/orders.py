from pydantic import BaseModel
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Order, OrderItem, Product, Cart
from utils.stock import reduce_stock
from auth.dependencies import get_current_user

router = APIRouter()


@router.post("/checkout")
def checkout(db=Depends(get_db), user=Depends(get_current_user)):

    cart = db.query(Cart).filter(Cart.user_id == user.id).all()

    if not cart:
        raise HTTPException(400, "Empty cart")

    order = Order(user_id=user.id, total=0)
    db.add(order)
    db.commit()
    db.refresh(order)

    total = 0

    for item in cart:
        product = db.query(Product).get(item.product_id)

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

    return {"order_id": order.id, "total": total}


@router.put("/{order_id}/status")
def update_order_status(
    order_id: int,
    status_data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Check if user is admin (you'll need to add is_admin field)
    # For now, allow any logged-in user

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    order.status = status_data.get("status")
    db.commit()

    return {"message": "Order status updated"}


class EmailCampaign(BaseModel):
    recipients: List[str]
    subject: str
    message: str


@router.post("/send")
async def send_newsletter_email(
    campaign: EmailCampaign,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)  # Only admins can send emails
):
    # Here you would integrate with an email service like SendGrid, Mailgun, etc.
    # For now, we'll just log it

    print(f"Sending email to {len(campaign.recipients)} recipients")
    print(f"Subject: {campaign.subject}")
    print(f"Message: {campaign.message}")

    # TODO: Implement actual email sending
    # For production, use a service like:
    # - SendGrid
    # - Mailgun
    # - AWS SES
    # - Nodemailer (if using Node.js)

    return {"message": f"Email campaign sent to {len(campaign.recipients)} subscribers"}
