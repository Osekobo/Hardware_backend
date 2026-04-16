import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Your existing imports and app setup
from database import Base, engine
from routes import auth, products, cart, orders, mpesa, upload, admin, newsletter

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://hardwarefrontend.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth")
app.include_router(products.router, prefix="/products")
app.include_router(cart.router, prefix="/cart")
app.include_router(orders.router, prefix="/orders")
app.include_router(mpesa.router, prefix="/mpesa")
app.include_router(upload.router, prefix="/upload")
app.include_router(admin.router, prefix="/admin")
app.include_router(newsletter.router, prefix="/newsletter")

@app.get("/")
def root():
    return {"message": "Kione Hardware API is running"}

# This is the CRITICAL part for Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)