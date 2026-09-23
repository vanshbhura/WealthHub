from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

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

# Locate root-level frontend build directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DIST_DIR = Path(os.environ.get("FRONTEND_DIST_DIR", BASE_DIR / "dist")).resolve()

# Mount frontend assets if directory exists
assets_dir = DIST_DIR / "assets"
if assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/api/health", tags=["Health"])
def api_health():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


@app.get("/", include_in_schema=False)
async def serve_root():
    index_file = DIST_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {
        "app": "WealthHub API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
        "message": "Frontend build not found. Run 'npm run build' to generate dist/."
    }


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    # Guard: API endpoints must never be swallowed by the SPA fallback
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(
            status_code=404,
            detail={"code": "ENDPOINT_NOT_FOUND", "message": f"API endpoint '/{full_path}' not found"}
        )

    # Guard: FastAPI docs routes
    if full_path in ("docs", "redoc", "openapi.json"):
        raise HTTPException(status_code=404, detail="Not Found")

    # Serve static file from dist root if it exists (e.g. favicon.ico, vite.svg)
    candidate_file = DIST_DIR / full_path
    if candidate_file.is_file():
        return FileResponse(candidate_file)

    # SPA client-side routing fallback: return dist/index.html
    index_file = DIST_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    raise HTTPException(
        status_code=404,
        detail="Frontend build not found. Run 'npm run build' to generate dist/."
    )
