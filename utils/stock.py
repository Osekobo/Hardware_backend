from fastapi import HTTPException

def reduce_stock(product, qty, db):
    if product.stock < qty:
        raise HTTPException(400, "Out of stock")

    product.stock -= qty
    db.commit()