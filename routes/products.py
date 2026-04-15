from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Product
from auth.dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter()

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    image_url: str = None
    stock: int

class ProductUpdate(BaseModel):
    name: str = None
    description: str = None
    price: float = None
    image_url: str = None
    stock: int = None

@router.post("/")
def create_product(data: ProductCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = Product(
        name=data.name,
        description=data.description,
        price=data.price,
        image_url=data.image_url,
        stock=data.stock
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.get("/")
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    return product

@router.put("/{product_id}")
def update_product(
    product_id: int, 
    data: ProductUpdate, 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    if data.name is not None:
        product.name = data.name
    if data.description is not None:
        product.description = data.description
    if data.price is not None:
        product.price = data.price
    if data.image_url is not None:
        product.image_url = data.image_url
    if data.stock is not None:
        product.stock = data.stock
    
    db.commit()
    db.refresh(product)
    return product

@router.delete("/{product_id}")
def delete_product(
    product_id: int, 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}