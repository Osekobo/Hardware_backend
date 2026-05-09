from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
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
    category: str
    subcategory: Optional[str] = None
    file_image: str = None
    stock: int
    rating: float = 0.0

class ProductUpdate(BaseModel):
    name: str = None
    description: str = None
    price: float = None
    category: str = None
    subcategory: str = None
    file_image: str = None
    stock: int = None
    rating: float = None

class BatchDeleteRequest(BaseModel):
    product_ids: List[int]

@router.post("/")
def create_product(data: ProductCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = Product(**data.dict())
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
    response: Response,
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of products to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    sort_by: str = Query("newest", description="Sort by: newest, price_asc, price_desc, name_asc, name_desc, rating, popular"),
    db: Session = Depends(get_db)
):
    """
    Get products with pagination, filtering, and sorting
    """
    # Cache for home page queries (5 minutes) - improves performance
    if skip == 0 and limit == 8 and not category and not search:
        response.headers["Cache-Control"] = "public, max-age=300"
    
    query = db.query(Product)
    
    # Category filter
    if category and category != "all":
        query = query.filter(Product.category == category)
    
    # Search filter
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
    
    # Sorting - using mapping for cleaner code
    sort_mapping = {
        "price_asc": Product.price.asc(),
        "price_desc": Product.price.desc(),
        "name_asc": Product.name.asc(),
        "name_desc": Product.name.desc(),
        "rating": Product.rating.desc(),
        "popular": Product.rating.desc(),
        "newest": Product.id.desc()
    }
    query = query.order_by(sort_mapping.get(sort_by, Product.id.desc()))
    
    # Get total count
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
    
    # Update only provided fields
    for key, value in data.dict(exclude_unset=True).items():
        setattr(product, key, value)
    
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

@router.delete("/batch")
def delete_products(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    """Admin only - Delete multiple products at once"""
    if not user.is_admin:
        raise HTTPException(403, "Admin access required")
    
    deleted = db.query(Product).filter(Product.id.in_(request.product_ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Deleted {deleted} products"}

@router.get("/search/quick")
def quick_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Number of results to return"),
    db: Session = Depends(get_db)
):
    """Quick search endpoint for autocomplete/fast search"""
    products = db.query(
        Product.id, 
        Product.name, 
        Product.price, 
        Product.file_image
    ).filter(
        or_(
            Product.name.ilike(f"%{q}%"),
            Product.description.ilike(f"%{q}%")
        )
    ).limit(limit).all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "file_image": p.file_image
        }
        for p in products
    ]