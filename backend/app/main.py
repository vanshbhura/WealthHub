from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database import engine, Base
import app.models  # ensure all models are registered with Base.metadata
from app.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from app.routers import (
    auth,
    platforms,
    connections,
    accounts,
    assets,
    transactions,
    portfolio,
    imports,
    account_aggregator,
)

# Auto-create tables on startup (and Alembic for migrations)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WealthHub API",
    description="Backend API and database engine for WealthHub — One Clean Window Into All Your Money.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


@app.on_event("startup")
def startup_event():
    # Ensure platform catalog is seeded idempotently on startup
    try:
        from app.seed import seed_platforms
        seed_platforms()
    except Exception as e:
        print(f"Warning: platform seed on startup failed: {e}")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
if not settings.DEBUG:
    app.add_exception_handler(Exception, generic_exception_handler)

# Register Routers
app.include_router(auth.router)
app.include_router(platforms.router)
app.include_router(connections.router)
app.include_router(accounts.router)
app.include_router(assets.router)
app.include_router(transactions.router)
app.include_router(portfolio.router)
app.include_router(imports.router)
app.include_router(account_aggregator.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "app": "WealthHub API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }
