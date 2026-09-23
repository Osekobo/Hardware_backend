import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Product
from database import Base


def normalize_url(url):
    if not url:
        return None
    if "asyncpg" in url:
        url = url.replace("+asyncpg", "")
    if "render.com" in url and "sslmode" not in url:
        url += "?sslmode=require"
    return url


def make_session(url):
    engine = create_engine(url, pool_pre_ping=True)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def migrate(reset=False):
    local_url = normalize_url(os.getenv("LOCAL_DATABASE_URL"))
    render_url = normalize_url(os.getenv("DATABASE_URL"))

    if not local_url:
        raise ValueError("LOCAL_DATABASE_URL is not set (add it to .env)")

    local_db = make_session(local_url)
    render_db = make_session(render_url)

    try:
        rows = local_db.execute(
            text("SELECT name, description, price, category, subcategory, "
                 "file_image, stock, rating FROM products ORDER BY id")
        ).fetchall()
        print(f"📦 Found {len(rows)} products in local DB")

        if not rows:
            print("❌ No products to migrate")
            return

        existing = render_db.query(Product).count()
        if existing > 0 and not reset:
            print(f"⚠️  Render already has {existing} products.")
            ans = input("Delete them and insert local products instead? (y/n): ").strip().lower()
            if ans != "y":
                print("❌ Aborted")
                return
            reset = True

        if reset:
            render_db.query(Product).delete()
            print("🗑  Cleared existing products in Render")
            render_db.commit()

        products = [
            Product(
                name=r.name,
                description=r.description,
                price=r.price,
                category=r.category,
                subcategory=r.subcategory,
                file_image=r.file_image,
                stock=r.stock,
                rating=r.rating or 0.0,
            )
            for r in rows
        ]
        render_db.add_all(products)
        render_db.commit()
        print(f"✅ Migrated {len(products)} products from local → Render!")
    finally:
        local_db.close()
        render_db.close()


if __name__ == "__main__":
    migrate(reset="--reset" in sys.argv)