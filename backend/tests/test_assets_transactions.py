def test_create_and_manage_asset(client, test_user_token):
    # Get Groww platform
    plat_res = client.get("/api/platforms/groww")
    groww_id = plat_res.json()["id"]

    # Create asset
    asset_payload = {
        "platform_id": groww_id,
        "asset_type": "MUTUAL_FUNDS",
        "name": "Parag Parikh Flexi Cap Fund",
        "quantity": 100.0,
        "average_buy_price": 50.0,
        "invested_amount": 5000.0,
        "current_price": 65.0,
        "current_value": 6500.0,
        "currency": "INR"
    }
    create_res = client.post("/api/assets", json=asset_payload, headers=test_user_token["headers"])
    assert create_res.status_code == 201
    asset = create_res.json()
    asset_id = asset["id"]
    assert asset["name"] == "Parag Parikh Flexi Cap Fund"
    assert asset["invested_amount"] == 5000.0
    assert asset["current_value"] == 6500.0

    # Retrieve asset
    get_res = client.get(f"/api/assets/{asset_id}", headers=test_user_token["headers"])
    assert get_res.status_code == 200

    # Update asset valuation
    patch_res = client.patch(f"/api/assets/{asset_id}", json={"current_price": 70.0, "current_value": 7000.0}, headers=test_user_token["headers"])
    assert patch_res.status_code == 200
    assert patch_res.json()["current_value"] == 7000.0

    # Create BUY transaction
    tx_payload = {
        "asset_id": asset_id,
        "transaction_type": "BUY",
        "quantity": 50.0,
        "price": 70.0,
        "amount": 3500.0,
        "fees": 10.0,
        "taxes": 5.0
    }
    tx_res = client.post("/api/transactions", json=tx_payload, headers=test_user_token["headers"])
    assert tx_res.status_code == 201
    tx = tx_res.json()
    assert tx["amount"] == 3500.0

    # Verify asset was updated by BUY: quantity 100 + 50 = 150
    updated_asset = client.get(f"/api/assets/{asset_id}", headers=test_user_token["headers"]).json()
    assert updated_asset["quantity"] == 150.0
    assert updated_asset["invested_amount"] == 5000.0 + 3500.0 + 10.0 + 5.0

    # Filter transactions
    tx_list = client.get(f"/api/transactions?asset_id={asset_id}&transaction_type=BUY", headers=test_user_token["headers"])
    assert tx_list.status_code == 200
    assert len(tx_list.json()) == 1

    # Delete asset
    del_res = client.delete(f"/api/assets/{asset_id}", headers=test_user_token["headers"])
    assert del_res.status_code == 204

    # Verify deleted
    get_del = client.get(f"/api/assets/{asset_id}", headers=test_user_token["headers"])
    assert get_del.status_code == 404
