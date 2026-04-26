# check_schema.py
from sqlalchemy import create_engine, inspect

DATABASE_URL = "postgresql://kione_db_user:YOUR_PASSWORD@dpg-xxxxx.frankfurt-postgres.render.com:5432/kione_db"

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

columns = inspector.get_columns('products')
print("Columns in products table:")
for col in columns:
    print(f"  - {col['name']} ({col['type']})")