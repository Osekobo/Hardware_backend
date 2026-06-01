# routes/products.py
from fastapi import APIRouter, Depends, HTTPException, Query, Response, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from database import get_db
from models import Product
from auth.dependencies import get_current_user
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import uuid
from PIL import Image
from io import BytesIO
from datetime import datetime
import os

router = APIRouter()

# ============= IMAGE CONFIGURATION =============
# Import from config or define here
from config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE

# ============= PYDANTIC MODELS =============
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

# ============= IMAGE HELPER FUNCTIONS =============
def validate_image(file_content: bytes, filename: str) -> tuple[bool, str]:
    """Validate image file type and size"""
    # Check size
    if len(file_content) > MAX_FILE_SIZE:
        return False, f"File too large. Maximum {MAX_FILE_SIZE // (1024*1024)}MB"
    
    # Check extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Verify it's actually an image
    try:
        Image.open(BytesIO(file_content))
        return True, "Valid"
    except Exception:
        return False, "File is not a valid image"

def save_image(file_content: bytes, original_filename: str) -> str:
    """Save image to local storage and return the URL path"""
    # Generate unique filename
    ext = Path(original_filename).suffix.lower()
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / unique_filename
    
    # Save the file
    with open(filepath, "wb") as f:
        f.write(file_content)
    
    # Create thumbnail (200x200) for better performance
    try:
        img = Image.open(filepath)
        thumbnail_filename = f"thumb_{unique_filename}"
        thumbnail_path = UPLOAD_DIR / thumbnail_filename
        img.thumbnail((200, 200))
        img.save(thumbnail_path, optimize=True, quality=85)
    except Exception as e:
        print(f"Thumbnail creation failed: {e}")
    
    return f"/static/uploads/{unique_filename}"  # Return URL path

def delete_image(image_url: str):
    """Delete image file and its thumbnail from storage"""
    if not image_url:
        return
    
    try:
        # Extract filename from URL
        filename = image_url.split("/")[-1]
        
        # Delete original
        original_path = UPLOAD_DIR / filename
        if original_path.exists():
            original_path.unlink()
        
        # Delete thumbnail
        thumbnail_path = UPLOAD_DIR / f"thumb_{filename}"
        if thumbnail_path.exists():
            thumbnail_path.unlink()
    except Exception as e:
        print(f"Error deleting image: {e}")

# ============= PRODUCT ENDPOINTS =============

@router.post("/")
def create_product(
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    stock: int = Form(...),
    subcategory: Optional[str] = Form(None),
    rating: float = Form(0.0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Create a new product with image upload
    """
    # 1. Validate and save the image
    contents = file.file.read()
    is_valid, error_msg = validate_image(contents, file.filename)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Save image and get URL
    try:
        image_url = save_image(contents, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")
    
    # 2. Create product in database
    product = Product(
        name=name,
        description=description,
        price=price,
        category=category,
        subcategory=subcategory,
        stock=stock,
        rating=rating,
        file_image=image_url
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.post("/{product_id}/upload-image")
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Upload/Update image for an existing product
    """
    # Find product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    # Validate new image
    contents = file.file.read()
    is_valid, error_msg = validate_image(contents, file.filename)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Delete old image if exists
    if product.file_image:
        delete_image(product.file_image)
    
    # Save new image
    try:
        image_url = save_image(contents, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")
    
    # Update product
    product.file_image = image_url
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    
    return {"message": "Image uploaded successfully", "file_image": product.file_image}


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
    
    # Sorting
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
    user = Depends(get_current_user)
):
    """
    Update product details (text fields only)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    # Update only provided fields
    update_data = data.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(product, key, value)
    
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: int, 
    db: Session = Depends(get_db), 
    user = Depends(get_current_user)
):
    """
    Delete product and its associated image
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    # Delete the image file from storage
    if product.file_image:
        delete_image(product.file_image)
    
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}


@router.delete("/{product_id}/image")
def delete_product_image(
    product_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Delete only the product's image (not the product itself)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    if not product.file_image:
        raise HTTPException(404, "Product has no image")
    
    # Delete image file
    delete_image(product.file_image)
    
    # Remove image URL from database
    product.file_image = None
    product.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Product image deleted successfully"}


@router.delete("/batch")
def delete_products(
    request: BatchDeleteRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Admin only - Delete multiple products at once"""
    if not user.is_admin:
        raise HTTPException(403, "Admin access required")
    
    # Get all products to delete their images
    products_to_delete = db.query(Product).filter(Product.id.in_(request.product_ids)).all()
    
    # Delete image files
    for product in products_to_delete:
        if product.file_image:
            delete_image(product.file_image)
    
    # Delete from database
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