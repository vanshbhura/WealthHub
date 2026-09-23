import uuid
from datetime import datetime, date
import pytest
from app.models.platform import Platform
from app.models.connection import Connection
from app.models.account import Account
from app.models.asset import Asset
from app.models.snapshot import PortfolioSnapshot
from app.services.portfolio_service import PortfolioService
from app.services.valuation_service import ValuationService
from app.services.snapshot_service import SnapshotService


def test_platform_catalog_endpoint_success_and_entries(client):
    """6 & 7: Verify platform catalog endpoint returns successfully and contains existing entries."""
    res = client.get("/api/platforms")
    assert res.status_code == 200
    platforms = res.json()
    assert len(platforms) >= 19

    # Verify key platforms exist
    slugs = {p["slug"] for p in platforms}
    for expected in ["groww", "zerodha", "sbi", "lendenclub", "phonepe", "jar", "account-aggregator"]:
        assert expected in slugs, f"Expected {expected} in platform catalog"

    # Verify categories
    categories = {p["category"] for p in platforms}
    assert "BROKER" in categories
    assert "BANK" in categories
    assert "P2P" in categories
    assert "DIGITAL_GOLD" in categories
    assert "AGGREGATOR" in categories


def test_account_aggregator_sandbox_not_connected_by_default(client):
    """8 & 9: Verify Account Aggregator sandbox remains available and not represented as connected."""
    res = client.get("/api/platforms/account-aggregator")
    assert res.status_code == 200
    data = res.json()
    assert data["slug"] == "account-aggregator"
    assert data["integration_type"] == "ACCOUNT_AGGREGATOR"
    assert "Sandbox" in data["description"] or "sandbox" in data["description"].lower()

    # Check connectors for account-aggregator
    conn_res = client.get("/api/platforms/account-aggregator/connectors")
    assert conn_res.status_code == 200
    connectors = conn_res.json()
    assert len(connectors) > 0

    # Never automatically mark as CONNECTED in public catalog
    for c in connectors:
        assert c["status"] in ("AVAILABLE", "SANDBOX", "COMING_SOON")


def test_user_with_valid_holdings_gets_nonzero_total_wealth(client, db_session, test_user_token):
    """1, 2, 4: Verify user with valid platform holdings gets non-zero total wealth equaling platform totals."""
    user_id = uuid.UUID(test_user_token["user"]["id"])

    # Find groww and zerodha platforms
    groww = db_session.query(Platform).filter_by(slug="groww").first()
    zerodha = db_session.query(Platform).filter_by(slug="zerodha").first()
    assert groww is not None
    assert zerodha is not None

    # Create connection for Groww
    conn_groww = Connection(
        id=uuid.uuid4(),
        user_id=user_id,
        platform_id=groww.id,
        status="CONNECTED",
        last_synced_at=datetime.utcnow()
    )
    db_session.add(conn_groww)

    # Add Asset 1 (Groww): Current 342650, Invested 295000
    asset_groww = Asset(
        id=uuid.uuid4(),
        user_id=user_id,
        platform_id=groww.id,
        name="Parag Parikh Flexi Cap Direct",
        symbol="PPFAS",
        asset_type="MUTUAL_FUNDS",
        quantity=890.3,
        current_price=384.87,
        current_value=342650.0,
        invested_amount=295000.0,
        last_valued_at=datetime.utcnow(),
        data_source="BROKER_API"
    )
    db_session.add(asset_groww)

    # Create connection for Zerodha
    conn_zerodha = Connection(
        id=uuid.uuid4(),
        user_id=user_id,
        platform_id=zerodha.id,
        status="CONNECTED",
        last_synced_at=datetime.utcnow()
    )
    db_session.add(conn_zerodha)

    # Add Asset 2 (Zerodha): Current 182400, Invested 155000
    asset_zerodha = Asset(
        id=uuid.uuid4(),
        user_id=user_id,
        platform_id=zerodha.id,
        name="Nifty 50 ETF",
        symbol="NIFTYBEES",
        asset_type="ETFS",
        quantity=800.0,
        current_price=228.0,
        current_value=182400.0,
        invested_amount=155000.0,
        last_valued_at=datetime.utcnow(),
        data_source="BROKER_API"
    )
    db_session.add(asset_zerodha)
    db_session.commit()

    # Call summary endpoint
    sum_res = client.get("/api/portfolio/summary", headers=test_user_token["headers"])
    assert sum_res.status_code == 200
    sum_data = sum_res.json()

    expected_total = 342650.0 + 182400.0  # 525,050.0
    expected_invested = 295000.0 + 155000.0  # 450,000.0
    expected_pnl = expected_total - expected_invested  # 75,050.0

    assert sum_data["total_wealth"] == expected_total
    assert sum_data["total_wealth"] > 0
    assert sum_data["invested_value"] == expected_invested
    assert sum_data["profit_loss"] == expected_pnl

    # Call platforms breakdown endpoint
    plat_res = client.get("/api/portfolio/platforms", headers=test_user_token["headers"])
    assert plat_res.status_code == 200
    plat_data = plat_res.json()
    assert len(plat_data) == 2

    plat_total_sum = sum(p["current_value"] for p in plat_data)
    assert plat_total_sum == sum_data["total_wealth"]


def test_graph_current_value_matches_total_wealth(client, db_session, test_user_token):
    """3: Verify graph current value and summary total wealth are identical."""
    user_id = uuid.UUID(test_user_token["user"]["id"])
    sbi = db_session.query(Platform).filter_by(slug="sbi").first()

    account = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        platform_id=sbi.id,
        account_name="SBI Savings",
        account_type="SAVINGS",
        masked_identifier="*1234",
        current_value=89200.0,
        invested_value=80000.0,
        currency="INR"
    )
    db_session.add(account)
    db_session.commit()

    # Check summary
    sum_res = client.get("/api/portfolio/summary", headers=test_user_token["headers"])
    assert sum_res.status_code == 200
    summary_wealth = sum_res.json()["total_wealth"]
    assert summary_wealth == 89200.0

    # Capture snapshot for today
    snapshot = SnapshotService.capture_daily_snapshot(user_id=user_id, db=db_session)
    assert snapshot.total_value == summary_wealth

    # Check snapshots endpoint
    snap_res = client.get("/api/portfolio/snapshots?envelope=true", headers=test_user_token["headers"])
    assert snap_res.status_code == 200
    snap_data = snap_res.json()
    assert snap_data["data_points_count"] >= 1
    assert snap_data["snapshots"][-1]["value"] == summary_wealth


def test_api_failure_does_not_convert_to_zero(client):
    """5: Verify API authentication failure returns 401 Unauthorized, never 200 with total_wealth=0."""
    res = client.get("/api/portfolio/summary")
    assert res.status_code == 401
    err_body = res.json()
    assert err_body.get("success") is False or "error" in err_body or "detail" in err_body


def test_user_data_isolation_remains_intact(client, db_session, test_user_token, test_user_b_token):
    """10: Verify user data isolation: User A's wealth is completely isolated from User B."""
    user_a_id = uuid.UUID(test_user_token["user"]["id"])
    groww = db_session.query(Platform).filter_by(slug="groww").first()

    asset_a = Asset(
        id=uuid.uuid4(),
        user_id=user_a_id,
        platform_id=groww.id,
        name="User A Private Asset",
        asset_type="STOCKS",
        quantity=10,
        current_price=1000.0,
        current_value=10000.0,
        invested_amount=9000.0,
        data_source="MANUAL"
    )
    db_session.add(asset_a)
    db_session.commit()

    # User A sees 10000
    res_a = client.get("/api/portfolio/summary", headers=test_user_token["headers"])
    assert res_a.json()["total_wealth"] == 10000.0

    # User B has no assets, sees 0
    res_b = client.get("/api/portfolio/summary", headers=test_user_b_token["headers"])
    assert res_b.json()["total_wealth"] == 0.0
