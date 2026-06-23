import os
import sys
import tempfile
import uuid

# Isolated env vars must be set BEFORE importing the app — database.py and
# services/rag.py create their engine/Chroma client at import time.
TEST_DIR = tempfile.mkdtemp(prefix="aam_test_")
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DIR}/test.db"
os.environ["CHROMA_STORE_PATH"] = os.path.join(TEST_DIR, "chroma_store")
os.environ["UPLOAD_DIR"] = os.path.join(TEST_DIR, "uploads")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:8000")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def registered_company(client):
    """A fresh company per test — avoids the free plan's 1-document limit
    bleeding between tests that each need to upload their own document."""
    email = f"test-{uuid.uuid4().hex[:10]}@example.com"
    res = client.post("/auth/register", json={
        "name": "Test Co",
        "email": email,
        "password": "testpass123",
    })
    assert res.status_code == 200, res.text
    data = res.json()
    return {
        "token": data["access_token"],
        "company_id": data["company_id"],
        "email": email,
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
    }
