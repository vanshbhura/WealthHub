import os
import uuid
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.connectors.brokers.groww_client import GrowwApiClient
from app.connectors.brokers.groww import GrowwConnector
from app.connectors.credentials import credential_store, FernetCredentialStore
from app.connectors.exceptions import (
    AuthFailedError,
    TokenExpiredError,
    RateLimitedError,
    ProviderUnavailableError,
    InvalidResponseError,
)
from app.connectors.sync_service import SyncService
from app.models.platform import Platform
from app.models.connection import Connection
from app.models.account import Account
from app.models.asset import Asset
from app.models.transaction import Transaction
from app.services.portfolio_service import PortfolioService


# --- FIXTURES ---

@pytest.fixture
def auth_headers(client: TestClient) -> dict:
    email = f"groww_user_{uuid.uuid4().hex[:6]}@example.com"
    reg_res = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Groww Investor"
    })
    token = reg_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user_headers(client: TestClient) -> dict:
    email = f"other_{uuid.uuid4().hex[:6]}@example.com"
    reg_res = client.post("/api/auth/register", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Other User"
    })
    token = reg_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def groww_platform(db_session: Session) -> Platform:
    stmt = select(Platform).where(Platform.slug == "groww")
    plat = db_session.execute(stmt).scalar_one_or_none()
    if not plat:
        plat = Platform(
            id=uuid.uuid4(),
            name="Groww",
            slug="groww",
            category="BROKER",
            integration_type="DIRECT_API",
            is_active=True
        )
        db_session.add(plat)
        db_session.commit()
        db_session.refresh(plat)
    return plat


MOCK_PROFILE_PAYLOAD = {
    "status": "SUCCESS",
    "payload": {
        "vendor_user_id": "groww-user-uuid-12345",
        "ucc": "924189",
        "nse_enabled": True,
        "bse_enabled": True,
        "ddpi_enabled": False,
        "active_segments": ["CASH", "FNO"]
    }
}

MOCK_HOLDINGS_PAYLOAD = {
    "status": "SUCCESS",
    "payload": {
        "holdings": [
            {
                "isin": "INE002A01018",
                "trading_symbol": "RELIANCE",
                "quantity": 10,
                "average_price": 2850.50,
                "ltp": 2900.00,
                "pledge_quantity": 0,
                "demat_locked_quantity": 0,
                "groww_locked_quantity": 0,
                "demat_free_quantity": 10
            },
            {
                "isin": "INE009A01021",
                "trading_symbol": "INFY",
                "quantity": 25,
                "average_price": 1450.00,
                "ltp": 1500.00,
                "pledge_quantity": 0,
                "demat_locked_quantity": 0,
                "groww_locked_quantity": 0,
                "demat_free_quantity": 25
            }
        ]
    }
}

MOCK_POSITIONS_PAYLOAD = {
    "status": "SUCCESS",
    "payload": {
        "positions": [
            {
                "isin": "INE040A01034",
                "trading_symbol": "HDFCBANK",
                "quantity": 5,
                "average_price": 1600.00,
                "ltp": 1620.00
            }
        ]
    }
}

MOCK_MARGIN_PAYLOAD = {
    "status": "SUCCESS",
    "payload": {
        "clear_cash": 12500.00,
        "net_margin_used": 35000.00,
        "brokerage_and_charges": 150.00,
        "collateral_available": 50000.00,
        "adhoc_margin": 0.0
    }
}


# --- 1. GROWW API CLIENT TESTS ---

def test_groww_client_headers_and_initialization():
    """Verify GrowwApiClient properly constructs headers without leaking token."""
    client = GrowwApiClient(access_token="test_secret_token_123")
    headers = client._headers

    assert headers["Accept"] == "application/json"
    assert headers["Authorization"] == "Bearer test_secret_token_123"
    assert headers["X-API-VERSION"] == "1.0"

    with pytest.raises(AuthFailedError):
        GrowwApiClient(access_token="")


@pytest.mark.anyio
async def test_groww_client_get_user_profile_success():
    """Verify get_user_profile parses valid response correctly."""
    client = GrowwApiClient(access_token="valid_token")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_PROFILE_PAYLOAD

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        res = await client.get_user_profile()
        assert res["status"] == "SUCCESS"
        assert res["payload"]["ucc"] == "924189"
        assert "CASH" in res["payload"]["active_segments"]


@pytest.mark.anyio
async def test_groww_client_auth_failure_401():
    """Verify HTTP 401 raises AuthFailedError."""
    client = GrowwApiClient(access_token="bad_token")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"message": "Invalid token"}

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        with pytest.raises(AuthFailedError) as exc:
            await client.get_user_profile()
        assert "authentication failed" in str(exc.value).lower()


@pytest.mark.anyio
async def test_groww_client_token_expired_detection():
    """Verify expired token message raises TokenExpiredError."""
    client = GrowwApiClient(access_token="expired_token")

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"message": "Token expired"}

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        with pytest.raises(TokenExpiredError):
            await client.get_holdings()


@pytest.mark.anyio
async def test_groww_client_rate_limited_429():
    """Verify HTTP 429 raises RateLimitedError after retry budget exhausted."""
    client = GrowwApiClient(access_token="rate_limited_token", max_retries=1)

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.headers = {"Retry-After": "1"}

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        with pytest.raises(RateLimitedError):
            await client.get_holdings()


@pytest.mark.anyio
async def test_groww_client_provider_unavailable_500():
    """Verify HTTP 500 raises ProviderUnavailableError."""
    client = GrowwApiClient(access_token="token", max_retries=1)

    mock_resp = MagicMock()
    mock_resp.status_code = 503

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        with pytest.raises(ProviderUnavailableError):
            await client.get_holdings()


@pytest.mark.anyio
async def test_groww_client_malformed_json_response():
    """Verify malformed JSON or failure status raises InvalidResponseError."""
    client = GrowwApiClient(access_token="token", max_retries=0)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "FAILURE", "message": "Backend query failed"}

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        with pytest.raises(InvalidResponseError):
            await client.get_holdings()


# --- 2. GROWW CONNECTOR NORMALIZATION TESTS ---

@pytest.mark.anyio
async def test_groww_connector_holdings_normalization():
    """Verify GrowwConnector correctly maps raw holdings into NormalizedHolding DTOs."""
    connector = GrowwConnector()
    assert connector.is_available() is True

    mock_client = MagicMock(spec=GrowwApiClient)
    mock_client.get_holdings = AsyncMock(return_value=MOCK_HOLDINGS_PAYLOAD)

    fake_conn = MagicMock()
    fake_conn.user_id = uuid.uuid4()
    fake_conn.id = uuid.uuid4()
    fake_conn.external_account_reference = "924189"

    with patch.object(connector, "_get_client_for_connection", return_value=mock_client):
        holdings = await connector.get_holdings(fake_conn)
        assert len(holdings) == 2

        # 1. Reliance
        rel = holdings[0].asset
        assert rel.symbol == "RELIANCE"
        assert rel.identifier == "INE002A01018"
        assert rel.asset_type == "STOCK"
        assert rel.quantity == 10
        assert rel.average_buy_price == 2850.50
        assert rel.invested_amount == 28505.00
        assert rel.current_price == 2900.00
        assert rel.current_value == 29000.00

        # 2. Infosys
        infy = holdings[1].asset
        assert infy.symbol == "INFY"
        assert infy.quantity == 25
        assert infy.invested_amount == 36250.00
        assert infy.current_value == 37500.00


@pytest.mark.anyio
async def test_groww_connector_balance_normalization_cash_vs_margin():
    """
    CRITICAL: Verify settled clear cash is mapped, and margin availability is NOT added as wealth.
    """
    connector = GrowwConnector()
    mock_client = MagicMock(spec=GrowwApiClient)
    mock_client.get_margin_details = AsyncMock(return_value=MOCK_MARGIN_PAYLOAD)

    fake_conn = MagicMock()
    fake_conn.user_id = uuid.uuid4()
    fake_conn.id = uuid.uuid4()

    with patch.object(connector, "_get_client_for_connection", return_value=mock_client):
        balances = await connector.get_balances(fake_conn)
        assert len(balances) == 1
        b = balances[0]
        # Only clear_cash (12500) should be available cash
        assert b.available_cash == 12500.00
        # Collateral (50000) and net margin (35000) MUST NOT inflate cash balance
        assert b.total_balance == 12500.00


@pytest.mark.anyio
async def test_groww_connector_connect_and_disconnect_credentials():
    """Verify connect validates profile and securely stores encrypted secrets."""
    connector = GrowwConnector()
    user_id = uuid.uuid4()
    conn_id = uuid.uuid4()

    mock_client = MagicMock(spec=GrowwApiClient)
    mock_client.get_user_profile = AsyncMock(return_value=MOCK_PROFILE_PAYLOAD)

    with patch("app.connectors.brokers.groww.GrowwApiClient", return_value=mock_client):
        # 1. Connect
        res = await connector.connect(
            user_id=user_id,
            credentials={"access_token": "secret_access_token_xyz"},
            connection_id=conn_id
        )
        assert res["status"] == "CONNECTED"
        assert res["ucc"] == "924189"

        # Verify token is encrypted in credential store
        stored = credential_store.get_secret(user_id, conn_id, "access_token")
        assert stored == "secret_access_token_xyz"

        # 2. Disconnect
        await connector.disconnect(user_id=user_id, connection_id=conn_id)
        assert credential_store.get_secret(user_id, conn_id, "access_token") is None


# --- 3. API ENDPOINTS & FLOW TESTS ---

def test_groww_test_connection_endpoint(client: TestClient, auth_headers: dict, groww_platform: Platform):
    """Verify POST /api/connections/test validates credentials."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_PROFILE_PAYLOAD

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        payload = {
            "platform_id": str(groww_platform.id),
            "connector_key": "groww_direct",
            "credentials": {"access_token": "test_token"}
        }
        res = client.post("/api/connections/test", json=payload, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["ucc"] == "924189"


def test_groww_connection_creation_flow(client: TestClient, auth_headers: dict, groww_platform: Platform):
    """Verify creating a Groww connection stores credentials and establishes CONNECTED state."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_PROFILE_PAYLOAD

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        payload = {
            "platform_id": str(groww_platform.id),
            "connection_type": "DIRECT_API",
            "connector_key": "groww_direct",
            "credentials": {"access_token": "groww_live_token_789"}
        }
        res = client.post("/api/connections", json=payload, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "CONNECTED"
        assert data["connection_type"] == "DIRECT_API"
        assert data["external_account_reference"] == "924189"


# --- 4. END-TO-END SYNC & PORTFOLIO ENGINE TESTS ---

@pytest.mark.anyio
async def test_groww_sync_pipeline_end_to_end(
    client: TestClient, auth_headers: dict, groww_platform: Platform, db_session: Session
):
    """
    End-to-end test: Connect Groww -> Sync -> Verify Assets, Holdings, Cash, and Portfolio Engine Totals.
    """
    mock_profile = MagicMock(status_code=200, json=lambda: MOCK_PROFILE_PAYLOAD)
    mock_holdings = MagicMock(status_code=200, json=lambda: MOCK_HOLDINGS_PAYLOAD)
    mock_positions = MagicMock(status_code=200, json=lambda: MOCK_POSITIONS_PAYLOAD)
    mock_margin = MagicMock(status_code=200, json=lambda: MOCK_MARGIN_PAYLOAD)

    async def mock_request(method, url, **kwargs):
        if "user/detail" in url:
            return mock_profile
        elif "holdings/user" in url:
            return mock_holdings
        elif "positions/user" in url:
            return mock_positions
        elif "margins/detail/user" in url:
            return mock_margin
        return MagicMock(status_code=404)

    with patch.object(httpx.AsyncClient, "request", AsyncMock(side_effect=mock_request)):
        # 1. Connect
        create_res = client.post("/api/connections", json={
            "platform_id": str(groww_platform.id),
            "connection_type": "DIRECT_API",
            "connector_key": "groww_direct",
            "credentials": {"access_token": "valid_token"}
        }, headers=auth_headers)
        assert create_res.status_code == 201
        conn_id = create_res.json()["id"]

        # 2. Trigger Sync
        sync_res = client.post(f"/api/connections/{conn_id}/sync", headers=auth_headers)
        assert sync_res.status_code == 200
        stats = sync_res.json()
        assert stats["status"] == "SUCCESS"
        assert stats["records_processed"] >= 3

        # 3. Verify Portfolio Summary via API
        summary_res = client.get("/api/portfolio/summary", headers=auth_headers)
        assert summary_res.status_code == 200
        summary = summary_res.json()

        # Calculation check:
        # Reliance: 10 * 2900 = 29,000 (invested 28,505)
        # Infosys:  25 * 1500 = 37,500 (invested 36,250)
        # HDFC Bank cash position: 5 * 1620 = 8,100 (invested 8,000)
        # Total stock current value = 29000 + 37500 + 8100 = 74,600
        # Total stock invested value = 28505 + 36250 + 8000 = 72,755
        # Profit / Loss = 74,600 - 72,755 = 1,845
        assert summary["total_wealth"] == pytest.approx(74600.00, 0.01)
        assert summary["invested_value"] == pytest.approx(72755.00, 0.01)
        assert summary["profit_loss"] == pytest.approx(1845.00, 0.01)


@pytest.mark.anyio
async def test_groww_idempotent_sync_no_duplicates(
    client: TestClient, auth_headers: dict, groww_platform: Platform, db_session: Session
):
    """
    CRITICAL: Running Groww sync twice must NOT duplicate assets or inflate portfolio values.
    """
    mock_profile = MagicMock(status_code=200, json=lambda: MOCK_PROFILE_PAYLOAD)
    mock_holdings = MagicMock(status_code=200, json=lambda: MOCK_HOLDINGS_PAYLOAD)
    mock_positions = MagicMock(status_code=200, json=lambda: {"status": "SUCCESS", "payload": {"positions": []}})
    mock_margin = MagicMock(status_code=200, json=lambda: MOCK_MARGIN_PAYLOAD)

    async def mock_request(method, url, **kwargs):
        if "user/detail" in url:
            return mock_profile
        elif "holdings/user" in url:
            return mock_holdings
        elif "positions/user" in url:
            return mock_positions
        elif "margins/detail/user" in url:
            return mock_margin
        return MagicMock(status_code=404)

    with patch.object(httpx.AsyncClient, "request", AsyncMock(side_effect=mock_request)):
        # Connect
        create_res = client.post("/api/connections", json={
            "platform_id": str(groww_platform.id),
            "connection_type": "DIRECT_API",
            "connector_key": "groww_direct",
            "credentials": {"access_token": "valid_token"}
        }, headers=auth_headers)
        conn_id = create_res.json()["id"]

        # First sync
        sync1 = client.post(f"/api/connections/{conn_id}/sync", headers=auth_headers)
        assert sync1.status_code == 200
        created1 = sync1.json()["records_created"]

        summary1 = client.get("/api/portfolio/summary", headers=auth_headers).json()

        # Second sync
        sync2 = client.post(f"/api/connections/{conn_id}/sync", headers=auth_headers)
        assert sync2.status_code == 200
        created2 = sync2.json()["records_created"]

        summary2 = client.get("/api/portfolio/summary", headers=auth_headers).json()

        # Second sync creates 0 new records
        assert created2 == 0
        # Total wealth remains identical
        assert summary1["total_wealth"] == summary2["total_wealth"]


@pytest.mark.anyio
async def test_groww_import_and_live_coexistence_no_double_counting(
    client: TestClient, auth_headers: dict, groww_platform: Platform, db_session: Session
):
    """
    Verify coexistence of Statement Import and Live API:
    If a user previously imported a Reliance holding from a statement,
    a subsequent Live API sync updates Reliance rather than creating a duplicate asset or doubling wealth.
    """
    # 1. Simulate existing imported statement with Reliance
    user_me = client.get("/api/auth/me", headers=auth_headers).json()
    user_id = uuid.UUID(user_me["id"])

    # Create prior imported asset for Reliance
    existing_asset = Asset(
        user_id=user_id,
        platform_id=groww_platform.id,
        name="RELIANCE",
        symbol="RELIANCE",
        identifier="INE002A01018",
        asset_type="STOCK",
        quantity=10,
        average_buy_price=2800.0,
        invested_amount=28000.0,
        current_price=2800.0,
        current_value=28000.0,
        data_source="IMPORT",
    )
    db_session.add(existing_asset)
    db_session.commit()

    # 2. Now run Live API sync with updated Reliance price (2900)
    mock_profile = MagicMock(status_code=200, json=lambda: MOCK_PROFILE_PAYLOAD)
    # Return only Reliance in live holdings
    mock_holdings = MagicMock(status_code=200, json=lambda: {
        "status": "SUCCESS",
        "payload": {
            "holdings": [
                {
                    "isin": "INE002A01018",
                    "trading_symbol": "RELIANCE",
                    "quantity": 10,
                    "average_price": 2850.50,
                    "ltp": 2900.00
                }
            ]
        }
    })
    mock_positions = MagicMock(status_code=200, json=lambda: {"status": "SUCCESS", "payload": {"positions": []}})
    mock_margin = MagicMock(status_code=200, json=lambda: {"status": "SUCCESS", "payload": {"clear_cash": 0.0}})

    async def mock_request(method, url, **kwargs):
        if "user/detail" in url:
            return mock_profile
        elif "holdings/user" in url:
            return mock_holdings
        elif "positions/user" in url:
            return mock_positions
        elif "margins/detail/user" in url:
            return mock_margin
        return MagicMock(status_code=404)

    with patch.object(httpx.AsyncClient, "request", AsyncMock(side_effect=mock_request)):
        create_res = client.post("/api/connections", json={
            "platform_id": str(groww_platform.id),
            "connection_type": "DIRECT_API",
            "connector_key": "groww_direct",
            "credentials": {"access_token": "token"}
        }, headers=auth_headers)
        conn_id = create_res.json()["id"]

        sync_res = client.post(f"/api/connections/{conn_id}/sync", headers=auth_headers)
        assert sync_res.status_code == 200

        # Check total assets in DB: should be exactly 1 Reliance asset, NOT 2!
        stmt = select(Asset).where(Asset.user_id == user_id, Asset.identifier == "INE002A01018")
        assets = list(db_session.execute(stmt).scalars().all())
        assert len(assets) == 1
        assert assets[0].current_value == 29000.0  # Updated to live market value


@pytest.mark.anyio
async def test_groww_token_expired_sets_auth_required(
    client: TestClient, auth_headers: dict, groww_platform: Platform
):
    """
    Verify that an expired token during sync transitions connection to AUTH_REQUIRED.
    """
    mock_profile = MagicMock(status_code=200, json=lambda: MOCK_PROFILE_PAYLOAD)
    mock_expired = MagicMock(status_code=401, json=lambda: {"message": "Access token expired"})

    async def mock_request(method, url, **kwargs):
        if "user/detail" in url:
            return mock_profile
        return mock_expired

    with patch.object(httpx.AsyncClient, "request", AsyncMock(side_effect=mock_request)):
        # 1. Connect
        create_res = client.post("/api/connections", json={
            "platform_id": str(groww_platform.id),
            "connection_type": "DIRECT_API",
            "connector_key": "groww_direct",
            "credentials": {"access_token": "expired_soon_token"}
        }, headers=auth_headers)
        conn_id = create_res.json()["id"]

        # 2. Sync fails due to expired token
        sync_res = client.post(f"/api/connections/{conn_id}/sync", headers=auth_headers)
        assert sync_res.status_code == 200
        assert sync_res.json()["status"] == "SYNC_FAILED"

        # 3. Connection status must now be AUTH_REQUIRED
        conn_res = client.get(f"/api/connections/{conn_id}", headers=auth_headers)
        assert conn_res.status_code == 200
        assert conn_res.json()["status"] == "AUTH_REQUIRED"


# --- 5. OPT-IN REAL GROWW API INTEGRATION TEST ---

@pytest.mark.skipif(
    not os.getenv("GROWW_LIVE_TEST"),
    reason="Opt-in live Groww integration test. Enable by setting GROWW_LIVE_TEST=1 and GROWW_ACCESS_TOKEN."
)
@pytest.mark.anyio
async def test_live_groww_api_read_only():
    """
    Optional live integration test that talks directly to official Groww Trading API.
    Does NOT run in standard CI or test suites.
    """
    token = os.getenv("GROWW_ACCESS_TOKEN")
    assert token, "GROWW_ACCESS_TOKEN required when GROWW_LIVE_TEST=1"

    client = GrowwApiClient(access_token=token)
    profile = await client.get_user_profile()
    assert profile["status"] == "SUCCESS"

    holdings = await client.get_holdings()
    assert holdings["status"] == "SUCCESS"

    margins = await client.get_margin_details()
    assert margins["status"] == "SUCCESS"
