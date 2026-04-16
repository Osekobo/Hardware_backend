from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine

from routes import (
    auth,
    products,
    cart,
    orders,
    mpesa,
    upload,
    admin,
    newsletter
)

from models import Product, NewsletterSubscriber

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS (FIXED for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "hardwarefrontend.netlify.app" 
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/auth")
app.include_router(products.router, prefix="/products")
app.include_router(cart.router, prefix="/cart")
app.include_router(orders.router, prefix="/orders")
app.include_router(mpesa.router, prefix="/mpesa")
app.include_router(upload.router, prefix="/upload")
app.include_router(admin.router, prefix="/admin")
app.include_router(newsletter.router, prefix="/newsletter")