from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Cart, Product
from auth.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter()

class AddToCartRequest(BaseModel):
    quantity: int = 1

class CartUpdate(BaseModel):
    quantity: int

@router.post("/add/{product_id}")
def add_to_cart(
    product_id: int,
    request: AddToCartRequest,
    db: Session = Depends(get_db), 
    user = Depends(get_current_user)
):
    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    # Check if item already in cart
    existing_item = db.query(Cart).filter(
        Cart.user_id == user.id,
        Cart.product_id == product_id
    ).first()
    
    if existing_item:
        # Increase quantity by the requested amount
        existing_item.quantity += request.quantity
        db.commit()
        db.refresh(existing_item)
        return {"message": "Cart updated", "item": existing_item}
    else:
        # Add new item to cart with specified quantity
        cart_item = Cart(
            user_id=user.id,
            product_id=product_id,
            quantity=request.quantity
        )
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)
        return {"message": "Item added to cart", "item": cart_item}

@router.get("/")
def get_cart(
    db: Session = Depends(get_db), 
    user = Depends(get_current_user)
):
    cart_items = db.query(Cart).filter(Cart.user_id == user.id).all()
    
    # Join with product details
    result = []
    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            result.append({
                "id": item.id,
                "product_id": product.id,
                "product": {
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "image_url": product.image_url,
                    "stock": product.stock
                },
                "quantity": item.quantity
            })
    
    return result

@router.put("/{cart_item_id}")
def update_cart_item(
    cart_item_id: int,
    update: CartUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    cart_item = db.query(Cart).filter(
        Cart.id == cart_item_id,
        Cart.user_id == user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(404, "Cart item not found")
    
    if update.quantity <= 0:
        db.delete(cart_item)
    else:
        cart_item.quantity = update.quantity
    
    db.commit()
    return {"message": "Cart updated"}

@router.delete("/{cart_item_id}")
def remove_from_cart(
    cart_item_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    cart_item = db.query(Cart).filter(
        Cart.id == cart_item_id,
        Cart.user_id == user.id
    ).first()
    
    if not cart_item:
        raise HTTPException(404, "Cart item not found")
    
    db.delete(cart_item)
    db.commit()
    return {"message": "Item removed from cart"}

