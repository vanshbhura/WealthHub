def test_list_platforms(client):
    res = client.get("/api/platforms")
    assert res.status_code == 200
    platforms = res.json()
    assert len(platforms) >= 14
    slugs = [p["slug"] for p in platforms]
    assert "groww" in slugs
    assert "zerodha" in slugs
    assert "sbi" in slugs
    assert "lendenclub" in slugs


def test_filter_platforms_by_category(client):
    res = client.get("/api/platforms?category=BROKER")
    assert res.status_code == 200
    brokers = res.json()
    assert len(brokers) >= 5
    for b in brokers:
        assert b["category"] == "BROKER"

    res_bank = client.get("/api/platforms?category=BANK")
    assert res_bank.status_code == 200
    banks = res_bank.json()
    for bank in banks:
        assert bank["category"] == "BANK"


def test_get_platform_by_slug(client):
    res = client.get("/api/platforms/groww")
    assert res.status_code == 200
    data = res.json()
    assert data["slug"] == "groww"
    assert data["name"] == "Groww"


def test_get_nonexistent_platform(client):
    res = client.get("/api/platforms/non-existent-platform-xyz")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PLATFORM_NOT_FOUND"
