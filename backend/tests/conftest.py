import os
import sys
import tempfile

import pytest

# Use a throwaway SQLite database and a fixed key for tests.
_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_db.name}"
os.environ.setdefault("SECRET_KEY", "test-secret-key")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    init_db()
    return TestClient(app)


def _register_and_login(client, role, email):
    r = client.post(f"/api/auth/register/{role}/", json={"name": email.split("@")[0], "email": email, "password": "pw-123456"})
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login/", json={"email": email, "password": "pw-123456"})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def tokens(client):
    return {
        "host": _register_and_login(client, "host", "host@example.com"),
        "renter": _register_and_login(client, "renter", "renter@example.com"),
        "other": _register_and_login(client, "renter", "other@example.com"),
    }


def auth(token):
    return {"Authorization": f"Bearer {token}"}
