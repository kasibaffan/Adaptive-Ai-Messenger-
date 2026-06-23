def test_plans_lists_three_tiers(client):
    res = client.get("/billing/plans")
    assert res.status_code == 200
    assert set(res.json().keys()) == {"free", "pro", "enterprise"}


def test_status_defaults_free_and_unconfigured(client, registered_company):
    res = client.get("/billing/status", headers=registered_company["headers"])
    assert res.status_code == 200
    body = res.json()
    assert body["plan"] == "free"
    assert body["billing_configured"] is False


def test_checkout_without_stripe_keys_returns_503(client, registered_company):
    res = client.post("/billing/checkout", headers=registered_company["headers"])
    assert res.status_code == 503
