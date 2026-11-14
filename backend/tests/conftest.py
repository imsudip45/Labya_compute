import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
# A throwaway database built by the real migrations, and a fixed key.
# Set TEST_DATABASE_URL to an empty PostgreSQL database to test against Postgres.
_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_db.close()
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_db.name}"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-123"
os.environ["ENVIRONMENT"] = "development"
for k, v in {"CLOUDFLARE_API_TOKEN": "t", "CLOUDFLARE_ACCOUNT_ID": "a", "CLOUDFLARE_ZONE_ID": "z", "TUNNEL_DOMAIN": "labhya.test"}.items():
    os.environ[k] = v
sys.path.insert(0, str(BACKEND))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

ALEMBIC = Config(str(BACKEND / "alembic.ini"))


class FakeCloudflare:
    """Stands in for app.cloudflare and records what the API asked Cloudflare to do."""

    def __init__(self):
        self.tunnels, self.routes, self.dns = [], {}, {}

    def create_tunnel(self, name):
        self.tunnels.append(name)
        return f"tunnel-{len(self.tunnels)}"

    def tunnel_token(self, tunnel_id):
        return f"token-for-{tunnel_id}"

    def set_routes(self, tunnel_id, routes):
        self.routes[tunnel_id] = dict(routes)

    def add_dns(self, hostname, tunnel_id):
        self.dns[f"rec-{hostname}"] = hostname
        return f"rec-{hostname}"

    def remove_dns(self, record_id):
        del self.dns[record_id]


@pytest.fixture(scope="session")
def cf():
    import app.cloudflare as real
    fake = FakeCloudflare()
    patch = pytest.MonkeyPatch()
    for name in ("create_tunnel", "tunnel_token", "set_routes", "add_dns", "remove_dns"):
        patch.setattr(real, name, getattr(fake, name))
    yield fake
    patch.undo()


@pytest.fixture(scope="session")
def client(cf):
    command.upgrade(ALEMBIC, "head")
    return TestClient(app)


def register(client, role, email, password="pw-123456"):
    r = client.post(f"/api/auth/register/{role}/", json={"name": email.split("@")[0], "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def tokens(client):
    return {
        "host": register(client, "host", "host@example.com"),
        "renter": register(client, "renter", "renter@example.com"),
        "other": register(client, "renter", "other@example.com"),
    }
