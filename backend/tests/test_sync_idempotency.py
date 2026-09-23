import pytest
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User
from app.models.platform import Platform
from app.models.connection import Connection
from app.models.account import Account
from app.models.asset import Asset
from app.models.transaction import Transaction
from app.connectors.sync_service import SyncService
from app.connectors.testing.mock import MockConnector
from app.connectors.exceptions import RateLimitedError
from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectionMethodStatus


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"sync_user_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fakehash",
        full_name="Sync Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_platform(db_session: Session) -> Platform:
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


@pytest.fixture
def test_connection(db_session: Session, test_user: User, test_platform: Platform) -> Connection:
    conn = Connection(
        id=uuid.uuid4(),
        user_id=test_user.id,
        platform_id=test_platform.id,
        connection_type="DIRECT_API",
        connector_key="mock_test_connector",
        status="CONNECTED",
    )
    db_session.add(conn)
    db_session.commit()
    db_session.refresh(conn)
    return conn


@pytest.mark.anyio
async def test_idempotent_sync_pipeline(
    db_session: Session, test_user: User, test_platform: Platform, test_connection: Connection
):
    """
    Verify running sync multiple times is strictly idempotent:
    produces zero duplicate accounts, assets, or transactions.
    """
    mock_connector = MockConnector()

    # --- RUN 1 ---
    res1 = await SyncService.sync_connection(
        connection_id=test_connection.id,
        user_id=test_user.id,
        db=db_session,
        connector_override=mock_connector,
    )
    assert res1.status == "SUCCESS"
    assert res1.records_created == 3
    assert res1.records_updated == 0

    # Verify database state after Run 1
    accs1 = db_session.execute(select(Account).where(Account.user_id == test_user.id)).scalars().all()
    assert len(accs1) == 1

    assets1 = db_session.execute(select(Asset).where(Asset.user_id == test_user.id)).scalars().all()
    assert len(assets1) == 1
    assert assets1[0].name == "Infosys Limited"
    assert assets1[0].current_value == 15000.0

    txs1 = db_session.execute(select(Transaction).where(Transaction.user_id == test_user.id)).scalars().all()
    assert len(txs1) == 1

    # --- RUN 2 (EXACT SAME DATA AGAIN) ---
    res2 = await SyncService.sync_connection(
        connection_id=test_connection.id,
        user_id=test_user.id,
        db=db_session,
        connector_override=mock_connector,
    )
    assert res2.status == "SUCCESS"
    assert res2.records_created == 0  # CRITICAL: NO DUPLICATES CREATED
    assert res2.records_updated >= 2  # Updated existing records

    # Verify counts remain 1 (no duplicates)
    accs2 = db_session.execute(select(Account).where(Account.user_id == test_user.id)).scalars().all()
    assert len(accs2) == 1

    assets2 = db_session.execute(select(Asset).where(Asset.user_id == test_user.id)).scalars().all()
    assert len(assets2) == 1
    assert assets2[0].current_value == 15000.0

    txs2 = db_session.execute(select(Transaction).where(Transaction.user_id == test_user.id)).scalars().all()
    assert len(txs2) == 1


class FailingConnector(BaseConnector):
    connector_key = "failing_mock"
    name = "Failing Connector"
    status = ConnectionMethodStatus.AVAILABLE

    async def sync(self, connection):
        raise RateLimitedError("Provider rate limit reached. Retry after 60s.", retry_after=60)


@pytest.mark.anyio
async def test_sync_failure_handling(
    db_session: Session, test_user: User, test_connection: Connection
):
    """Verify provider failure is safely handled, logged, and does not leak raw exceptions."""
    failing_conn = FailingConnector()

    res = await SyncService.sync_connection(
        connection_id=test_connection.id,
        user_id=test_user.id,
        db=db_session,
        connector_override=failing_conn,
    )

    assert res.status == "SYNC_FAILED"
    assert res.error_code == "RATE_LIMITED"
    assert "rate limit" in res.safe_error_message.lower()

    # Verify connection status is updated
    db_session.refresh(test_connection)
    assert test_connection.status == "SYNC_FAILED"
    assert test_connection.last_sync_status == "SYNC_FAILED"
    assert "rate limit" in test_connection.last_sync_error.lower()
