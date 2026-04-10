from fastapi import APIRouter, Depends, HTTPException
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