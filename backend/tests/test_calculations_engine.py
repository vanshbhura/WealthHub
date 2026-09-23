import uuid
from datetime import date, datetime, timedelta
import pytest
from app.models.snapshot import PortfolioSnapshot
from app.models.transaction import Transaction, TransactionType
from app.models.asset import Asset
from app.models.account import Account
from app.services.valuation_service import ValuationService
from app.services.pnl_service import PnlService
from app.services.performance_service import PerformanceService
from app.services.allocation_service import AllocationService
from app.services.snapshot_service import SnapshotService
from app.services.portfolio_service import PortfolioService
from app.domain.enums import AssetCategory, normalize_asset_category


# 1. TOTAL WEALTH TESTS
def test_total_wealth_zero_assets(client, test_user_token):
    res = client.get("/api/portfolio/summary", headers=test_user_token["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["total_wealth"] == 0.0
    assert data["invested_value"] == 0.0
    assert data["profit_loss"] == 0.0
    assert data["profit_loss_percentage"] is None


def test_total_wealth_single_and_multiple_assets(client, test_user_token):
    groww = client.get("/api/platforms/groww").json()
    zerodha = client.get("/api/platforms/zerodha").json()
    sbi = client.get("/api/platforms/sbi").json()

    # Asset 1 on Groww (Stock)
    client.post("/api/assets", json={
        "platform_id": groww["id"],
        "asset_type": "STOCK",
        "name": "Tata Consultancy Services",
        "quantity": 10.0,
        "average_buy_price": 3500.0,
        "invested_amount": 35000.0,
        "current_price": 4000.0,
        "current_value": 40000.0
    }, headers=test_user_token["headers"])

    # Asset 2 on Zerodha (ETF)
    client.post("/api/assets", json={
        "platform_id": zerodha["id"],
        "asset_type": "ETF",
        "name": "Nifty 50 BeES",
        "quantity": 100.0,
        "average_buy_price": 220.0,
        "invested_amount": 22000.0,
        "current_price": 250.0,
        "current_value": 25000.0
    }, headers=test_user_token["headers"])

    # Account on SBI (Savings Bank)
    client.post("/api/accounts", json={
        "platform_id": sbi["id"],
        "account_name": "SBI Primary Savings",
        "account_type": "SAVINGS",
        "current_value": 50000.0,
        "invested_value": 50000.0
    }, headers=test_user_token["headers"])

    res = client.get("/api/portfolio/summary", headers=test_user_token["headers"])
    assert res.status_code == 200
    data = res.json()
    # Total wealth: 40000 + 25000 + 50000 = 115000
    assert data["total_wealth"] == 115000.0
    # Total invested: 35000 + 22000 + 50000 = 107000
    assert data["invested_value"] == 107000.0
    # P&L: 115000 - 107000 = 8000
    assert data["profit_loss"] == 8000.0
    # P&L %: 8000 / 107000 * 100 = 7.48%
    assert round(data["profit_loss_percentage"], 2) == 7.48
    assert data["platform_count"] == 3


# 2. P&L TESTS: Profit, Loss, Zero Invested
def test_pnl_profit_and_loss_and_zero_invested():
    # Profit case
    pnl, pct = PnlService.calculate(current_value=120000.0, invested_value=100000.0)
    assert pnl == 20000.0
    assert pct == 20.0

    # Loss case
    pnl, pct = PnlService.calculate(current_value=85000.0, invested_value=100000.0)
    assert pnl == -15000.0
    assert pct == -15.0

    # Zero invested amount case (Null return percentage, not NaN or Inf)
    pnl, pct = PnlService.calculate(current_value=1000.0, invested_value=0.0)
    assert pnl == 1000.0
    assert pct is None

    pnl, pct = PnlService.calculate(current_value=0.0, invested_value=0.0)
    assert pnl == 0.0
    assert pct is None


# 3. DAILY CHANGE TESTS
def test_daily_change_scenarios():
    # Previous snapshot exists: 1,00,000 -> 1,05,000 (+5,000, +5.0%)
    change, pct = PerformanceService.calculate_daily_change(105000.0, 100000.0)
    assert change == 5000.0
    assert pct == 5.0

    # Negative movement
    change, pct = PerformanceService.calculate_daily_change(95000.0, 100000.0)
    assert change == -5000.0
    assert pct == -5.0

    # No previous snapshot exists
    change, pct = PerformanceService.calculate_daily_change(100000.0, None)
    assert change is None
    assert pct is None

    # Zero previous value
    change, pct = PerformanceService.calculate_daily_change(100000.0, 0.0)
    assert change is None
    assert pct is None


# 4. GOLD / SILVER PRECIOUS METALS VALUATION
def test_gold_silver_valuation(client, test_user_token):
    jar = client.get("/api/platforms/jar").json()

    # Add 10 grams Gold at average buy price 6500/g, current price 7200/g
    res = client.post("/api/assets", json={
        "platform_id": jar["id"],
        "asset_type": "DIGITAL_GOLD",
        "name": "SafeGold 24K 995",
        "quantity": 10.0,
        "average_buy_price": 6500.0,
        "invested_amount": 65000.0,
        "current_price": 7200.0,
        "current_value": 72000.0
    }, headers=test_user_token["headers"])
    assert res.status_code == 201

    # Check calculated assets API
    assets_res = client.get("/api/portfolio/assets?asset_type=DIGITAL_GOLD", headers=test_user_token["headers"])
    assert assets_res.status_code == 200
    items = assets_res.json()
    assert len(items) >= 1
    gold_item = items[0]
    assert gold_item["quantity"] == 10.0
    assert gold_item["invested_value"] == 65000.0
    assert gold_item["current_value"] == 72000.0
    assert gold_item["profit_loss"] == 7000.0
    assert round(gold_item["profit_loss_percentage"], 2) == 10.77
    assert gold_item["precious_metal_details"]["grams"] == 10.0


# 5. P2P CALCULATIONS
def test_p2p_valuation(client, test_user_token):
    lenden = client.get("/api/platforms/lendenclub").json()

    # P2P loan pool: 50,000 principal invested, 45,000 principal outstanding, 6,500 interest received
    client.post("/api/assets", json={
        "platform_id": lenden["id"],
        "asset_type": "P2P",
        "name": "FMPP Loan Pool Alpha",
        "quantity": 1.0,
        "invested_amount": 50000.0,
        "current_value": 45000.0,
        "metadata_json": {
            "principal_invested": 50000.0,
            "principal_outstanding": 45000.0,
            "interest_received": 6500.0,
            "repayments": 5000.0
        }
    }, headers=test_user_token["headers"])

    assets_res = client.get("/api/portfolio/assets?asset_type=P2P", headers=test_user_token["headers"])
    assert assets_res.status_code == 200
    p2p_items = assets_res.json()
    assert len(p2p_items) >= 1
    p2p_asset = p2p_items[0]
    assert p2p_asset["p2p_details"]["principal_invested"] == 50000.0
    assert p2p_asset["p2p_details"]["interest_received"] == 6500.0
    assert p2p_asset["p2p_details"]["repayments"] == 5000.0


# 6. ALLOCATION: PERCENTAGES SUM CORRECTLY TO 100%
def test_portfolio_allocation(client, test_user_token):
    groww = client.get("/api/platforms/groww").json()
    sbi = client.get("/api/platforms/sbi").json()

    # Asset 1 (Equity) 60k
    client.post("/api/assets", json={
        "platform_id": groww["id"],
        "asset_type": "STOCK",
        "name": "Infosys",
        "quantity": 40.0,
        "average_buy_price": 1500.0,
        "invested_amount": 60000.0,
        "current_price": 1500.0,
        "current_value": 60000.0
    }, headers=test_user_token["headers"])

    # Account (Cash) 40k
    client.post("/api/accounts", json={
        "platform_id": sbi["id"],
        "account_name": "SBI Savings",
        "account_type": "SAVINGS",
        "current_value": 40000.0,
        "invested_value": 40000.0
    }, headers=test_user_token["headers"])

    alloc_res = client.get("/api/portfolio/allocation", headers=test_user_token["headers"])
    assert alloc_res.status_code == 200
    alloc = alloc_res.json()

    assert alloc["total_basis"] == 100000.0
    by_type = alloc["by_asset_type"]
    total_pct_type = sum(s["percentage"] for s in by_type)
    assert abs(total_pct_type - 100.0) < 0.1

    by_plat = alloc["by_platform"]
    total_pct_plat = sum(s["percentage"] for s in by_plat)
    assert abs(total_pct_plat - 100.0) < 0.1


# 7. INTERNAL TRANSFERS: NO DOUBLE COUNTING
def test_internal_transfers_no_double_counting(client, test_user_token, db_session):
    sbi = client.get("/api/platforms/sbi").json()
    groww = client.get("/api/platforms/groww").json()

    # User creates SBI account with 100,000
    acc_sbi = client.post("/api/accounts", json={
        "platform_id": sbi["id"],
        "account_name": "SBI Main Account",
        "account_type": "SAVINGS",
        "current_value": 100000.0,
        "invested_value": 100000.0
    }, headers=test_user_token["headers"]).json()

    # User transfers 50,000 from SBI to Groww
    # Create matching TRANSFER_OUT on SBI and TRANSFER_IN on Groww
    transfer_ref = "TX-INT-50000-SBI-GROWW"

    client.post("/api/transactions", json={
        "transaction_type": "TRANSFER_OUT",
        "amount": 50000.0,
        "external_transaction_id": transfer_ref,
        "currency": "INR"
    }, headers=test_user_token["headers"])

    client.post("/api/transactions", json={
        "transaction_type": "TRANSFER_IN",
        "amount": 50000.0,
        "external_transaction_id": transfer_ref,
        "currency": "INR"
    }, headers=test_user_token["headers"])

    # Update account balances reflecting the transfer (SBI has 50k left, Groww has 50k)
    client.patch(f"/api/accounts/{acc_sbi['id']}", json={
        "current_value": 50000.0,
        "invested_value": 50000.0
    }, headers=test_user_token["headers"])

    client.post("/api/accounts", json={
        "platform_id": groww["id"],
        "account_name": "Groww Trading Balance",
        "account_type": "TRADING_WALLET",
        "current_value": 50000.0,
        "invested_value": 50000.0
    }, headers=test_user_token["headers"])

    # Check total wealth: 50,000 + 50,000 = 100,000 (NOT 1,50,000!)
    summary = client.get("/api/portfolio/summary", headers=test_user_token["headers"]).json()
    assert summary["total_wealth"] == 100000.0
    assert summary["invested_value"] == 100000.0


# 8. SNAPSHOT ENGINE IDEMPOTENCY & PERIOD FILTERS
def test_snapshot_engine_idempotency_and_periods(client, test_user_token):
    # Capture snapshot
    cap1 = client.post("/api/portfolio/snapshots/capture", headers=test_user_token["headers"])
    assert cap1.status_code == 200
    snap1 = cap1.json()

    # Capture snapshot again on same day — must update, NOT create duplicate
    cap2 = client.post("/api/portfolio/snapshots/capture", headers=test_user_token["headers"])
    assert cap2.status_code == 200
    snap2 = cap2.json()
    assert snap1["id"] == snap2["id"]

    # Test period parameter query
    for period in ["1M", "2M", "6M", "12M", "24M", "5Y"]:
        res = client.get(f"/api/portfolio/snapshots?period={period}", headers=test_user_token["headers"])
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    # Test envelope query
    env_res = client.get("/api/portfolio/snapshots?period=1M&envelope=true", headers=test_user_token["headers"])
    assert env_res.status_code == 200
    env_data = env_res.json()
    assert "has_sufficient_history" in env_data
    assert "snapshots" in env_data


# 9. USER ISOLATION
def test_strict_user_isolation(client, test_user_token, test_user_b_token):
    groww = client.get("/api/platforms/groww").json()

    # User A has 10,00,000 asset
    client.post("/api/assets", json={
        "platform_id": groww["id"],
        "asset_type": "REAL_ESTATE",
        "name": "Luxury Apartment",
        "quantity": 1.0,
        "invested_amount": 800000.0,
        "current_value": 1000000.0
    }, headers=test_user_token["headers"])

    # User B summary must not see User A's wealth
    res_b = client.get("/api/portfolio/summary", headers=test_user_b_token["headers"])
    assert res_b.status_code == 200
    assert res_b.json()["total_wealth"] == 0.0
    assert res_b.json()["invested_value"] == 0.0
