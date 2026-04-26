import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Product
from database import Base

# Use your Render PostgreSQL connection string
# Get this from Render Dashboard -> PostgreSQL Database -> Connection String
# add_products.py - Update to match Render backend
RENDER_DATABASE_URL = "postgresql://kione_hardware_db_user:dgEFoTNFveOAYaKvljd4HL9XcRlWiBAT@dpg-d7lb30f7f7vs73avj46g-a.oregon-postgres.render.com/kione_hardware_db"

def add_products_to_render():
    """Add products directly to Render PostgreSQL database from local machine"""
    
    # Create engine for Render database
    engine = create_engine(RENDER_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Check existing products
    existing_count = db.query(Product).count()
    print(f"📊 Existing products in Render: {existing_count}")
    
    if existing_count > 0:
        confirm = input(f"⚠️ Found {existing_count} products. Delete them and add new ones? (y/n): ")
        if confirm.lower() == 'y':
            db.query(Product).delete()
            print("✅ Cleared existing products")
        else:
            print("❌ Aborted")
            db.close()
            return
    
    products = [
        # Building Materials
        {
            "name": "Portland Cement (50kg)",
            "description": "High-quality Portland cement for all construction needs. Perfect for foundations, walls, and general building work.",
            "price": 850,
            "category": "building",
            "image_url": "https://images.unsplash.com/photo-1577789099564-8bf48d9ea15d?w=400",
            "stock": 500
        },
        {
            "name": "Grade 40 Steel Reinforcement Bar (12mm)",
            "description": "Strong steel reinforcement bars for concrete structures. Corrosion-resistant and meets international standards.",
            "price": 750,
            "category": "building",
            "image_url": "https://images.unsplash.com/photo-1583001903870-4ab9639d66cb?w=400",
            "stock": 1000
        },
        {
            "name": "Corrugated Iron Sheets (Mabati) - 30 Gauge",
            "description": "Durable galvanized roofing sheets. Weather-resistant and long-lasting. Ideal for residential and commercial buildings.",
            "price": 550,
            "category": "building",
            "image_url": "https://images.unsplash.com/photo-1567016432779-094069958ea5?w=400",
            "stock": 800
        },
        {
            "name": "Hardwood Timber - 2x4 (12ft)",
            "description": "Premium kiln-dried hardwood timber for construction and furniture making. Strong and durable.",
            "price": 1200,
            "category": "building",
            "image_url": "https://images.unsplash.com/photo-1580388768056-2bf284cd53d6?w=400",
            "stock": 300
        },
        {
            "name": "Concrete Blocks (6-inch)",
            "description": "High-strength concrete blocks for wall construction. Uniform size and shape for easy building.",
            "price": 120,
            "category": "building",
            "image_url": "https://images.unsplash.com/photo-1590075407676-b2f0ccb8c69c?w=400",
            "stock": 5000
        },
        {
            "name": "River Sand (Per Ton)",
            "description": "Clean, washed river sand perfect for plastering and concrete mixing. Well-screened and free from impurities.",
            "price": 3500,
            "category": "building",
            "image_url": "https://images.unsplash.com/photo-1580542221268-0bb055bce9e9?w=400",
            "stock": 200
        },
        
        # Paints
        {
            "name": "Interior Emulsion Paint - White (20L)",
            "description": "High-quality interior paint with excellent coverage. Washable and durable finish for walls and ceilings.",
            "price": 4500,
            "category": "paints",
            "image_url": "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=400",
            "stock": 150
        },
        {
            "name": "Exterior Weatherproof Paint - Terracotta (4L)",
            "description": "Premium exterior paint designed to withstand harsh weather conditions. UV resistant and long-lasting.",
            "price": 2800,
            "category": "paints",
            "image_url": "https://images.unsplash.com/photo-1562259949-e1816dedd812?w=400",
            "stock": 100
        },
        {
            "name": "Wood Varnish - Gloss Clear (1L)",
            "description": "High-gloss varnish for wood protection. Enhances natural wood grain while providing durable finish.",
            "price": 850,
            "category": "paints",
            "image_url": "https://images.unsplash.com/photo-1618354691373-d851c5c3a990?w=400",
            "stock": 80
        },
        {
            "name": "Wall Primer (10L)",
            "description": "Professional-grade wall primer for better paint adhesion and coverage. Seals porous surfaces effectively.",
            "price": 2200,
            "category": "paints",
            "image_url": "https://images.unsplash.com/photo-1589330273590-245f6d604155?w=400",
            "stock": 120
        },
        {
            "name": "Metal Paint - Anti-Rust Black (5L)",
            "description": "Protective coating for metal surfaces. Prevents rust and corrosion. Ideal for gates, roofs, and metal structures.",
            "price": 3200,
            "category": "paints",
            "image_url": "https://images.unsplash.com/photo-1590266893557-1e6edfecb35b?w=400",
            "stock": 60
        },
        {
            "name": "Paint Roller Set (9-inch)",
            "description": "Complete paint roller set including frame, roller cover, and tray. Professional quality for smooth application.",
            "price": 450,
            "category": "paints",
            "image_url": "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=400",
            "stock": 200
        },
        
        # Hardware Tools
        {
            "name": "Professional Hammer (16oz)",
            "description": "Durable steel hammer with anti-slip fiberglass handle. Perfect for framing and general construction work.",
            "price": 550,
            "category": "hardware",
            "image_url": "https://images.unsplash.com/photo-1586864387967-d02ef85d93e0?w=400",
            "stock": 150
        },
        {
            "name": "Cordless Drill 18V",
            "description": "Powerful cordless drill with 2 batteries and charger. Variable speed and 21-position clutch for precision drilling.",
            "price": 8500,
            "category": "hardware",
            "image_url": "https://images.unsplash.com/photo-1504917595217-d4dc5ebe6122?w=400",
            "stock": 45
        },
        {
            "name": "Tool Set - 100 Pieces",
            "description": "Complete tool set including sockets, wrenches, pliers, screwdrivers, and more. Perfect for home and workshop use.",
            "price": 6500,
            "category": "hardware",
            "image_url": "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=400",
            "stock": 80
        },
        {
            "name": "Measuring Tape (5m)",
            "description": "Professional measuring tape with metric and imperial measurements. Locking mechanism and durable blade.",
            "price": 250,
            "category": "hardware",
            "image_url": "https://images.unsplash.com/photo-1579174541026-64e1c6eaf93a?w=400",
            "stock": 300
        },
        {
            "name": "Angle Grinder 850W",
            "description": "Heavy-duty angle grinder with adjustable guard. Perfect for cutting and grinding metal, stone, and concrete.",
            "price": 4200,
            "category": "hardware",
            "image_url": "https://images.unsplash.com/photo-1572210552361-b939152dc161?w=400",
            "stock": 40
        },
        
        # Plumbing
        {
            "name": "PVC Water Pipe 1/2 inch (6m)",
            "description": "High-quality PVC pipe for water supply and drainage. UV resistant and durable.",
            "price": 850,
            "category": "plumbing",
            "image_url": "https://images.unsplash.com/photo-1584622781867-8afa0ab3a796?w=400",
            "stock": 500
        },
        {
            "name": "Kitchen Mixer Tap",
            "description": "Modern kitchen mixer tap with 360-degree swivel. Chrome finish and ceramic disc technology.",
            "price": 3500,
            "category": "plumbing",
            "image_url": "https://images.unsplash.com/photo-1590779032306-983786a0de1e?w=400",
            "stock": 50
        },
        
        # Electrical
        {
            "name": "LED Bulb 12W (Cold White)",
            "description": "Energy-saving LED bulb with long lifespan. Provides bright, consistent light for any room.",
            "price": 350,
            "category": "electrical",
            "image_url": "https://images.unsplash.com/photo-1562663474-6cbb3eaa4d4f?w=400",
            "stock": 1000
        },
        {
            "name": "Circuit Breaker 16A",
            "description": "Single pole circuit breaker for electrical safety. Protects against overloads and short circuits.",
            "price": 650,
            "category": "electrical",
            "image_url": "https://images.unsplash.com/photo-1627485933178-9283db6aecfd?w=400",
            "stock": 150
        },
        
        # General Store
        {
            "name": "Wheelbarrow Heavy Duty",
            "description": "Sturdy wheelbarrow with pneumatic tire. Perfect for transporting building materials.",
            "price": 4500,
            "category": "general",
            "image_url": "https://images.unsplash.com/photo-1567459169667-05cd47e4edb2?w=400",
            "stock": 30
        },
        {
            "name": "Safety Helmet (Hard Hat)",
            "description": "Industrial-grade safety helmet for construction sites. Adjustable and comfortable fit.",
            "price": 850,
            "category": "general",
            "image_url": "https://images.unsplash.com/photo-1581091226033-d5c48150dbaa?w=400",
            "stock": 200
        },
    ]
    
    for product_data in products:
        product = Product(**product_data)
        db.add(product)
    
    db.commit()
    
    # Verify
    count = db.query(Product).count()
    categories = db.query(Product.category).distinct().all()
    
    print(f"\n✅ Added {count} products to Render database!")
    print(f"📊 Categories:")
    for cat in categories:
        if cat[0]:
            cat_count = db.query(Product).filter(Product.category == cat[0]).count()
            print(f"   - {cat[0]}: {cat_count} products")
    
    db.close()

if __name__ == "__main__":
    add_products_to_render()