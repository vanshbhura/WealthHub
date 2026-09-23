import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.main import app
from app.database import get_db
from app.models.platform import Platform


@pytest.fixture
def auth_headers(client: TestClient) -> dict:
    # Register and login user A
    email = f"user_a_{uuid.uuid4().hex[:6]}@example.com"
    reg_res = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "User Alpha"
    })
    token = reg_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_user_b(client: TestClient) -> dict:
    # Register and login user B
    email = f"user_b_{uuid.uuid4().hex[:6]}@example.com"
    reg_res = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "User Beta"
    })
    token = reg_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_platform(db_session: Session) -> Platform:
    stmt = select(Platform).where(Platform.slug == "groww")
    plat = db_session.execute(stmt).scalar_one_or_none()
    if not plat:
        plat = Platform(
            id=uuid.uuid4(),
            name="Groww",
            slug="groww",
            category="BROKER",
            integration_type="STATEMENT_IMPORT",
            is_active=True
        )
        db_session.add(plat)
        db_session.commit()
        db_session.refresh(plat)
    return plat


def test_get_platform_connectors(client: TestClient, sample_platform: Platform):
    """Verify GET /api/platforms/{id}/connectors returns methods with accurate statuses."""
    res = client.get(f"/api/platforms/{sample_platform.slug}/connectors")
    assert res.status_code == 200
    connectors = res.json()
    assert len(connectors) >= 2

    # Check Manual is AVAILABLE
    manual = next((c for c in connectors if c["connector_type"] == "MANUAL"), None)
    assert manual is not None
    assert manual["status"] == "AVAILABLE"
    assert manual["is_enabled"] is True

    # Check Direct API for Groww is now AVAILABLE
    direct = next((c for c in connectors if c["connector_type"] == "DIRECT_API"), None)
    if direct:
        assert direct["status"] == "AVAILABLE"
        assert direct["is_enabled"] is True


def test_manual_connection_creation(client: TestClient, auth_headers: dict, sample_platform: Platform):
    """Verify user can create a MANUAL connection."""
    payload = {
        "platform_id": str(sample_platform.id),
        "connection_type": "MANUAL",
        "connector_key": "manual_asset"
    }
    res = client.post("/api/connections", json=payload, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["platform_id"] == str(sample_platform.id)
    assert data["connection_type"] == "MANUAL"
    assert data["status"] == "CONNECTED"


def test_coming_soon_connection_is_rejected(client: TestClient, auth_headers: dict, db_session: Session):
    """Verify attempting to establish a live connection to a COMING_SOON connector is rejected."""
    stmt = select(Platform).where(Platform.slug == "zerodha")
    plat = db_session.execute(stmt).scalar_one_or_none()
    if not plat:
        plat = Platform(
            id=uuid.uuid4(),
            name="Zerodha",
            slug="zerodha",
            category="BROKER",
            integration_type="STATEMENT_IMPORT",
            is_active=True
        )
        db_session.add(plat)
        db_session.commit()
        db_session.refresh(plat)

    payload = {
        "platform_id": str(plat.id),
        "connection_type": "DIRECT_API",
        "connector_key": "zerodha_kite"
    }
    res = client.post("/api/connections", json=payload, headers=auth_headers)
    assert res.status_code == 400
    err = res.json()["error"]
    assert err["code"] == "CONNECTOR_NOT_AVAILABLE"


def test_user_isolation_and_security(
    client: TestClient, auth_headers: dict, auth_headers_user_b: dict, sample_platform: Platform
):
    """Verify User B cannot view, modify, or sync User A's connections."""
    # Create connection for User A
    create_res = client.post("/api/connections", json={
        "platform_id": str(sample_platform.id),
        "connection_type": "MANUAL"
    }, headers=auth_headers)
    conn_id = create_res.json()["id"]

    # User A can access
    get_res = client.get(f"/api/connections/{conn_id}", headers=auth_headers)
    assert get_res.status_code == 200

    # User B cannot access User A's connection
    unauth_get = client.get(f"/api/connections/{conn_id}", headers=auth_headers_user_b)
    assert unauth_get.status_code == 404

    # User B cannot sync User A's connection
    unauth_sync = client.post(f"/api/connections/{conn_id}/sync", headers=auth_headers_user_b)
    assert unauth_sync.status_code in (404, 500)

    # User B cannot disconnect User A's connection
    unauth_del = client.delete(f"/api/connections/{conn_id}", headers=auth_headers_user_b)
    assert unauth_del.status_code == 404


def test_disconnect_and_reconnect_lifecycle(
    client: TestClient, auth_headers: dict, sample_platform: Platform
):
    """Verify disconnect sets DISCONNECTED status and reconnect preserves/re-enables it."""
    # Create
    create_res = client.post("/api/connections", json={
        "platform_id": str(sample_platform.id),
        "connection_type": "MANUAL"
    }, headers=auth_headers)
    conn_id = create_res.json()["id"]

    # Disconnect
    del_res = client.delete(f"/api/connections/{conn_id}", headers=auth_headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "DISCONNECTED"

    # Status check
    status_res = client.get(f"/api/connections/{conn_id}/status", headers=auth_headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "DISCONNECTED"

    # Reconnect
    reconnect_res = client.post("/api/connections", json={
        "platform_id": str(sample_platform.id),
        "connection_type": "MANUAL"
    }, headers=auth_headers)
    assert reconnect_res.status_code == 201
    assert reconnect_res.json()["id"] == conn_id
    assert reconnect_res.json()["status"] == "CONNECTED"
