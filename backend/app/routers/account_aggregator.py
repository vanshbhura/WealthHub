import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.connection import Connection
from app.models.platform import Platform
from app.models.account import Account
from app.models.asset import Asset
from app.dependencies import get_current_user
from app.connectors.account_aggregator.setu_client import SetuAAClient
from app.connectors.account_aggregator.setu_connector import SetuAAConnector
from app.connectors.account_aggregator.dtos import SetuConsentRequest
from app.connectors.account_aggregator.exceptions import (
    SetuClientError,
    SetuConsentRejectedError,
    SetuConsentExpiredError,
    SetuConsentRevokedError,
    SetuConfigurationError,
)
from app.connectors.sync_service import SyncService

router = APIRouter(prefix="/api/account-aggregator", tags=["Account Aggregator"])


# --- Schemas ---

class AAConsentCreateRequest(BaseModel):
    customer_phone: Optional[str] = Field(None, description="Customer 10-digit mobile number for AA handle lookup")
    customer_vpa: Optional[str] = Field(None, description="Customer AA VPA handle (e.g. 9876543210@onemoney)")
    fi_types: List[str] = Field(
        default=["DEPOSIT", "TERM_DEPOSIT", "MUTUAL_FUNDS", "EQUITIES", "NPS"],
        description="List of RBI FI-Types to request consent for",
    )
    expiry_days: int = 90
    redirect_url: Optional[str] = None


class AAConsentCreateResponse(BaseModel):
    consent_id: str
    url: Optional[str]
    status: str
    created_at: datetime
    connection_id: uuid.UUID
    is_sandbox: bool = True


class AAConsentStatusResponse(BaseModel):
    consent_id: str
    status: str
    fi_types: List[str]
    expires_at: Optional[datetime] = None
    connection_id: uuid.UUID
    is_sandbox: bool = True


class AASyncResponse(BaseModel):
    status: str
    records_processed: int
    records_created: int
    records_updated: int
    completed_at: datetime
    connection_id: uuid.UUID
    accounts_discovered: int
    holdings_discovered: int
    is_sandbox: bool = True
    data_source: str = "SANDBOX_MOCK"


class AAConnectionStatus(BaseModel):
    connection_id: uuid.UUID
    platform_name: str
    status: str
    consent_id: Optional[str] = None
    consent_status: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    last_data_fetch: Optional[datetime] = None
    is_sandbox: bool = True


# --- Endpoints ---

@router.post("/consent", response_model=AAConsentCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_consent(
    payload: AAConsentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initiates a new sandbox consent session via Setu AA.
    Creates or reuses the user's Account Aggregator connection.
    """
    # 1. Resolve Account Aggregator platform
    plat_stmt = select(Platform).where(Platform.slug == "account-aggregator")
    platform = db.execute(plat_stmt).scalar_one_or_none()
    if not platform:
        # Fallback if seed has not run
        platform = Platform(
            name="Account Aggregator",
            slug="account-aggregator",
            category="AGGREGATOR",
            integration_type="ACCOUNT_AGGREGATOR",
            description="RBI-regulated consent-based financial data aggregation (Sandbox).",
        )
        db.add(platform)
        db.flush()

    # 2. Find or create user connection
    conn_stmt = select(Connection).where(
        Connection.user_id == current_user.id,
        Connection.platform_id == platform.id,
    )
    connection = db.execute(conn_stmt).scalar_one_or_none()

    if not connection:
        connection = Connection(
            user_id=current_user.id,
            platform_id=platform.id,
            connection_type="ACCOUNT_AGGREGATOR",
            connector_key="setu_aa",
            status="CONNECTING",
            provider="setu",
        )
        db.add(connection)
        db.flush()

    # 3. Create consent request via client
    client = SetuAAClient()
    req = SetuConsentRequest(
        customer_phone=payload.customer_phone,
        customer_vpa=payload.customer_vpa,
        fi_types=payload.fi_types,
        expiry_days=payload.expiry_days,
        redirect_url=payload.redirect_url,
    )

    try:
        consent_resp = await client.create_consent_request(req)
    except SetuConfigurationError as ce:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ce.safe_message)
    except SetuClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=e.safe_message)

    # 4. Record consent information on connection
    now = datetime.utcnow()
    connection.consent_id = consent_resp.id
    connection.consent_status = consent_resp.status
    connection.consent_created_at = consent_resp.created_at
    connection.consent_expires_at = now + timedelta(days=payload.expiry_days)
    connection.status = "CONNECTING"
    connection.provider_metadata = {
        "fi_types": payload.fi_types,
        "customer_phone": payload.customer_phone,
        "is_sandbox": True,
    }
    db.commit()

    return AAConsentCreateResponse(
        consent_id=consent_resp.id,
        url=consent_resp.url,
        status=consent_resp.status,
        created_at=consent_resp.created_at,
        connection_id=connection.id,
        is_sandbox=True,
    )


@router.get("/consent/{consent_id}", response_model=AAConsentStatusResponse)
async def get_consent_status(
    consent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves current authorization status for a consent request.
    Strictly verifies ownership by authenticated user.
    """
    stmt = select(Connection).where(
        Connection.consent_id == consent_id,
        Connection.user_id == current_user.id,
    )
    connection = db.execute(stmt).scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent session not found or unauthorized.",
        )

    client = SetuAAClient()
    try:
        status_dto = await client.get_consent_status(consent_id)
        connection.consent_status = status_dto.status
        if status_dto.status in ("ACTIVE", "AUTHORIZED"):
            connection.status = "CONNECTED"
        elif status_dto.status in ("REJECTED", "REVOKED", "EXPIRED"):
            connection.status = "DISCONNECTED"
        elif status_dto.status in ("ERROR", "FAILED"):
            connection.status = "ERROR"
        db.commit()
    except (SetuConsentRejectedError, SetuConsentExpiredError, SetuConsentRevokedError) as e:
        connection.consent_status = e.code
        connection.status = "DISCONNECTED"
        db.commit()
        return AAConsentStatusResponse(
            consent_id=consent_id,
            status=e.code,
            fi_types=[],
            connection_id=connection.id,
            is_sandbox=True,
        )
    except SetuClientError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=e.safe_message)

    return AAConsentStatusResponse(
        consent_id=status_dto.id,
        status=status_dto.status,
        fi_types=status_dto.fi_types,
        expires_at=status_dto.consent_expires_at,
        connection_id=connection.id,
        is_sandbox=True,
    )


@router.post("/consent/{consent_id}/sync", response_model=AASyncResponse)
async def sync_consent_data(
    consent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ingests sandbox financial data for an authorized consent session.
    Feeds normalized assets into SyncService and existing portfolio engine.
    """
    stmt = select(Connection).where(
        Connection.consent_id == consent_id,
        Connection.user_id == current_user.id,
    )
    connection = db.execute(stmt).scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent session not found or unauthorized.",
        )

    client = SetuAAClient()
    if client.use_mock:
        # In internal mock mode: advance mock consent to ACTIVE upon user sync trigger
        client.set_mock_consent_status(consent_id, "ACTIVE")
        connection.consent_status = "ACTIVE"
        connection.status = "CONNECTED"
        db.commit()
    else:
        # In real Setu mode: verify consent is ACTIVE or AUTHORIZED
        if connection.consent_status not in ("ACTIVE", "AUTHORIZED"):
            try:
                status_dto = await client.get_consent_status(consent_id)
                connection.consent_status = status_dto.status
                if status_dto.status in ("ACTIVE", "AUTHORIZED"):
                    connection.status = "CONNECTED"
                    db.commit()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot sync financial data: consent status is '{status_dto.status}'. Authorization must be completed first.",
                    )
            except (SetuConsentRejectedError, SetuConsentExpiredError, SetuConsentRevokedError) as e:
                connection.consent_status = e.code
                connection.status = "DISCONNECTED"
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot sync financial data: {e.safe_message}",
                )

    # Trigger SyncService
    result = await SyncService.sync_connection(
        connection_id=connection.id,
        user_id=current_user.id,
        db=db,
    )

    if result.status != "SUCCESS":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.safe_error_message or "Account Aggregator data sync failed.",
        )

    # Count accounts and holdings belonging to this connection
    acc_count = db.execute(
        select(Account).where(Account.connection_id == connection.id)
    ).scalars().all()

    hold_count = db.execute(
        select(Asset).where(Asset.platform_id == connection.platform_id, Asset.user_id == current_user.id)
    ).scalars().all()

    data_source_label = "SANDBOX_MOCK" if client.use_mock else "SETU_SANDBOX"

    return AASyncResponse(
        status="SUCCESS",
        records_processed=result.records_processed,
        records_created=result.records_created,
        records_updated=result.records_updated,
        completed_at=result.completed_at,
        connection_id=connection.id,
        accounts_discovered=len(acc_count),
        holdings_discovered=len(hold_count),
        is_sandbox=True,
        data_source=data_source_label,
    )


@router.get("/health")
async def check_setu_health():
    """
    Checks Setu AA connectivity and sandbox configuration.
    Safe diagnostic reporting without exposing secrets.
    """
    client = SetuAAClient()
    return await client.health_check()


@router.post("/callback")
@router.get("/callback")
async def handle_setu_callback(
    payload: Optional[Dict[str, Any]] = None,
    consent_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Handles Setu AA sandbox callback or redirection.
    Validates and updates consent status securely.
    """
    data = payload or {}
    cid = consent_id or data.get("consentId") or data.get("id")
    st = (status or data.get("status") or "ACTIVE").upper()

    if cid:
        stmt = select(Connection).where(Connection.consent_id == cid)
        connection = db.execute(stmt).scalar_one_or_none()
        if connection:
            connection.consent_status = st
            if st in ("ACTIVE", "AUTHORIZED"):
                connection.status = "CONNECTED"
            elif st in ("REJECTED", "REVOKED", "EXPIRED"):
                connection.status = "DISCONNECTED"
            db.commit()

    client = SetuAAClient()
    return await client.handle_callback({"consentId": cid, "status": st})


@router.get("/{connection_id}/status", response_model=AAConnectionStatus)
def get_connection_status(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns connection and consent status for an Account Aggregator connection.
    Enforces user isolation.
    """
    stmt = (
        select(Connection, Platform.name.label("platform_name"))
        .join(Platform, Platform.id == Connection.platform_id)
        .where(
            Connection.id == connection_id,
            Connection.user_id == current_user.id,
        )
    )
    row = db.execute(stmt).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found or unauthorized.",
        )

    conn, plat_name = row
    return AAConnectionStatus(
        connection_id=conn.id,
        platform_name=plat_name,
        status=conn.status,
        consent_id=conn.consent_id,
        consent_status=conn.consent_status,
        last_synced_at=conn.last_synced_at,
        last_data_fetch=conn.last_data_fetch,
        is_sandbox=True,
    )


@router.post("/{connection_id}/disconnect")
async def disconnect_aa_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Disconnects Account Aggregator connection and marks consent as REVOKED.
    Enforces user isolation.
    """
    stmt = select(Connection).where(
        Connection.id == connection_id,
        Connection.user_id == current_user.id,
    )
    connection = db.execute(stmt).scalar_one_or_none()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found or unauthorized.",
        )

    connection.status = "DISCONNECTED"
    connection.consent_status = "REVOKED"
    db.commit()

    return {
        "status": "DISCONNECTED",
        "connection_id": str(connection.id),
        "message": "Account Aggregator sandbox connection disconnected.",
    }
