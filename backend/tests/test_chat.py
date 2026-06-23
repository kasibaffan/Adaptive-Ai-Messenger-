import io


def test_chat_unknown_company_returns_404(client):
    res = client.post("/chat/does-not-exist", json={"message": "hi", "customer_id": "c1"})
    assert res.status_code == 404


def test_chat_without_documents_returns_fallback(client, registered_company):
    res = client.post(f"/chat/{registered_company['company_id']}", json={
        "message": "what are your hours",
        "customer_id": "c1",
    })
    assert res.status_code == 200
    body = res.json()
    assert "don't have that information" in body["reply"]
    assert body["sources_used"] == 0


def test_chat_answers_from_uploaded_document(client, registered_company):
    headers = registered_company["headers"]
    client.post(
        "/documents/upload",
        headers=headers,
        files={"file": ("faq.txt", io.BytesIO(
            b"Our store hours are 9am to 6pm, Monday through Friday. "
            b"We accept Visa, Mastercard, and PayPal."
        ), "text/plain")},
    )
    res = client.post(f"/chat/{registered_company['company_id']}", json={
        "message": "what are your store hours",
        "customer_id": "c1",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["sources_used"] >= 1
    assert "9am" in body["reply"] or "9" in body["reply"]


def test_unanswerable_question_logged_as_knowledge_gap(client, registered_company):
    headers = registered_company["headers"]
    client.post(
        "/documents/upload",
        headers=headers,
        files={"file": ("faq.txt", io.BytesIO(b"Our store hours are 9am to 6pm."), "text/plain")},
    )
    client.post(f"/chat/{registered_company['company_id']}", json={
        "message": "do you sell rocket ships",
        "customer_id": "c1",
    })
    res = client.get("/gaps/", headers=headers)
    assert res.status_code == 200
    questions = [g["question"] for g in res.json()]
    assert "do you sell rocket ships" in questions
