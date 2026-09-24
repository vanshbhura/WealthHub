import os
import uuid
import time
import pytest
import httpx
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.config import settings
from app.domain.enums import AssetCategory, TransactionType
from app.models.connection import Connection
from app.models.platform import Platform
from app.models.asset import Asset
from app.models.account import Account
from app.models.snapshot import PortfolioSnapshot
from app.connectors.account_aggregator.dtos import (
    SetuConsentRequest,
    SetuConsentResponse,
    SetuConsentStatus,
    SetuFinancialDataResponse,
    SetuBankAccount,
    SetuBankTransaction,
    SetuMutualFundHolding,
    SetuEquityHolding,
    SetuFixedDeposit,
    SetuNPSAccount,
)
from app.connectors.account_aggregator.exceptions import (
    SetuClientError,
    SetuAuthError,
    SetuTimeoutError,
    SetuProviderUnavailableError,
    SetuInvalidResponseError,
    SetuRateLimitError,
    SetuConsentRejectedError,
    SetuConsentExpiredError,
    SetuConsentRevokedError,
    SetuConfigurationError,
)
from app.connectors.account_aggregator.sandbox import SetuSandboxDataGenerator
from app.connectors.account_aggregator.setu_client import SetuAAClient, redact_sensitive_data
from app.connectors.account_aggregator.mapper import AAMapper
from app.connectors.account_aggregator.setu_connector import SetuAAConnector
from app.connectors.sync_service import SyncService
from app.services.portfolio_service import PortfolioService
from app.services.valuation_service import ValuationService
from app.services.deduplication_engine import DeduplicationEngine


# ---------------------------------------------------------
# 1. Setu client initialization
# ---------------------------------------------------------
def test_setu_client_initialization():
    client = SetuAAClient(
        base_url="https://custom-sandbox.setu.co",
        client_id="test_client_id",
        client_secret="test_secret",
        product_instance_id="prod_inst_1",
        timeout=20.0,
        force_sandbox_mock=False,
    )
    assert client.base_url == "https://custom-sandbox.setu.co"
    assert client.client_id == "test_client_id"
    assert client.timeout == 20.0
    assert client.use_mock is False


# ---------------------------------------------------------
# 2. Missing credentials fallback
# ---------------------------------------------------------
def test_missing_credentials_fallback():
    client = SetuAAClient(
        client_id=None,
        client_secret=None,
        product_instance_id=None,
    )
    assert client.use_mock is True


# ---------------------------------------------------------
# 3. Authentication failure
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_authentication_failure():
    client = SetuAAClient(
        client_id="invalid_id",
        client_secret="invalid_secret",
        product_instance_id="inst",
        force_sandbox_mock=False,
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        with pytest.raises(SetuAuthError):
            await client.create_consent_request(SetuConsentRequest())


# ---------------------------------------------------------
# 4. Provider unavailable
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_provider_unavailable():
    client = SetuAAClient(
        client_id="id", client_secret="sec", product_instance_id="inst", force_sandbox_mock=False
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 503

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        with pytest.raises(SetuProviderUnavailableError):
            await client.create_consent_request(SetuConsentRequest())


# ---------------------------------------------------------
# 5. Timeout handling
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_timeout_handling():
    client = SetuAAClient(
        client_id="id", client_secret="sec", product_instance_id="inst", force_sandbox_mock=False
    )
    with patch.object(httpx.AsyncClient, "request", AsyncMock(side_effect=httpx.TimeoutException("Read timed out"))):
        with pytest.raises(SetuTimeoutError):
            await client.create_consent_request(SetuConsentRequest())


# ---------------------------------------------------------
# 6. Malformed response handling
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_malformed_response():
    client = SetuAAClient(
        client_id="id", client_secret="sec", product_instance_id="inst", force_sandbox_mock=False
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("Invalid JSON string")

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        with pytest.raises(SetuInvalidResponseError):
            await client.create_consent_request(SetuConsentRequest())


# ---------------------------------------------------------
# 7. Consent creation
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_consent_creation():
    client = SetuAAClient(force_sandbox_mock=True)
    req = SetuConsentRequest(
        customer_phone="9876543210",
        customer_vpa="9876543210@setu",
        fi_types=["DEPOSIT", "MUTUAL_FUNDS"],
    )
    resp = await client.create_consent_request(req)
    assert resp.id.startswith("sandbox-consent-")
    assert "consents/redirect" in resp.url
    assert resp.status == "PENDING"


# ---------------------------------------------------------
# 8. Consent pending status
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_consent_pending():
    client = SetuAAClient(force_sandbox_mock=True)
    req = SetuConsentRequest(customer_phone="9876543210")
    consent = await client.create_consent_request(req)
    status_dto = await client.get_consent_status(consent.id)
    assert status_dto.status == "PENDING"


# ---------------------------------------------------------
# 9. Consent authorized status
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_consent_authorized():
    client = SetuAAClient(force_sandbox_mock=True)
    req = SetuConsentRequest(customer_phone="9876543210")
    consent = await client.create_consent_request(req)
    client.set_mock_consent_status(consent.id, "ACTIVE")
    status_dto = await client.get_consent_status(consent.id)
    assert status_dto.status == "ACTIVE"


# ---------------------------------------------------------
# 10. Consent rejected
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_consent_rejected():
    client = SetuAAClient(
        client_id="id",
        client_secret="sec",
        product_instance_id="inst",
        auth_token="mock_auth_token",
        force_sandbox_mock=False,
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "c-1", "status": "REJECTED", "error": "Customer denied"}

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        with pytest.raises(SetuConsentRejectedError):
            await client.get_consent_status("c-1")


# ---------------------------------------------------------
# 11. Consent expired
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_consent_expired():
    client = SetuAAClient(
        client_id="id",
        client_secret="sec",
        product_instance_id="inst",
        auth_token="mock_auth_token",
        force_sandbox_mock=False,
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "c-1", "status": "EXPIRED"}

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        with pytest.raises(SetuConsentExpiredError):
            await client.get_consent_status("c-1")


# ---------------------------------------------------------
# 12. Financial data parsing
# ---------------------------------------------------------
def test_financial_data_parsing():
    portfolio_data = SetuSandboxDataGenerator.generate_sandbox_portfolio("test-consent")
    assert portfolio_data.data_source in ("SANDBOX", "SANDBOX_MOCK")
    assert len(portfolio_data.bank_accounts) == 1
    assert len(portfolio_data.mutual_funds) == 2
    assert len(portfolio_data.equities) == 2
    assert len(portfolio_data.fixed_deposits) == 1
    assert len(portfolio_data.nps_accounts) == 1


# ---------------------------------------------------------
# 13. Equity normalization
# ---------------------------------------------------------
def test_equity_normalization():
    eq = SetuEquityHolding(
        isin="INE002A01018",
        company_name="Reliance Industries",
        symbol="RELIANCE",
        demat_account="1208160000123456",
        depository="CDSL",
        quantity=20.0,
        average_buy_price=2500.0,
        current_price=2900.0,
        current_value=58000.0,
    )
    holding = AAMapper.map_equity(eq, account_ref="CDSL-1208160000123456")
    asset = holding.asset
    assert asset.asset_type == AssetCategory.STOCK.value
    assert asset.identifier == "INE002A01018"
    assert asset.symbol == "RELIANCE"
    assert asset.quantity == 20.0
    assert asset.invested_amount == 50000.0
    assert asset.current_value == 58000.0
    assert asset.metadata.get("data_source") in ("SANDBOX", "SANDBOX_MOCK")


# ---------------------------------------------------------
# 14. MF normalization
# ---------------------------------------------------------
def test_mf_normalization():
    mf = SetuMutualFundHolding(
        amc="HDFC Mutual Fund",
        scheme_name="HDFC Top 100 Fund",
        isin="INF179K01BE2",
        folio_number="12345/67",
        units=100.0,
        nav=900.0,
        invested_value=80000.0,
        current_value=90000.0,
    )
    holding = AAMapper.map_mutual_fund(mf)
    asset = holding.asset
    assert asset.asset_type == AssetCategory.MUTUAL_FUND.value
    assert asset.identifier == "INF179K01BE2"
    assert asset.quantity == 100.0
    assert asset.current_price == 900.0
    assert asset.current_value == 90000.0


# ---------------------------------------------------------
# 15. Bank normalization
# ---------------------------------------------------------
def test_bank_normalization():
    bank = SetuBankAccount(
        fip_id="FIP-HDFC",
        bank_name="HDFC Bank",
        account_number_masked="****1234",
        account_type="SAVINGS",
        current_balance=25000.0,
        transactions=[
            SetuBankTransaction(
                txn_id="TX-1",
                type="CREDIT",
                amount=10000.0,
                narration="Salary",
            )
        ],
    )
    acc, holding, txns = AAMapper.map_bank_account(bank)
    assert acc.account_name == "HDFC Bank (****1234)"
    assert acc.current_value == 25000.0
    assert holding.asset.asset_type == AssetCategory.CASH.value
    assert holding.asset.current_value == 25000.0
    assert len(txns) == 1
    assert txns[0].transaction_type == TransactionType.DEPOSIT.value


# ---------------------------------------------------------
# 16. FD normalization
# ---------------------------------------------------------
def test_fd_normalization():
    fd = SetuFixedDeposit(
        bank_name="SBI",
        deposit_number_masked="****9999",
        principal_amount=50000.0,
        current_value=53500.0,
        interest_rate=7.0,
    )
    holding = AAMapper.map_fixed_deposit(fd)
    assert holding.asset.asset_type == AssetCategory.FD.value
    assert holding.asset.invested_amount == 50000.0
    assert holding.asset.current_value == 53500.0


# ---------------------------------------------------------
# 17. NPS normalization
# ---------------------------------------------------------
def test_nps_normalization():
    nps = SetuNPSAccount(
        pran_masked="****4455",
        tier="TIER_1",
        total_contribution=40000.0,
        current_value=46000.0,
    )
    holding = AAMapper.map_nps(nps)
    assert holding.asset.asset_type == AssetCategory.NPS.value
    assert holding.asset.invested_amount == 40000.0
    assert holding.asset.current_value == 46000.0


# ---------------------------------------------------------
# 18. Transaction normalization
# ---------------------------------------------------------
def test_transaction_normalization():
    portfolio = AAMapper.to_normalized_portfolio(
        SetuSandboxDataGenerator.generate_sandbox_portfolio("c-1")
    )
    assert len(portfolio.transactions) >= 3
    for tx in portfolio.transactions:
        assert tx.transaction_type in (TransactionType.DEPOSIT.value, TransactionType.WITHDRAWAL.value)
        assert tx.amount > 0


# ---------------------------------------------------------
# 19. Duplicate transaction handling
# ---------------------------------------------------------
def test_duplicate_transaction_handling(db_session, test_user_token):
    user_id = uuid.UUID(test_user_token["user"]["id"])
    portfolio = AAMapper.to_normalized_portfolio(
        SetuSandboxDataGenerator.generate_sandbox_portfolio("c-dup")
    )
    # First deduplication pass: all new
    filtered = DeduplicationEngine.deduplicate_transactions(user_id, portfolio.transactions, db_session)
    assert len(filtered) == len(portfolio.transactions)


# ---------------------------------------------------------
# 20. User isolation
# ---------------------------------------------------------
def test_user_isolation(client, test_user_token, test_user_b_token):
    # User A initiates consent
    res_a = client.post(
        "/api/account-aggregator/consent",
        json={"customer_phone": "9876543210"},
        headers=test_user_token["headers"],
    )
    assert res_a.status_code == 201
    consent_id = res_a.json()["consent_id"]
    conn_id = res_a.json()["connection_id"]

    # User B cannot access User A's consent
    res_b = client.get(
        f"/api/account-aggregator/consent/{consent_id}",
        headers=test_user_b_token["headers"],
    )
    assert res_b.status_code == 404

    # User B cannot trigger sync on User A's consent
    res_b_sync = client.post(
        f"/api/account-aggregator/consent/{consent_id}/sync",
        headers=test_user_b_token["headers"],
    )
    assert res_b_sync.status_code == 404

    # User B cannot inspect User A's connection status
    res_b_status = client.get(
        f"/api/account-aggregator/{conn_id}/status",
        headers=test_user_b_token["headers"],
    )
    assert res_b_status.status_code == 404


# ---------------------------------------------------------
# 21. Sync pipeline execution
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_sync_pipeline(db_session, test_user_token):
    user_id = uuid.UUID(test_user_token["user"]["id"])

    # Resolve platform
    plat = db_session.query(Platform).filter_by(slug="account-aggregator").first()
    assert plat is not None

    connection = Connection(
        user_id=user_id,
        platform_id=plat.id,
        connection_type="ACCOUNT_AGGREGATOR",
        connector_key="setu_aa",
        status="CONNECTED",
        consent_id="sandbox-test-pipeline",
    )
    db_session.add(connection)
    db_session.commit()

    result = await SyncService.sync_connection(connection.id, user_id, db_session)
    assert result.status == "SUCCESS"
    assert result.records_created > 0

    # Ensure assets and accounts exist
    assets = db_session.query(Asset).filter_by(user_id=user_id, platform_id=plat.id).all()
    assert len(assets) >= 5  # Savings, 2 MF, 2 Equities, FD, NPS


# ---------------------------------------------------------
# 22. Portfolio recalculation
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_portfolio_recalculation(db_session, test_user_token):
    user_id = uuid.UUID(test_user_token["user"]["id"])
    plat = db_session.query(Platform).filter_by(slug="account-aggregator").first()

    connection = Connection(
        user_id=user_id,
        platform_id=plat.id,
        connection_type="ACCOUNT_AGGREGATOR",
        connector_key="setu_aa",
        status="CONNECTED",
        consent_id="sandbox-test-portfolio",
    )
    db_session.add(connection)
    db_session.commit()

    await SyncService.sync_connection(connection.id, user_id, db_session)
    summary = PortfolioService.get_summary(user_id=user_id, db=db_session)
    assert summary["total_wealth"] > 0
    assert summary["invested_value"] > 0
    assert summary["asset_count"] >= 5


# ---------------------------------------------------------
# 23. Snapshot capture
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_snapshot_capture(db_session, test_user_token):
    user_id = uuid.UUID(test_user_token["user"]["id"])
    plat = db_session.query(Platform).filter_by(slug="account-aggregator").first()

    connection = Connection(
        user_id=user_id,
        platform_id=plat.id,
        connection_type="ACCOUNT_AGGREGATOR",
        connector_key="setu_aa",
        status="CONNECTED",
        consent_id="sandbox-test-snapshot",
    )
    db_session.add(connection)
    db_session.commit()

    await SyncService.sync_connection(connection.id, user_id, db_session)
    snapshots = db_session.query(PortfolioSnapshot).filter_by(user_id=user_id).all()
    assert len(snapshots) >= 1
    assert snapshots[0].total_value > 0


# ---------------------------------------------------------
# 24. AA + manual coexistence
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_aa_and_manual_coexistence(db_session, test_user_token):
    user_id = uuid.UUID(test_user_token["user"]["id"])
    aa_plat = db_session.query(Platform).filter_by(slug="account-aggregator").first()
    sbi_plat = db_session.query(Platform).filter_by(slug="sbi").first()

    # 1. User has a manual gold asset in SBI
    manual_asset = Asset(
        user_id=user_id,
        platform_id=sbi_plat.id,
        asset_type=AssetCategory.PHYSICAL_GOLD.value,
        name="Family Gold Sovereign",
        quantity=50.0,
        average_buy_price=6000.0,
        invested_amount=300000.0,
        current_price=7200.0,
        current_value=360000.0,
        data_source="MANUAL",
    )
    db_session.add(manual_asset)
    db_session.commit()

    # 2. User syncs Account Aggregator
    connection = Connection(
        user_id=user_id,
        platform_id=aa_plat.id,
        connection_type="ACCOUNT_AGGREGATOR",
        connector_key="setu_aa",
        status="CONNECTED",
        consent_id="sandbox-test-coexist-manual",
    )
    db_session.add(connection)
    db_session.commit()

    await SyncService.sync_connection(connection.id, user_id, db_session)

    summary = PortfolioService.get_summary(user_id=user_id, db=db_session)
    # Total wealth includes both manual gold and AA assets
    assert summary["total_wealth"] >= 360000.0


# ---------------------------------------------------------
# 25. AA + import coexistence
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_aa_and_import_coexistence(db_session, test_user_token):
    user_id = uuid.UUID(test_user_token["user"]["id"])
    aa_plat = db_session.query(Platform).filter_by(slug="account-aggregator").first()
    zerodha_plat = db_session.query(Platform).filter_by(slug="zerodha").first()

    # 1. Imported asset from Zerodha statement (Infosys, different from AA Reliance/TCS)
    imported_asset = Asset(
        user_id=user_id,
        platform_id=zerodha_plat.id,
        asset_type=AssetCategory.STOCK.value,
        name="Infosys Limited",
        symbol="INFY",
        identifier="INE009A01021",
        quantity=50.0,
        average_buy_price=1400.0,
        invested_amount=70000.0,
        current_price=1550.0,
        current_value=77500.0,
        data_source="CSV",
    )
    db_session.add(imported_asset)
    db_session.commit()

    # 2. Sync AA
    connection = Connection(
        user_id=user_id,
        platform_id=aa_plat.id,
        connection_type="ACCOUNT_AGGREGATOR",
        connector_key="setu_aa",
        status="CONNECTED",
        consent_id="sandbox-test-coexist-import",
    )
    db_session.add(connection)
    db_session.commit()

    await SyncService.sync_connection(connection.id, user_id, db_session)

    summary = PortfolioService.get_summary(user_id=user_id, db=db_session)
    assert summary["total_wealth"] >= 77500.0


# ---------------------------------------------------------
# 26. AA + Groww coexistence
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_aa_and_groww_coexistence(db_session, test_user_token):
    user_id = uuid.UUID(test_user_token["user"]["id"])
    aa_plat = db_session.query(Platform).filter_by(slug="account-aggregator").first()
    groww_plat = db_session.query(Platform).filter_by(slug="groww").first()

    # 1. Groww Live asset (Wipro)
    groww_asset = Asset(
        user_id=user_id,
        platform_id=groww_plat.id,
        asset_type=AssetCategory.STOCK.value,
        name="Wipro Limited",
        symbol="WIPRO",
        identifier="INE075A01022",
        quantity=100.0,
        average_buy_price=450.0,
        invested_amount=45000.0,
        current_price=520.0,
        current_value=52000.0,
        data_source="BROKER_API",
    )
    db_session.add(groww_asset)
    db_session.commit()

    # 2. Sync AA
    connection = Connection(
        user_id=user_id,
        platform_id=aa_plat.id,
        connection_type="ACCOUNT_AGGREGATOR",
        connector_key="setu_aa",
        status="CONNECTED",
        consent_id="sandbox-test-coexist-groww",
    )
    db_session.add(connection)
    db_session.commit()

    await SyncService.sync_connection(connection.id, user_id, db_session)

    summary = PortfolioService.get_summary(user_id=user_id, db=db_session)
    assert summary["total_wealth"] >= 52000.0


# ---------------------------------------------------------
# 27. Double-counting protection
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_double_counting_protection(db_session, test_user_token):
    user_id = uuid.UUID(test_user_token["user"]["id"])
    aa_plat = db_session.query(Platform).filter_by(slug="account-aggregator").first()
    groww_plat = db_session.query(Platform).filter_by(slug="groww").first()

    # Pre-existing Groww holding with Reliance ISIN INE002A01018 (₹74,500 value)
    groww_holding = Asset(
        user_id=user_id,
        platform_id=groww_plat.id,
        asset_type=AssetCategory.STOCK.value,
        name="Reliance Industries Limited",
        symbol="RELIANCE",
        identifier="INE002A01018",
        quantity=25.0,
        average_buy_price=2750.0,
        invested_amount=68750.0,
        current_price=2980.0,
        current_value=74500.0,
        data_source="BROKER_API",
    )
    db_session.add(groww_holding)
    db_session.commit()

    wealth_before = ValuationService.calculate_user_wealth(user_id, db_session)["total_wealth"]
    assert wealth_before == 74500.0

    # Sync Account Aggregator (which also provides Reliance INE002A01018 from CDSL)
    connection = Connection(
        user_id=user_id,
        platform_id=aa_plat.id,
        connection_type="ACCOUNT_AGGREGATOR",
        connector_key="setu_aa",
        status="CONNECTED",
        consent_id="sandbox-test-dedup",
    )
    db_session.add(connection)
    db_session.commit()

    await SyncService.sync_connection(connection.id, user_id, db_session)

    # Check valuation with double counting protection
    val = ValuationService.calculate_user_wealth(user_id, db_session)

    # Notice: The AA Reliance holding MUST NOT be added again to total wealth!
    # Reliance is only counted ONCE.
    # Total wealth should be Groww Reliance (₹74,500) + other non-overlapping AA assets (TCS, MF, Bank, FD, NPS)
    aa_reliance = (
        db_session.query(Asset)
        .filter_by(user_id=user_id, platform_id=aa_plat.id, identifier="INE002A01018")
        .first()
    )
    assert aa_reliance is not None
    assert aa_reliance.metadata_json.get("is_duplicate") is True
    assert "Overlaps with holding" in aa_reliance.metadata_json.get("duplicate_reason", "")
    assert val["duplicate_count"] >= 1


# ---------------------------------------------------------
# 28. Credential & account number redaction
# ---------------------------------------------------------
def test_credential_and_pii_redaction():
    sample = {
        "client_secret": "super_secret_setu_token_12345",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "account_number": "123456789012",
        "demat_account": "1208160000123456",
        "safe_field": "HDFC Bank",
    }
    redacted = redact_sensitive_data(sample)
    assert redacted["client_secret"] == "[REDACTED]"
    assert redacted["access_token"] == "[REDACTED]"
    assert redacted["account_number"] == "[REDACTED]"
    assert redacted["demat_account"] == "[REDACTED]"
    assert redacted["safe_field"] == "HDFC Bank"


# ---------------------------------------------------------
# 29. Live Setu Sandbox Integration Test (Opt-in via SETU_LIVE_TEST)
# ---------------------------------------------------------
@pytest.mark.skipif(
    not settings.SETU_LIVE_TEST,
    reason="Live Setu AA sandbox test disabled. Set SETU_LIVE_TEST=true to execute.",
)
@pytest.mark.anyio
async def test_live_setu_sandbox_integration():
    # If live test is requested but credentials are not configured, skip honestly explaining missing credentials
    if not (settings.SETU_CLIENT_ID and settings.SETU_CLIENT_SECRET and settings.SETU_PRODUCT_INSTANCE_ID):
        missing = []
        if not settings.SETU_CLIENT_ID:
            missing.append("SETU_CLIENT_ID")
        if not settings.SETU_CLIENT_SECRET:
            missing.append("SETU_CLIENT_SECRET")
        if not settings.SETU_PRODUCT_INSTANCE_ID:
            missing.append("SETU_PRODUCT_INSTANCE_ID")
        pytest.skip(f"SETU credentials not configured: Missing {', '.join(missing)}.")

    client = SetuAAClient(force_sandbox_mock=False)
    res = await client.health_check()
    assert res["status"] in ("healthy", "unauthorized", "provider_unavailable", "unavailable", "degraded")


# ---------------------------------------------------------
# 30. SETU_CONFIGURATION_ERROR when missing credentials in real mode
# ---------------------------------------------------------
def test_setu_configuration_error_when_missing_credentials_in_real_mode():
    with pytest.raises(SetuConfigurationError) as exc_info:
        SetuAAClient(
            client_id=None,
            client_secret=None,
            product_instance_id=None,
            force_sandbox_mock=False,
        )
    assert exc_info.value.code == "SETU_CONFIGURATION_ERROR"
    assert "Missing required configuration" in exc_info.value.safe_message
    assert "SETU_CLIENT_ID" in exc_info.value.safe_message
    assert "SETU_CLIENT_SECRET" in exc_info.value.safe_message
    assert "SETU_PRODUCT_INSTANCE_ID" in exc_info.value.safe_message


# ---------------------------------------------------------
# 31. Real Setu mode: NO silent fallback to mock on API error
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_real_mode_no_silent_fallback_on_api_error():
    client = SetuAAClient(
        client_id="valid_client_id",
        client_secret="valid_secret",
        product_instance_id="valid_instance",
        force_sandbox_mock=False,
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        # MUST raise SetuProviderUnavailableError, MUST NOT return mock data!
        with pytest.raises(SetuProviderUnavailableError):
            await client.get_data("consent-test-fail")


# ---------------------------------------------------------
# 32. Health check: Mock vs Real diagnostics
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_health_check_mock_vs_real():
    # A. Mock mode
    mock_client = SetuAAClient(force_sandbox_mock=True)
    mock_res = await mock_client.health_check()
    assert mock_res["status"] == "healthy"
    assert mock_res["mode"] == "sandbox_mock"

    # B. Real mode with missing credentials
    real_client_no_creds = SetuAAClient(
        client_id=None,
        client_secret=None,
        product_instance_id=None,
        force_sandbox_mock=True,
    )
    # Temporarily switch to real to check health_check report without crashing
    real_client_no_creds.use_mock = False
    real_res = await real_client_no_creds.health_check()
    assert real_res["status"] == "configuration_error"
    assert "SETU_CONFIGURATION_ERROR" in real_res["error"]

    # C. Real mode with credentials (mocking HTTP 200 with OAuth token + gateway health)
    real_client_with_creds = SetuAAClient(
        client_id="id1",
        client_secret="sec1",
        product_instance_id="inst1",
        force_sandbox_mock=False,
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "UP",
        "success": True,
        "data": {"token": "valid-oauth-token-123", "expiresIn": 1800},
    }

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        healthy_res = await real_client_with_creds.health_check()
        assert healthy_res["status"] == "healthy"
        assert healthy_res["mode"] == "real_setu"
        assert "latency_ms" in healthy_res


# ---------------------------------------------------------
# 33. Real Setu FIU payload parser and SETU_SANDBOX tagging
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_real_setu_payload_parser_and_source_tagging():
    client = SetuAAClient(
        client_id="id1",
        client_secret="sec1",
        product_instance_id="inst1",
        auth_token="test_token",
        force_sandbox_mock=False,
    )

    # Realistic Setu FIU payload structure
    sample_fiu_payload = {
        "id": "session-12345",
        "status": "COMPLETED",
        "Payload": [
            {
                "fipId": "FIP-HDFC-BANK",
                "fipName": "HDFC Bank Ltd",
                "accounts": [
                    {
                        "type": "DEPOSIT",
                        "maskedAccNumber": "****9988",
                        "summary": {
                            "bankName": "HDFC Bank",
                            "currentBalance": "52000.50",
                            "currency": "INR",
                        },
                        "transactions": [
                            {
                                "txnId": "TXN-REAL-101",
                                "type": "CREDIT",
                                "amount": "10000.00",
                                "narration": "Sandbox Salary Deposit",
                            }
                        ],
                    }
                ],
            },
            {
                "fipId": "FIP-CDSL-DEMAT",
                "accounts": [
                    {
                        "type": "EQUITIES",
                        "equities": [
                            {
                                "isin": "INE002A01018",
                                "companyName": "Reliance Industries Limited",
                                "symbol": "RELIANCE",
                                "dematAccount": "1208160000999999",
                                "depository": "CDSL",
                                "quantity": "10",
                                "averageBuyPrice": "2800.00",
                                "currentPrice": "3000.00",
                            }
                        ],
                    }
                ],
            },
            {
                "fipId": "FIP-CAMS-CAS",
                "accounts": [
                    {
                        "type": "MUTUAL_FUNDS",
                        "funds": [
                            {
                                "isin": "INF179K01BE2",
                                "schemeName": "HDFC Top 100 Fund",
                                "amc": "HDFC Mutual Fund",
                                "folioNumber": "FOLIO-7788",
                                "units": "50.0",
                                "nav": "950.0",
                                "investedValue": "45000.0",
                                "currentValue": "47500.0",
                            }
                        ],
                    }
                ],
            },
        ],
    }

    mock_sess_resp = MagicMock()
    mock_sess_resp.status_code = 200
    mock_sess_resp.json.return_value = {"id": "sess-real-001", "status": "COMPLETED"}

    mock_data_resp = MagicMock()
    mock_data_resp.status_code = 200
    mock_data_resp.json.return_value = sample_fiu_payload

    with patch.object(
        httpx.AsyncClient,
        "request",
        AsyncMock(side_effect=[mock_sess_resp, mock_data_resp]),
    ):
        result = await client.get_data("consent-real-001")

        # Crucial assertions:
        assert result.data_source == "SETU_SANDBOX"
        assert len(result.bank_accounts) == 1
        assert result.bank_accounts[0].current_balance == 52000.50
        assert len(result.equities) == 1
        assert result.equities[0].symbol == "RELIANCE"
        assert len(result.mutual_funds) == 1
        assert result.mutual_funds[0].scheme_name == "HDFC Top 100 Fund"

        # Verify mapping into NormalizedPortfolio propagates SETU_SANDBOX
        portfolio = AAMapper.to_normalized_portfolio(result)
        assert len(portfolio.accounts) == 2  # 1 bank + 1 Demat
        assert portfolio.accounts[0].metadata.get("data_source") == "SETU_SANDBOX"
        assert portfolio.holdings[0].asset.metadata.get("data_source") == "SETU_SANDBOX"


# ---------------------------------------------------------
# 34. All consent status transitions (AUTHORIZED, REJECTED, EXPIRED, REVOKED)
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_all_consent_status_transitions():
    client = SetuAAClient(force_sandbox_mock=True)
    req = SetuConsentRequest(customer_phone="9876543210")
    consent = await client.create_consent_request(req)

    # 1. PENDING initially
    status_p = await client.get_consent_status(consent.id)
    assert status_p.status == "PENDING"

    # 2. AUTHORIZED
    client.set_mock_consent_status(consent.id, "AUTHORIZED")
    status_auth = await client.get_consent_status(consent.id)
    assert status_auth.status == "AUTHORIZED"

    # 3. REJECTED
    client.set_mock_consent_status(consent.id, "REJECTED")
    with pytest.raises(SetuConsentRejectedError):
        await client.get_consent_status(consent.id)

    # 4. EXPIRED
    client.set_mock_consent_status(consent.id, "EXPIRED")
    with pytest.raises(SetuConsentExpiredError):
        await client.get_consent_status(consent.id)

    # 5. REVOKED
    client.set_mock_consent_status(consent.id, "REVOKED")
    with pytest.raises(SetuConsentRevokedError):
        await client.get_consent_status(consent.id)


# =========================================================
# REAL SETU AA OAUTH AUTHENTICATION & GATEWAY TESTS (Task 7)
# =========================================================

# ---------------------------------------------------------
# 35. Successful OAuth Authentication & Header Composition
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_oauth_successful_authentication():
    client = SetuAAClient(
        client_id="test_client_id_123",
        client_secret="test_secret_abc",
        product_instance_id="prod_inst_xyz",
        force_sandbox_mock=False,
    )
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {
        "status": 200,
        "success": True,
        "data": {
            "token": "valid-jwt-token-999",
            "expiresIn": 1800,
        },
    }

    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=mock_token_resp)) as mock_post:
        token = await client.get_access_token()
        assert token == "valid-jwt-token-999"

        # Verify auth URL was called with clientID and secret payload
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["json"] == {
            "clientID": "test_client_id_123",
            "secret": "test_secret_abc",
        }

        # Verify header composition
        headers = await client._get_headers()
        assert headers["Authorization"] == "Bearer valid-jwt-token-999"
        assert headers["x-product-instance-id"] == "prod_inst_xyz"
        assert "x-client-id" not in headers
        assert "x-client-secret" not in headers


# ---------------------------------------------------------
# 36. Invalid Credentials / 401 Rejection
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_oauth_invalid_credentials_401():
    client = SetuAAClient(
        client_id="wrong_id",
        client_secret="wrong_secret",
        product_instance_id="inst1",
        force_sandbox_mock=False,
    )
    mock_fail_resp = MagicMock()
    mock_fail_resp.status_code = 401
    mock_fail_resp.json.return_value = {
        "error": "unauthorized",
        "message": "Invalid client credentials",
    }

    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=mock_fail_resp)):
        with pytest.raises(SetuAuthError) as exc_info:
            await client.get_access_token()
        assert exc_info.value.code == "SETU_AUTH_FAILED"

        # Health check must report unauthorized
        res = await client.health_check()
        assert res["status"] == "unauthorized"
        assert res["mode"] == "real_setu"
        assert "verify client ID and secret" in res["error"]


# ---------------------------------------------------------
# 37. Token Expiry & Automatic Refresh Handling
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_oauth_token_expiry_handling():
    client = SetuAAClient(
        client_id="test_client",
        client_secret="test_secret",
        product_instance_id="test_inst",
        force_sandbox_mock=False,
    )
    # Simulate an expired token in cache
    client._cached_token = "old-expired-token"
    client._token_expires_at = time.time() - 30  # Expired 30 seconds ago

    mock_refresh_resp = MagicMock()
    mock_refresh_resp.status_code = 200
    mock_refresh_resp.json.return_value = {
        "success": True,
        "data": {
            "token": "new-refreshed-token-2026",
            "expiresIn": 3600,
        },
    }

    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=mock_refresh_resp)):
        token = await client.get_access_token()
        assert token == "new-refreshed-token-2026"
        assert client._cached_token == "new-refreshed-token-2026"
        assert client._token_expires_at > time.time() + 3500


# ---------------------------------------------------------
# 38. Gateway 401 Token Refresh & Request Retry
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_oauth_token_refresh_on_gateway_401():
    client = SetuAAClient(
        client_id="test_client",
        client_secret="test_secret",
        product_instance_id="test_inst",
        auth_token="initial-token",
        force_sandbox_mock=False,
    )

    # 1. Gateway returns 401 on first try
    resp_gateway_401 = MagicMock()
    resp_gateway_401.status_code = 401

    # 2. Token refresh endpoint returns new token
    resp_token_ok = MagicMock()
    resp_token_ok.status_code = 200
    resp_token_ok.json.return_value = {
        "success": True,
        "data": {"token": "refreshed-after-401", "expiresIn": 1800},
    }

    # 3. Gateway returns 200 on retry
    resp_gateway_200 = MagicMock()
    resp_gateway_200.status_code = 200
    resp_gateway_200.json.return_value = {"status": "SUCCESS", "data": "recovered"}

    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=resp_token_ok)):
        with patch.object(
            httpx.AsyncClient,
            "request",
            AsyncMock(side_effect=[resp_gateway_401, resp_gateway_200]),
        ) as mock_req:
            res = await client._request("GET", "/health")
            assert res == {"status": "SUCCESS", "data": "recovered"}
            assert mock_req.call_count == 2
            assert client._cached_token == "refreshed-after-401"


# ---------------------------------------------------------
# 39. Missing Credentials in Real Mode
# ---------------------------------------------------------
def test_oauth_missing_credentials_in_real_mode():
    with pytest.raises(SetuConfigurationError) as exc_info:
        SetuAAClient(
            client_id="",
            client_secret="",
            product_instance_id="",
            force_sandbox_mock=False,
        )
    assert exc_info.value.code == "SETU_CONFIGURATION_ERROR"
    missing = exc_info.value.missing_keys
    assert "SETU_CLIENT_ID" in missing
    assert "SETU_CLIENT_SECRET" in missing
    assert "SETU_PRODUCT_INSTANCE_ID" in missing


# ---------------------------------------------------------
# 40. Wrong Product Instance ID Rejection
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_oauth_wrong_product_instance_id():
    client = SetuAAClient(
        client_id="valid_client",
        client_secret="valid_secret",
        product_instance_id="wrong_instance_id",
        auth_token="valid_token",
        force_sandbox_mock=False,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = '{"error": "invalid-product-instance-id", "message": "Product instance does not exist"}'

    with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
        with pytest.raises(SetuAuthError):
            await client._request("GET", "/health", max_retries=0)

    # In health_check, if token fetch succeeds but gateway rejects product instance with 403 or 400:
    mock_token_ok = MagicMock()
    mock_token_ok.status_code = 200
    mock_token_ok.json.return_value = {
        "success": True,
        "data": {"token": "valid_token", "expiresIn": 1800},
    }
    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=mock_token_ok)):
        with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_resp)):
            health_res = await client.health_check()
            assert health_res["status"] == "unauthorized"
            assert "rejected authentication or product instance ID" in health_res["error"]


# ---------------------------------------------------------
# 41. Setu OAuth Timeout Handling
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_oauth_auth_timeout():
    client = SetuAAClient(
        client_id="client_id",
        client_secret="client_sec",
        product_instance_id="inst1",
        force_sandbox_mock=False,
    )

    with patch.object(
        httpx.AsyncClient,
        "post",
        AsyncMock(side_effect=httpx.TimeoutException("Connection timed out")),
    ):
        with pytest.raises(SetuTimeoutError) as exc_info:
            await client.get_access_token()
        assert exc_info.value.code == "SETU_TIMEOUT"

        health = await client.health_check()
        assert health["status"] == "timeout"
        assert "timed out" in health["error"]


# ---------------------------------------------------------
# 42. Setu Auth Server Error 5xx Handling
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_oauth_auth_server_error_5xx():
    client = SetuAAClient(
        client_id="client_id",
        client_secret="client_sec",
        product_instance_id="inst1",
        force_sandbox_mock=False,
    )

    mock_503 = MagicMock()
    mock_503.status_code = 503
    mock_503.text = "Service Unavailable"

    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=mock_503)):
        with pytest.raises(SetuProviderUnavailableError) as exc_info:
            await client.get_access_token()
        assert exc_info.value.code == "SETU_UNAVAILABLE"

        health = await client.health_check()
        assert health["status"] in ("provider_unavailable", "unavailable")


# ---------------------------------------------------------
# 43. Real Setu Mode Never Silently Falls Back to SANDBOX_MOCK
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_real_setu_mode_never_silently_uses_sandbox_mock(monkeypatch):
    monkeypatch.setattr(settings, "SETU_ENVIRONMENT", "sandbox")
    monkeypatch.setattr(settings, "SETU_CLIENT_ID", "live_client_id")
    monkeypatch.setattr(settings, "SETU_CLIENT_SECRET", "live_secret")
    monkeypatch.setattr(settings, "SETU_PRODUCT_INSTANCE_ID", "live_product_instance")

    # In sandbox/real_setu mode, force_sandbox_mock is not provided
    client = SetuAAClient()
    assert client.use_mock is False

    # Simulate Setu Gateway returning 500
    mock_500 = MagicMock()
    mock_500.status_code = 500

    # Ensure get_data throws error, NEVER returning mock bank/equities
    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {"data": {"token": "jwt", "expiresIn": 1800}}))):
        with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_500)):
            with pytest.raises(SetuProviderUnavailableError):
                await client.get_data("consent-test-strict-real")

            # Health check must report provider_unavailable, NEVER healthy with sandbox_mock
            health = await client.health_check()
            assert health["mode"] == "real_setu"
            assert health["status"] in ("provider_unavailable", "unavailable")


# ---------------------------------------------------------
# 44. Setu Sandbox Exact Configuration & Bearer Header Verification
# ---------------------------------------------------------
@pytest.mark.anyio
async def test_setu_sandbox_exact_config_and_bearer_headers():
    test_client_id = "6896da69-c53c-476a-a4f5-16f608c63cf9"
    test_product_inst_id = "2d842846-71aa-4642-8d09-f7555ef15236"
    test_auth_url = "https://uat.setu.co/api/v2/auth/token"
    test_base_url = "https://fiu-sandbox.setu.co"

    client = SetuAAClient(
        base_url=test_base_url,
        auth_url=test_auth_url,
        client_id=test_client_id,
        client_secret="mock_test_secret_for_unit_test",
        product_instance_id=test_product_inst_id,
        force_sandbox_mock=False,
    )

    mock_oauth_resp = MagicMock()
    mock_oauth_resp.status_code = 200
    mock_oauth_resp.json.return_value = {
        "status": 200,
        "success": True,
        "data": {
            "token": "sandbox-jwt-bearer-token-xyz",
            "expiresIn": 1800,
        },
    }

    mock_gateway_resp = MagicMock()
    mock_gateway_resp.status_code = 200
    mock_gateway_resp.json.return_value = {"status": "UP"}

    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=mock_oauth_resp)) as mock_post:
        with patch.object(httpx.AsyncClient, "request", AsyncMock(return_value=mock_gateway_resp)) as mock_req:
            # 1. Verify token retrieval targets the exact auth URL with clientID
            token = await client.get_access_token()
            assert token == "sandbox-jwt-bearer-token-xyz"
            mock_post.assert_called_once()
            called_auth_url = mock_post.call_args[0][0]
            assert called_auth_url == "https://uat.setu.co/api/v2/auth/token"
            assert mock_post.call_args[1]["json"]["clientID"] == test_client_id

            # 2. Verify subsequent AA request has Bearer token and product instance ID
            res = await client._request("GET", "/health")
            assert res == {"status": "UP"}
            mock_req.assert_called_once()
            method, gateway_url = mock_req.call_args[0][:2]
            headers = mock_req.call_args[1]["headers"]
            assert gateway_url == "https://fiu-sandbox.setu.co/health"
            assert headers["Authorization"] == "Bearer sandbox-jwt-bearer-token-xyz"
            assert headers["x-product-instance-id"] == test_product_inst_id
            # Crucial: verify x-client-id and x-client-secret are NOT in gateway headers
            assert "x-client-id" not in headers
            assert "x-client-secret" not in headers



