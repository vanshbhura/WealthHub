import pytest
import uuid
from app.connectors.registry import registry
from app.connectors.enums import ConnectorType, ConnectorCapability, ConnectionMethodStatus
from app.connectors.exceptions import (
    ConnectorError,
    AuthFailedError,
    RateLimitedError,
    TokenExpiredError,
    ConnectorNotImplementedError,
)
from app.connectors.credentials import CredentialStore, FernetCredentialStore
from app.connectors.testing.mock import MockConnector
from app.connectors.dtos import (
    NormalizedAccount,
    NormalizedAsset,
    NormalizedHolding,
    NormalizedTransaction,
    NormalizedBalance,
    NormalizedPortfolio,
)


def test_registry_lookup_and_availability():
    """Verify registry resolves known connectors with accurate availability statuses."""
    # Manual connector must be AVAILABLE
    manual = registry.get("manual_asset")
    assert manual is not None
    assert manual.connector_type == ConnectorType.MANUAL
    assert manual.status == ConnectionMethodStatus.AVAILABLE
    assert manual.is_available() is True
    assert ConnectorCapability.HOLDINGS in manual.get_capabilities()

    # Live Groww connector is now AVAILABLE (Prompt 7)
    groww = registry.get("groww_direct")
    assert groww is not None
    assert groww.connector_type == ConnectorType.DIRECT_API
    assert groww.status == ConnectionMethodStatus.AVAILABLE
    assert groww.is_available() is True
    assert ConnectorCapability.HOLDINGS in groww.get_capabilities()
    assert ConnectorCapability.POSITIONS in groww.get_capabilities()

    # Other external broker connectors remain COMING_SOON (zero-fabrication)
    zerodha = registry.get("zerodha_kite")
    assert zerodha is not None
    assert zerodha.connector_type == ConnectorType.DIRECT_API
    assert zerodha.status == ConnectionMethodStatus.COMING_SOON
    assert zerodha.is_available() is False

    # AA connector must be COMING_SOON
    aa = registry.get("account_aggregator")
    assert aa is not None
    assert aa.connector_type == ConnectorType.ACCOUNT_AGGREGATOR
    assert aa.status == ConnectionMethodStatus.COMING_SOON
    assert aa.is_available() is False

    # Statement import is now AVAILABLE in Prompt 6
    stmt_import = registry.get("statement_import")
    assert stmt_import is not None
    assert stmt_import.status == ConnectionMethodStatus.AVAILABLE
    assert stmt_import.is_available() is True

    # Nonexistent connector
    assert registry.get("fake_nonexistent_broker") is None
    with pytest.raises(ConnectorNotImplementedError):
        registry.get_or_raise("fake_nonexistent_broker")


def test_registry_get_for_platform():
    """Verify registry returns all supported methods for a given platform slug."""
    groww_conns = registry.get_for_platform("groww")
    keys = [c.connector_key for c in groww_conns]
    assert "groww_direct" in keys
    assert "manual_asset" in keys
    assert "statement_import" in keys

    sbi_conns = registry.get_for_platform("sbi")
    sbi_keys = [c.connector_key for c in sbi_conns]
    assert "account_aggregator" in sbi_keys
    assert "manual_asset" in sbi_keys
    assert "statement_import" in sbi_keys


@pytest.mark.anyio
async def test_coming_soon_connector_blocks_live_connection():
    """Verify calling connect/sync on an unintegrated connector raises ConnectorNotImplementedError."""
    zerodha = registry.get("zerodha_kite")
    assert zerodha is not None
    assert zerodha.is_available() is False

    dummy_user_id = uuid.uuid4()
    with pytest.raises(ConnectorNotImplementedError) as exc_info:
        await zerodha.connect(dummy_user_id)
    assert "coming soon" in str(exc_info.value).lower()

    with pytest.raises(ConnectorNotImplementedError):
        await zerodha.sync(None)


def test_credential_store_encryption_and_revocation():
    """Verify CredentialStore securely encrypts tokens, allows retrieval, and revokes upon disconnect."""
    store = FernetCredentialStore(master_key="wealthhub-test-master-encryption-key-32b")
    user_id = uuid.uuid4()
    connection_id = uuid.uuid4()

    token_secret = "gho_test_provider_access_token_secret_12345"
    store.store_secret(user_id, connection_id, "access_token", token_secret)

    # Retrieval
    retrieved = store.get_secret(user_id, connection_id, "access_token")
    assert retrieved == token_secret

    # Wrong user or connection cannot retrieve
    assert store.get_secret(uuid.uuid4(), connection_id, "access_token") is None
    assert store.get_secret(user_id, uuid.uuid4(), "access_token") is None

    # Revocation / delete
    deleted = store.delete_secret(user_id, connection_id, "access_token")
    assert deleted is True
    assert store.get_secret(user_id, connection_id, "access_token") is None

    # Test delete_all_secrets
    store.store_secret(user_id, connection_id, "token1", "val1")
    store.store_secret(user_id, connection_id, "token2", "val2")
    count = store.delete_all_secrets(user_id, connection_id)
    assert count == 2
    assert store.get_secret(user_id, connection_id, "token1") is None
    assert store.get_secret(user_id, connection_id, "token2") is None


def test_error_normalization():
    """Verify provider errors have safe customer-facing messages."""
    auth_err = AuthFailedError()
    assert auth_err.code == "AUTH_FAILED"
    assert "password" not in auth_err.safe_message.lower()
    assert "secret" not in auth_err.safe_message.lower()

    rate_err = RateLimitedError(retry_after=60)
    assert rate_err.code == "RATE_LIMITED"
    assert rate_err.retry_after == 60


@pytest.mark.anyio
async def test_mock_connector_pipeline():
    """Verify MockConnector yields normalized DTOs for testing."""
    mock_conn = MockConnector()
    portfolio = await mock_conn.sync(None)
    assert len(portfolio.accounts) == 1
    assert len(portfolio.holdings) == 1
    assert len(portfolio.transactions) == 1
    assert portfolio.holdings[0].asset.name == "Infosys Limited"
    assert portfolio.holdings[0].asset.current_value == 15000.0
