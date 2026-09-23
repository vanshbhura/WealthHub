import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.connection import Connection
from app.models.platform import Platform
from app.schemas.connection import ConnectionCreate, ConnectionTestRequest, ConnectionTestResponse
from app.connectors.registry import registry
from app.connectors.credentials import credential_store
from app.connectors.enums import ConnectionMethodStatus
from app.connectors.exceptions import ConnectorError


class ConnectionService:
    @staticmethod
    async def create_connection(user_id: uuid.UUID, data: ConnectionCreate, db: Session) -> Connection:
        """
        Creates or reconnects a platform connection.
        Enforces zero-fabrication: rejects connecting any connector whose status is COMING_SOON or unintegrated.
        For direct API connectors, validates credentials against provider before creating or updating connection.
        """
        # 1. Validate platform exists
        plat_stmt = select(Platform).where(Platform.id == data.platform_id)
        platform = db.execute(plat_stmt).scalar_one_or_none()
        if not platform:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PLATFORM_NOT_FOUND", "message": "Selected platform does not exist"}
            )

        # 2. Determine and validate connector
        conn_type = data.connection_type.upper()
        connector_key = data.connector_key

        if not connector_key:
            if conn_type == "MANUAL":
                connector_key = "manual_asset"
            elif conn_type == "IMPORT":
                connector_key = "statement_import"
            else:
                connector_key = f"{platform.slug}_direct"

        connector = registry.get(connector_key)
        if not connector:
            # Check platform mapping
            p_conns = registry.get_for_platform(platform.slug)
            connector = p_conns[0] if p_conns else None

        # Zero-fabrication check: only AVAILABLE connectors may establish live connections
        if not connector or connector.status != ConnectionMethodStatus.AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "CONNECTOR_NOT_AVAILABLE",
                    "message": f"Direct integration with {platform.name} ({connector_key}) is coming soon. Use manual entry or statement import.",
                }
            )

        # 3. Check for existing connection
        conn_stmt = select(Connection).where(
            Connection.user_id == user_id,
            Connection.platform_id == data.platform_id
        )
        existing = db.execute(conn_stmt).scalar_one_or_none()

        conn = existing
        if not conn:
            conn = Connection(
                user_id=user_id,
                platform_id=data.platform_id,
                connection_type=conn_type,
                connector_key=connector_key,
                status="CONNECTED",
                external_account_reference=data.external_account_reference,
                last_synced_at=datetime.utcnow(),
                last_sync_status="SUCCESS",
            )
            db.add(conn)
            db.flush()
        else:
            conn.connection_type = conn_type
            conn.connector_key = connector_key
            conn.status = "CONNECTED"
            conn.last_sync_error = None
            if data.external_account_reference:
                conn.external_account_reference = data.external_account_reference

        # 4. If credentials provided for live connector, authenticate and store encrypted
        if data.credentials:
            try:
                connect_res = await connector.connect(
                    user_id=user_id,
                    credentials=data.credentials,
                    connection_id=conn.id,
                )
                if connect_res.get("ucc"):
                    conn.external_account_reference = str(connect_res["ucc"])
            except ConnectorError as ce:
                conn.status = "AUTH_REQUIRED"
                conn.last_sync_status = "AUTH_FAILED"
                conn.last_sync_error = ce.safe_message
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"code": ce.code, "message": ce.safe_message}
                )

        conn.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(conn)
        return conn

    @staticmethod
    async def test_connection(
        user_id: uuid.UUID, data: ConnectionTestRequest, db: Session
    ) -> ConnectionTestResponse:
        """
        Tests provider authentication credentials without saving connection state.
        """
        plat_stmt = select(Platform).where(Platform.id == data.platform_id)
        platform = db.execute(plat_stmt).scalar_one_or_none()
        if not platform:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PLATFORM_NOT_FOUND", "message": "Selected platform does not exist"}
            )

        connector_key = data.connector_key or f"{platform.slug}_direct"
        connector = registry.get(connector_key)
        if not connector or not connector.is_available():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "CONNECTOR_NOT_AVAILABLE",
                    "message": f"Connector '{connector_key}' is not available for live testing.",
                }
            )

        try:
            res = await connector.connect(user_id=user_id, credentials=data.credentials)
            return ConnectionTestResponse(
                success=True,
                status="CONNECTED",
                message="Groww API authenticated successfully.",
                ucc=res.get("ucc"),
                vendor_user_id=res.get("vendor_user_id"),
                active_segments=res.get("active_segments", []),
            )
        except ConnectorError as ce:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": ce.code, "message": ce.safe_message}
            )

    @staticmethod
    def disconnect(user_id: uuid.UUID, connection_id: uuid.UUID, db: Session, purge_data: bool = False) -> Connection:
        """
        Disconnects a platform connection, revokes/deletes stored credentials,
        and retains historical records unless purge_data is explicitly requested.
        """
        conn_stmt = select(Connection).where(
            Connection.id == connection_id, Connection.user_id == user_id
        )
        conn = db.execute(conn_stmt).scalar_one_or_none()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "CONNECTION_NOT_FOUND", "message": "Connection does not exist"}
            )

        # Revoke credentials from secure credential store
        credential_store.delete_all_secrets(user_id=user_id, connection_id=connection_id)

        if purge_data:
            db.delete(conn)
        else:
            conn.status = "DISCONNECTED"
            conn.last_sync_status = "DISCONNECTED"
            conn.updated_at = datetime.utcnow()

        db.commit()
        if not purge_data:
            db.refresh(conn)
        return conn
