import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.connection import Connection
from app.models.sync_log import SyncLog
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionStatusResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
)
from app.schemas.sync_log import SyncLogResponse
from app.connectors.dtos import SyncResult
from app.dependencies import get_current_user
from app.services.connection_service import ConnectionService
from app.connectors.sync_service import SyncService

router = APIRouter(prefix="/api/connections", tags=["Connections"])


@router.get("", response_model=List[ConnectionResponse])
def list_user_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all platform connections belonging to the authenticated user."""
    stmt = (
        select(Connection)
        .where(Connection.user_id == current_user.id)
        .order_by(Connection.created_at.desc())
    )
    connections = list(db.execute(stmt).scalars().all())
    return [ConnectionResponse.model_validate(c) for c in connections]


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    payload: ConnectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Connect a financial platform.
    Strictly verifies connector availability; unintegrated connectors (COMING_SOON) are rejected.
    For live direct connectors (e.g. Groww), credentials are authenticated and encrypted.
    """
    conn = await ConnectionService.create_connection(user_id=current_user.id, data=payload, db=db)
    return ConnectionResponse.model_validate(conn)


@router.post("/test", response_model=ConnectionTestResponse)
async def test_connection(
    payload: ConnectionTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Test provider credentials without creating or modifying a connection record.
    """
    return await ConnectionService.test_connection(user_id=current_user.id, data=payload, db=db)


@router.get("/{connection_id}", response_model=ConnectionResponse)
def get_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve connection details by ID (isolated to authenticated user)."""
    stmt = select(Connection).where(Connection.id == connection_id, Connection.user_id == current_user.id)
    conn = db.execute(stmt).scalar_one_or_none()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONNECTION_NOT_FOUND", "message": "Connection does not exist"}
        )
    return ConnectionResponse.model_validate(conn)


@router.delete("/{connection_id}", response_model=ConnectionResponse)
def disconnect_connection(
    connection_id: uuid.UUID,
    purge_data: bool = Query(False, description="Whether to permanently remove all associated assets/records"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnects a platform connection and revokes stored credentials.
    Historical financial records are preserved unless purge_data=True is specified.
    """
    conn = ConnectionService.disconnect(
        user_id=current_user.id, connection_id=connection_id, db=db, purge_data=purge_data
    )
    if purge_data:
        return None
    return ConnectionResponse.model_validate(conn)


@router.post("/{connection_id}/sync", response_model=SyncResult)
async def sync_connection(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger manual or periodic synchronization for this connection.
    Executes idempotent upsert and portfolio recalculation.
    """
    conn_stmt = select(Connection).where(
        Connection.id == connection_id, Connection.user_id == current_user.id
    )
    conn = db.execute(conn_stmt).scalar_one_or_none()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONNECTION_NOT_FOUND", "message": "Connection does not exist"}
        )

    result = await SyncService.sync_connection(
        connection_id=connection_id,
        user_id=current_user.id,
        db=db,
    )
    return result


@router.get("/{connection_id}/status", response_model=ConnectionStatusResponse)
def get_connection_status(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve live connection status, sync results, and recent audit logs."""
    stmt = select(Connection).where(Connection.id == connection_id, Connection.user_id == current_user.id)
    conn = db.execute(stmt).scalar_one_or_none()
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONNECTION_NOT_FOUND", "message": "Connection does not exist"}
        )

    logs_stmt = (
        select(SyncLog)
        .where(SyncLog.connection_id == connection_id)
        .order_by(SyncLog.started_at.desc())
        .limit(10)
    )
    logs = list(db.execute(logs_stmt).scalars().all())

    return ConnectionStatusResponse(
        id=conn.id,
        platform_id=conn.platform_id,
        connection_type=conn.connection_type,
        connector_key=conn.connector_key,
        status=conn.status,
        last_synced_at=conn.last_synced_at,
        last_sync_status=conn.last_sync_status,
        last_sync_error=conn.last_sync_error,
        recent_logs=[SyncLogResponse.model_validate(log) for log in logs],
    )
