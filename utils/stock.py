from fastapi import HTTPException
from models import Product, OrderItem


def reduce_stock(product, qty, db):
    if product.stock < qty:
        raise HTTPException(400, "Out of stock")

    product.stock -= qty
    db.commit()


def restore_stock(order, db):
    items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()

    for item in items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.stock += item.quantity

    db.commit()