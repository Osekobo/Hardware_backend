import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Your existing imports and app setup
from database import Base, engine
from routes import auth, products, cart, orders, mpesa, upload, admin, newsletter

# Create tables (only create, not drop - keep drop_all commented out)
# Base.metadata.drop_all(bind=engine)  # ⚠️ Only uncomment if you want to delete all data!
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kione Hardware API", version="1.0.0")

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

# Include routers (remove duplicate entries)
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(cart.router, prefix="/cart", tags=["Cart"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(mpesa.router, prefix="/mpesa", tags=["M-Pesa"])
app.include_router(upload.router, prefix="/upload", tags=["Uploads"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(newsletter.router, prefix="/newsletter", tags=["Newsletter"])


@app.get("/")
def root():
    return {"message": "Kione Hardware API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# This is the CRITICAL part for Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)