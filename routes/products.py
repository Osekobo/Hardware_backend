from fastapi import APIRouter, Depends
from database import get_db
from models import Product
from auth.dependencies import get_current_user

router = APIRouter()

@router.post("/")
def create_product(data, db=Depends(get_db), user=Depends(get_current_user)):
    product = Product(**data.dict())
    db.add(product)
    db.commit()
    return product


@router.get("/")
def get_products(db=Depends(get_db)):
    return db.query(Product).all()
