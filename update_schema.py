# update_schema.py
import os
from sqlalchemy import create_engine, text

# Your Render PostgreSQL connection string
# Get this from Render Dashboard -> PostgreSQL service -> External Connection URL
DATABASE_URL = "postgresql://kione_db_user:YOUR_PASSWORD@dpg-xxxxx.frankfurt-postgres.render.com:5432/kione_db"

def update_schema():
    """Add missing columns to products table"""
    
    print("🔗 Connecting to Render PostgreSQL...")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Add category column
        try:
            conn.execute(text("ALTER TABLE products ADD COLUMN category VARCHAR;"))
            print("✅ Added 'category' column")
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print("ℹ️ 'category' column already exists")
            else:
                print(f"⚠️ Error adding category: {e}")
        
        # Add subcategory column
        try:
            conn.execute(text("ALTER TABLE products ADD COLUMN subcategory VARCHAR;"))
            print("✅ Added 'subcategory' column")
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print("ℹ️ 'subcategory' column already exists")
            else:
                print(f"⚠️ Error adding subcategory: {e}")
        
        # Add rating column
        try:
            conn.execute(text("ALTER TABLE products ADD COLUMN rating FLOAT DEFAULT 0;"))
            print("✅ Added 'rating' column")
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                print("ℹ️ 'rating' column already exists")
            else:
                print(f"⚠️ Error adding rating: {e}")
        
        conn.commit()
        print("\n✅ Schema update complete!")

if __name__ == "__main__":
    update_schema()