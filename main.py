from routes import mpesa, admin
from fastapi import FastAPI
from routes import auth, products, cart, orders, mpesa, upload
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from models import Product   # IMPORTANT: ensure model is imported

Base.metadata.create_all(bind=engine)
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, prefix="/auth")
app.include_router(products.router, prefix="/products")
app.include_router(cart.router, prefix="/cart")
app.include_router(orders.router, prefix="/orders")
# app.include_router(mpesa.router, prefix="/mpesa")
app.include_router(upload.router, prefix="/upload")
app.include_router(mpesa.router, prefix="/mpesa")
app.include_router(admin.router, prefix="/admin")
