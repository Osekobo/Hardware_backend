import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Product

def add_sample_products():
    db = SessionLocal()
    
    # Clear existing products (optional)
    db.query(Product).delete()
    
    products = [
        Product(
            name="iPhone 15 Pro",
            description="Latest Apple iPhone with A17 Pro chip, 48MP camera, and titanium design. 256GB storage.",
            price=165000,
            image_url="https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=400",
            stock=15
        ),
        Product(
            name="Samsung Galaxy S24 Ultra",
            description="Premium Android smartphone with 200MP camera, S Pen, and AI features. 512GB storage.",
            price=185000,
            image_url="https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400",
            stock=12
        ),
        Product(
            name="MacBook Pro M3",
            description="14-inch laptop with M3 Pro chip, 18GB RAM, 512GB SSD. Perfect for professionals.",
            price=285000,
            image_url="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400",
            stock=8
        ),
        Product(
            name="Sony WH-1000XM5",
            description="Industry-leading noise canceling headphones with 30-hour battery life.",
            price=35000,
            image_url="https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?w=400",
            stock=25
        ),
        Product(
            name="Nike Air Max 90",
            description="Classic running shoes with iconic Air cushioning. Available in multiple colors.",
            price=12500,
            image_url="https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=400",
            stock=40
        ),
        Product(
            name="Leather Backpack",
            description="Genuine leather backpack with laptop compartment. Perfect for work or travel.",
            price=8500,
            image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400",
            stock=30
        ),
        Product(
            name="Smart Watch Series 8",
            description="Fitness tracker with heart rate monitor, GPS, and 5-day battery life.",
            price=22500,
            image_url="https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=400",
            stock=20
        ),
        Product(
            name="Wireless Earbuds Pro",
            description="Active noise cancellation, 24-hour battery, and crystal clear calls.",
            price=8500,
            image_url="https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=400",
            stock=50
        ),
        Product(
            name="Gaming Keyboard RGB",
            description="Mechanical keyboard with customizable RGB lighting and programmable keys.",
            price=6500,
            image_url="https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400",
            stock=35
        ),
        Product(
            name="Ergonomic Office Chair",
            description="Adjustable chair with lumbar support for home office comfort.",
            price=18500,
            image_url="https://images.unsplash.com/photo-1589384267710-7a170981ca78?w=400",
            stock=10
        ),
        Product(
            name="4K Action Camera",
            description="Waterproof action camera with 4K video and image stabilization.",
            price=15500,
            image_url="https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=400",
            stock=18
        ),
        Product(
            name="Portable Bluetooth Speaker",
            description="Waterproof speaker with 20-hour battery and powerful bass.",
            price=7500,
            image_url="https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400",
            stock=28
        ),
        Product(
            name="Fitness Tracker Band",
            description="Track steps, calories, sleep, and heart rate with smartphone sync.",
            price=4500,
            image_url="https://images.unsplash.com/photo-1575311373937-040b8e1fd6b6?w=400",
            stock=45
        ),
        Product(
            name="Laptop Stand",
            description="Adjustable aluminum laptop stand for better ergonomics.",
            price=3500,
            image_url="https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400",
            stock=60
        ),
        Product(
            name="Wireless Mouse",
            description="Ergonomic wireless mouse with silent clicks and long battery life.",
            price=2500,
            image_url="https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400",
            stock=55
        ),
        Product(
            name="USB-C Hub",
            description="7-in-1 multiport adapter with 4K HDMI, USB 3.0, and SD card reader.",
            price=4500,
            image_url="https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=400",
            stock=32
        ),
        Product(
            name="Desk Lamp",
            description="LED desk lamp with adjustable brightness and color temperature.",
            price=3500,
            image_url="https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=400",
            stock=25
        ),
        Product(
            name="Coffee Mug Warmer",
            description="Keep your coffee at perfect temperature all day.",
            price=2500,
            image_url="https://images.unsplash.com/photo-1517256673644-36ad1125d3d9?w=400",
            stock=40
        ),
        Product(
            name="Phone Gimbal Stabilizer",
            description="3-axis smartphone gimbal for smooth video recording.",
            price=12500,
            image_url="https://images.unsplash.com/photo-1590736704728-f4730bb30770?w=400",
            stock=15
        ),
        Product(
            name="External SSD 1TB",
            description="Portable solid state drive with USB-C, 1050MB/s read speed.",
            price=15500,
            image_url="https://images.unsplash.com/photo-1627207643571-ae86dfa2a6d7?w=400",
            stock=22
        ),
    ]
    
    for product in products:
        db.add(product)
    
    db.commit()
    print(f"✅ Added {len(products)} products to database!")
    
    # Verify
    count = db.query(Product).count()
    print(f"📊 Total products in database: {count}")
    
    db.close()

if __name__ == "__main__":
    add_sample_products()