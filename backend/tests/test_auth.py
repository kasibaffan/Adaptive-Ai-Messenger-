def test_register_returns_token(client):
    res = client.post("/auth/register", json={
        "name": "Acme",
        "email": "auth-test-1@example.com",
        "password": "secret123",
    })
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["company_name"] == "Acme"


def test_duplicate_email_rejected(client):
    payload = {"name": "Acme", "email": "dupe@example.com", "password": "secret123"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 200
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 400


def test_login_success(client, registered_company):
    res = client.post("/auth/login", json={
        "email": registered_company["email"],
        "password": "testpass123",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password(client, registered_company):
    res = client.post("/auth/login", json={
        "email": registered_company["email"],
        "password": "wrongpass",
    })
    assert res.status_code == 401


def test_me_defaults_to_free_plan(client, registered_company):
    res = client.get("/auth/me", headers=registered_company["headers"])
    assert res.status_code == 200
    body = res.json()
    assert body["plan"] == "free"
    assert body["brand_color"] == "#4f46e5"


def test_delete_account_wrong_password_rejected(client, registered_company):
    res = client.request(
        "DELETE", "/auth/account",
        headers=registered_company["headers"],
        json={"password": "not-the-right-password"},
    )
    assert res.status_code == 401


def test_delete_account_removes_company(client, registered_company):
    res = client.request(
        "DELETE", "/auth/account",
        headers=registered_company["headers"],
        json={"password": "testpass123"},
    )
    assert res.status_code == 200

    # Account is gone — login no longer works
    login = client.post("/auth/login", json={
        "email": registered_company["email"],
        "password": "testpass123",
    })
    assert login.status_code == 401

    # Token is also dead — the company row backing it no longer exists
    me = client.get("/auth/me", headers=registered_company["headers"])
    assert me.status_code == 401
