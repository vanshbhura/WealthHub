def test_register_user_success(client):
    response = client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "password": "Password123!",
        "full_name": "New Investor"
    })
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["full_name"] == "New Investor"
    assert "password_hash" not in data["user"]


def test_register_duplicate_email(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "full_name": "Duplicate User"
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_login_invalid_password(client):
    client.post("/api/auth/register", json={
        "email": "loginfail@example.com",
        "password": "CorrectPassword123!",
        "full_name": "Login Fail"
    })
    res = client.post("/api/auth/login", json={
        "email": "loginfail@example.com",
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_success(client):
    client.post("/api/auth/register", json={
        "email": "loginsuccess@example.com",
        "password": "CorrectPassword123!",
        "full_name": "Login Success"
    })
    res = client.post("/api/auth/login", json={
        "email": "loginsuccess@example.com",
        "password": "CorrectPassword123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "loginsuccess@example.com"


def test_auth_me_unauthorized(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_auth_me_authorized(client, test_user_token):
    res = client.get("/api/auth/me", headers=test_user_token["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "usera@example.com"


def test_refresh_token_flow(client):
    reg = client.post("/api/auth/register", json={
        "email": "refresher@example.com",
        "password": "Password123!",
        "full_name": "Token Refresher"
    })
    refresh_token = reg.json()["refresh_token"]

    res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["access_token"] != refresh_token
