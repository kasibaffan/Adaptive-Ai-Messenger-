def test_create_email_reminder(client, registered_company):
    res = client.post("/reminders/", headers=registered_company["headers"], json={
        "channel": "email",
        "customer_email": "customer@example.com",
        "message": "Don't forget your appointment",
        "trigger_type": "no_reply",
        "trigger_value": "1",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["channel"] == "email"
    assert body["customer_email"] == "customer@example.com"


def test_create_sms_reminder(client, registered_company):
    res = client.post("/reminders/", headers=registered_company["headers"], json={
        "channel": "sms",
        "customer_phone": "+14155551234",
        "message": "Your order shipped",
        "trigger_type": "no_reply",
        "trigger_value": "1",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["channel"] == "sms"
    assert body["customer_phone"] == "+14155551234"


def test_sms_reminder_requires_phone(client, registered_company):
    res = client.post("/reminders/", headers=registered_company["headers"], json={
        "channel": "sms",
        "message": "Your order shipped",
        "trigger_type": "no_reply",
        "trigger_value": "1",
    })
    assert res.status_code == 400


def test_email_reminder_requires_email(client, registered_company):
    res = client.post("/reminders/", headers=registered_company["headers"], json={
        "channel": "email",
        "message": "Don't forget",
        "trigger_type": "no_reply",
        "trigger_value": "1",
    })
    assert res.status_code == 400


def test_invalid_channel_rejected(client, registered_company):
    res = client.post("/reminders/", headers=registered_company["headers"], json={
        "channel": "carrier_pigeon",
        "customer_email": "x@example.com",
        "message": "hi",
        "trigger_type": "no_reply",
        "trigger_value": "1",
    })
    assert res.status_code == 400


def test_list_reminders(client, registered_company):
    client.post("/reminders/", headers=registered_company["headers"], json={
        "channel": "email",
        "customer_email": "customer@example.com",
        "message": "Reminder",
        "trigger_type": "no_reply",
        "trigger_value": "1",
    })
    res = client.get("/reminders/", headers=registered_company["headers"])
    assert res.status_code == 200
    assert len(res.json()) == 1
