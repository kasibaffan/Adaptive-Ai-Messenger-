import io


def _upload(client, headers, filename="doc.txt", content=b"Some FAQ content. Store hours are 9 to 5."):
    return client.post(
        "/documents/upload",
        headers=headers,
        files={"file": (filename, io.BytesIO(content), "text/plain")},
    )


def test_upload_success(client, registered_company):
    res = _upload(client, registered_company["headers"])
    assert res.status_code == 200
    assert res.json()["filename"] == "doc.txt"


def test_unsupported_extension_rejected(client, registered_company):
    res = _upload(client, registered_company["headers"], filename="doc.exe")
    assert res.status_code == 400


def test_free_plan_blocks_second_document(client, registered_company):
    first = _upload(client, registered_company["headers"], filename="one.txt")
    assert first.status_code == 200
    second = _upload(client, registered_company["headers"], filename="two.txt")
    assert second.status_code == 403
    assert "plan allows" in second.json()["detail"]


def test_list_documents(client, registered_company):
    _upload(client, registered_company["headers"])
    res = client.get("/documents/", headers=registered_company["headers"])
    assert res.status_code == 200
    assert len(res.json()) == 1
