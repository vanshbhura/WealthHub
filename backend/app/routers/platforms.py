import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.platform import Platform
from app.models.platform_connector import PlatformConnector
from app.schemas.platform import PlatformResponse
from app.schemas.platform_connector import PlatformConnectorResponse
from app.connectors.registry import registry
from app.connectors.enums import ConnectionMethodStatus

router = APIRouter(prefix="/api/platforms", tags=["Platforms"])


@router.get("", response_model=List[PlatformResponse])
def list_platforms(
    category: Optional[str] = Query(None, description="Filter by category: BANK, BROKER, MUTUAL_FUND, P2P, DIGITAL_GOLD, DIGITAL_SILVER, CRYPTO, RETIREMENT, OTHER"),
    active_only: bool = Query(True, description="Filter only active platforms"),
    db: Session = Depends(get_db)
):
    """Retrieve catalog of supported financial platforms, optionally filtered by asset category."""
    stmt = select(Platform)
    if active_only:
        stmt = stmt.where(Platform.is_active == True)
    if category:
        stmt = stmt.where(Platform.category == category.upper())

    stmt = stmt.order_by(Platform.name.asc())
    platforms = list(db.execute(stmt).scalars().all())
    return [PlatformResponse.model_validate(p) for p in platforms]


@router.get("/{platform_id}", response_model=PlatformResponse)
def get_platform_by_id(platform_id: str, db: Session = Depends(get_db)):
    """Retrieve a specific platform by its UUID or unique slug."""
    try:
        pid = uuid.UUID(platform_id)
        stmt = select(Platform).where(Platform.id == pid)
    except ValueError:
        # Match by slug
        stmt = select(Platform).where(Platform.slug == platform_id.lower())

    platform = db.execute(stmt).scalar_one_or_none()
    if not platform:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PLATFORM_NOT_FOUND", "message": f"Platform '{platform_id}' not found"}
        )

    return PlatformResponse.model_validate(platform)


@router.get("/{platform_id}/connectors", response_model=List[PlatformConnectorResponse])
def get_platform_connectors(platform_id: str, db: Session = Depends(get_db)):
    """
    Retrieve supported connection methods, status, and capabilities for a platform.
    Strictly differentiates between live AVAILABLE methods and COMING_SOON integrations.
    """
    try:
        pid = uuid.UUID(platform_id)
        stmt = select(Platform).where(Platform.id == pid)
    except ValueError:
        stmt = select(Platform).where(Platform.slug == platform_id.lower())

    platform = db.execute(stmt).scalar_one_or_none()
    if not platform:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PLATFORM_NOT_FOUND", "message": f"Platform '{platform_id}' not found"}
        )

    # 1. Query database platform_connectors
    db_conns_stmt = select(PlatformConnector).where(PlatformConnector.platform_id == platform.id)
    db_conns = list(db.execute(db_conns_stmt).scalars().all())

    if db_conns:
        return [
            PlatformConnectorResponse(
                id=c.id,
                platform_id=c.platform_id,
                connector_type=c.connector_type,
                connector_key=c.connector_key,
                name=c.connector_type.replace("_", " ").title(),
                status=c.status,
                capabilities=[cap if isinstance(cap, str) else cap.value for cap in c.capabilities],
                is_enabled=c.is_enabled,
                requirements="No credentials required" if c.connector_type == "MANUAL" else "API authentication required",
            )
            for c in db_conns
        ]

    # 2. Fallback to registered connectors dynamically
    connectors = registry.get_for_platform(platform.slug)
    response_items = []

    for c in connectors:
        req = "No credentials required" if c.connector_type.value == "MANUAL" else "Direct provider API credentials"
        if c.connector_type.value == "ACCOUNT_AGGREGATOR":
            req = "RBI Account Aggregator consent authorization"
        elif c.connector_type.value == "IMPORT":
            req = "Account / CAS statement file (PDF, Excel, CSV)"

        response_items.append(
            PlatformConnectorResponse(
                platform_id=platform.id,
                connector_type=c.connector_type.value,
                connector_key=c.connector_key,
                name=c.name,
                status=c.status.value,
                capabilities=[cap.value for cap in c.get_capabilities()],
                is_enabled=c.is_available(),
                requirements=req,
            )
        )

    return response_items
