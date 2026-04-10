from fastapi import APIRouter, Depends
from database import get_db
from models import Cart
from auth.dependencies import get_current_user

router = APIRouter()

@router.post("/add/{product_id}")
def add_to_cart(product_id: int, db=Depends(get_db), user=Depends(get_current_user)):
    item = Cart(user_id=user.id, product_id=product_id, quantity=1)
    db.add(item)
    db.commit()
    return {"message": "added"}