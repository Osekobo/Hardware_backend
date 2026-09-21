import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from sqlalchemy import text
import uvicorn
from fastapi.staticfiles import StaticFiles

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from database import Base, engine, SessionLocal
from routes import auth, products, cart, orders, mpesa, upload, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Kione Hardware API...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Kione Hardware API...")
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app = FastAPI(
    title="Kione Hardware API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

from pathlib import Path
UPLOAD_DIR = Path("static/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static/uploads", StaticFiles(directory="static/uploads"), name="uploads")
logger.info("Static files mounted at /static/uploads")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Content-Length", "X-Total-Count"],
    max_age=3600,
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500}
    )

routers = [
    (auth.router, "/auth", ["Authentication"]),
    (products.router, "/products", ["Products"]),
    (cart.router, "/cart", ["Cart"]),
    (orders.router, "/orders", ["Orders"]),
    (mpesa.router, "/mpesa", ["M-Pesa"]),
    (upload.router, "/upload", ["Uploads"]),
    (admin.router, "/admin", ["Admin"]),
]

for router, prefix, tags in routers:
    app.include_router(router, prefix=prefix, tags=tags)
    logger.info(f"Registered router: {prefix}")

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Kione Hardware API is running",
        "version": app.version,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "status": "operational"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    health_status = {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        "services": {
            "database": "unknown",
            "api": "healthy"
        }
    }
    
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["status"] = "degraded"
        health_status["services"]["database"] = "unhealthy"
    
    if health_status["services"]["database"] != "healthy":
        return JSONResponse(status_code=503, content=health_status)
    
    return health_status

@app.get("/api/info", tags=["Info"])
async def api_info():
    return {
        "name": "Kione Hardware API",
        "version": app.version,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "routes": len(app.routes),
        "endpoints": [
            {"path": route.path, "methods": list(route.methods) if hasattr(route, 'methods') else []}
            for route in app.routes if hasattr(route, 'methods')
        ]
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    environment = os.getenv("ENVIRONMENT", "development")
    
    if environment == "production":
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            workers=int(os.getenv("WEB_CONCURRENCY", 4)),
            log_level="info",
            access_log=True,
            proxy_headers=True,
            forwarded_allow_ips="*"
        )
    else:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=True,
            log_level="debug",
            access_log=True
        )