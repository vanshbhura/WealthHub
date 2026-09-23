from datetime import date, timedelta
from app.models.snapshot import PortfolioSnapshot
from app.database import SessionLocal


def test_zero_investment_edge_case(client, test_user_token):
    # When user has no assets or invested value is 0
    res = client.get("/api/portfolio/summary", headers=test_user_token["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["total_wealth"] == 0.0
    assert data["invested_value"] == 0.0
    assert data["profit_loss"] == 0.0
    assert data["profit_loss_percentage"] is None
    assert data["today_change"] is None  # Insufficient historical data


def test_portfolio_calculation_and_pnl(client, test_user_token):
    # Get platforms
    groww = client.get("/api/platforms/groww").json()
    sbi = client.get("/api/platforms/sbi").json()

    # User adds a stock on Groww
    client.post("/api/assets", json={
        "platform_id": groww["id"],
        "asset_type": "STOCKS",
        "name": "Reliance Industries",
        "quantity": 10.0,
        "average_buy_price": 2500.0,
        "invested_amount": 25000.0,
        "current_price": 3000.0,
        "current_value": 30000.0
    }, headers=test_user_token["headers"])

    # User adds a bank balance on SBI
    client.post("/api/accounts", json={
        "platform_id": sbi["id"],
        "account_name": "SBI Savings Account",
        "account_type": "SAVINGS",
        "current_value": 15000.0,
        "invested_value": 15000.0
    }, headers=test_user_token["headers"])

    # Check consolidated summary
    res = client.get("/api/portfolio/summary", headers=test_user_token["headers"])
    assert res.status_code == 200
    summary = res.json()

    # Total wealth: 30000 + 15000 = 45000
    assert summary["total_wealth"] == 45000.0
    # Total invested: 25000 + 15000 = 40000
    assert summary["invested_value"] == 40000.0
    # Profit: 45000 - 40000 = 5000
    assert summary["profit_loss"] == 5000.0
    # Profit percentage: (5000 / 40000) * 100 = 12.5%
    assert summary["profit_loss_percentage"] == 12.5

    # Connected platforms breakdown
    plat_res = client.get("/api/portfolio/platforms", headers=test_user_token["headers"])
    assert plat_res.status_code == 200
    plats = plat_res.json()
    assert len(plats) == 2


def test_user_data_isolation(client, test_user_token, test_user_b_token):
    # User A creates a high-value asset
    groww = client.get("/api/platforms/groww").json()
    asset_res = client.post("/api/assets", json={
        "platform_id": groww["id"],
        "asset_type": "DIGITAL_GOLD",
        "name": "Private Vault Gold",
        "quantity": 10.0,
        "average_buy_price": 5000.0,
        "invested_amount": 50000.0,
        "current_price": 6000.0,
        "current_value": 60000.0
    }, headers=test_user_token["headers"])
    asset_id_a = asset_res.json()["id"]

    # User B checks their own portfolio summary — must be 0!
    res_b = client.get("/api/portfolio/summary", headers=test_user_b_token["headers"])
    assert res_b.status_code == 200
    assert res_b.json()["total_wealth"] == 0.0

    # User B attempts to access User A's asset directly — must return 404
    forbidden_res = client.get(f"/api/assets/{asset_id_a}", headers=test_user_b_token["headers"])
    assert forbidden_res.status_code == 404

    # User B attempts to delete User A's asset directly — must return 404
    forbidden_del = client.delete(f"/api/assets/{asset_id_a}", headers=test_user_b_token["headers"])
    assert forbidden_del.status_code == 404

    # User A's asset must still exist
    check_a = client.get(f"/api/assets/{asset_id_a}", headers=test_user_token["headers"])
    assert check_a.status_code == 200


def test_snapshot_capture_and_daily_change(client, test_user_token, db_session):
    # Trigger snapshot capture
    cap_res = client.post("/api/portfolio/snapshots/capture", headers=test_user_token["headers"])
    assert cap_res.status_code == 200
    snap = cap_res.json()
    assert "snapshot_date" in snap
    assert "total_value" in snap

    # Fetch snapshots by 1M timeframe
    snaps_res = client.get("/api/portfolio/snapshots?timeframe=1M", headers=test_user_token["headers"])
    assert snaps_res.status_code == 200
    assert len(snaps_res.json()) >= 1
