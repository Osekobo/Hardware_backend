from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from database import get_db
from models import Product
from auth.dependencies import get_current_user
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str  # ✅ Added category field
    subcategory: Optional[str] = None  # Optional: for more specific filtering
    image_url: str = None
    stock: int
    rating: float = 0.0  # Optional rating field

class ProductUpdate(BaseModel):
    name: str = None
    description: str = None
    price: float = None
    category: str = None  # ✅ Added category field
    subcategory: str = None
    image_url: str = None
    stock: int = None
    rating: float = None

@router.post("/")
def create_product(data: ProductCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = Product(
        name=data.name,
        description=data.description,
        price=data.price,
        category=data.category,  # ✅ Added category
        subcategory=data.subcategory,  # ✅ Added subcategory
        image_url=data.image_url,
        stock=data.stock,
        rating=data.rating
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """Get all unique categories from products"""
    categories = db.query(Product.category).distinct().filter(Product.category.isnot(None)).all()
    return [cat[0] for cat in categories if cat[0]]

@router.get("/")
def get_products(
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of products to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    sort_by: str = Query("newest", description="Sort by: newest, price_asc, price_desc, name_asc, name_desc, rating"),
    db: Session = Depends(get_db)
):
    """
    Get products with pagination, filtering, and sorting
    """
    query = db.query(Product)
    
    # Category filter
    if category and category != "all":
        query = query.filter(Product.category == category)
    
    # Search filter (name or description)
    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.description.ilike(f"%{search}%")
            )
        )
    
    # Price filter
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    # Sorting
    if sort_by == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort_by == "name_asc":
        query = query.order_by(Product.name.asc())
    elif sort_by == "name_desc":
        query = query.order_by(Product.name.desc())
    elif sort_by == "rating":
        query = query.order_by(Product.rating.desc())
    else:  # newest - sort by id descending (assuming newer products have higher IDs)
        query = query.order_by(Product.id.desc())
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    products = query.offset(skip).limit(limit).all()
    
    # Calculate total pages
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    
    return {
        "products": products,
        "total": total,
        "skip": skip,
        "limit": limit,
        "total_pages": total_pages,
        "current_page": (skip // limit) + 1 if limit > 0 else 1
    }

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
    if data.category is not None:
        product.category = data.category
    if data.subcategory is not None:
        product.subcategory = data.subcategory
    if data.image_url is not None:
        product.image_url = data.image_url
    if data.stock is not None:
        product.stock = data.stock
    if data.rating is not None:
        product.rating = data.rating
    
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