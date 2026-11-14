from datetime import timedelta
from decimal import Decimal

from alembic import command
from sqlmodel import Session as DB

from app.db import engine
from app.models import Session
from tests.conftest import ALEMBIC, auth, register


def _gpu(client, host, price=100):
    r = client.post("/api/gpus/", headers=host, json={"gpu_name": "RTX 3060", "gpu_memory": 12, "gpu_price": price, "gpu_location": "Kathmandu"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _start(client, host, sid, port=22001):
    """What the agent does: get its tunnel, start the container, report it started."""
    assert client.post("/api/hosts/tunnel/", headers=host).status_code == 200
    return client.post(f"/api/sessions/{sid}/mark_started/", headers=host, json={"ssh_password": "pw-abcdefgh", "host_port": port})


def _balance(client, who):
    return Decimal(str(client.get("/api/wallets/", headers=who).json()["balance"]))


def _backdate_start(session_id, hours):
    """Pretend the session started `hours` ago."""
    import uuid
    with DB(engine) as db:
        s = db.get(Session, uuid.UUID(session_id))
        s.start_time -= timedelta(hours=hours)
        db.add(s)
        db.commit()


def test_migrations_match_models(client):
    command.check(ALEMBIC)  # fails if a model changed without a migration


def test_rental_flow_and_access_control(client, tokens):
    host, renter, other = (auth(tokens[k]["access"]) for k in ("host", "renter", "other"))
    gpu_id = _gpu(client, host)
    assert any(g["id"] == gpu_id for g in client.get("/api/gpus/available/").json())
    assert client.post("/api/wallets/add_funds/", headers=renter, json={"amount": 1000}).status_code == 200

    r = client.post("/api/sessions/", headers=renter, json={"gpu": gpu_id})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    # Rented GPUs leave the public list, and can't be rented twice
    assert all(g["id"] != gpu_id for g in client.get("/api/gpus/available/").json())
    client.post("/api/wallets/add_funds/", headers=other, json={"amount": 1000})
    assert client.post("/api/sessions/", headers=other, json={"gpu": gpu_id}).status_code == 409

    # Only the session's renter or host can see it (it contains SSH details)
    assert client.get(f"/api/sessions/{sid}/").status_code == 401
    assert client.get(f"/api/sessions/{sid}/", headers=other).status_code == 404
    assert client.get(f"/api/sessions/{sid}/", headers=renter).status_code == 200

    # Only the host running it can report its state
    started = {"ssh_password": "pw-abcdefgh", "host_port": 22001}
    assert client.post(f"/api/sessions/{sid}/mark_started/", headers=renter, json=started).status_code == 403
    assert _start(client, host, sid).status_code == 200
    assert _start(client, host, sid).status_code == 409  # only once
    metrics = {"gpu_utilization": 50, "memory_utilization": 40, "temperature": 60}
    assert client.post(f"/api/sessions/{sid}/update_gpu_metrics/", headers=host, json=metrics).status_code == 200
    assert client.post(f"/api/sessions/{sid}/update_gpu_metrics/", headers=host, json={**metrics, "gpu_utilization": 101}).status_code == 422

    # Two hours at Rs 100/hr: the renter pays exactly what the host earns
    _backdate_start(sid, 2)
    before_r, before_h = _balance(client, renter), _balance(client, host)
    assert client.post(f"/api/sessions/{sid}/end_session/", headers=other).status_code == 404
    r = client.post(f"/api/sessions/{sid}/end_session/", headers=renter)
    assert r.status_code == 200, r.text
    cost = Decimal(str(r.json()["total_cost"]))
    assert Decimal("200") <= cost < Decimal("201")
    assert _balance(client, renter) == before_r - cost
    assert _balance(client, host) == before_h + cost
    assert client.post(f"/api/sessions/{sid}/end_session/", headers=host).status_code == 409
    assert any(g["id"] == gpu_id for g in client.get("/api/gpus/available/").json())

    # A GPU with session history can't be deleted (billing references it)
    assert client.delete(f"/api/gpus/{gpu_id}/", headers=host).status_code == 400
    # Another host can't touch it
    intruder = auth(register(client, "host", "intruder@example.com")["access"])
    assert client.patch(f"/api/gpus/{gpu_id}/", headers=intruder, json={"gpu_price": 1}).status_code == 404


def test_cancelled_request_costs_nothing(client, tokens):
    host, renter = auth(tokens["host"]["access"]), auth(tokens["renter"]["access"])
    gpu_id = _gpu(client, host)
    before = _balance(client, renter)
    sid = client.post("/api/sessions/", headers=renter, json={"gpu": gpu_id}).json()["id"]
    r = client.post(f"/api/sessions/{sid}/end_session/", headers=renter)
    assert r.json()["status"] == "CANCELLED" and _balance(client, renter) == before


def test_session_ends_when_wallet_runs_out(client):
    host = auth(register(client, "host", "h2@example.com")["access"])
    renter = auth(register(client, "renter", "r2@example.com")["access"])
    gpu_id = _gpu(client, host, price=300)
    assert client.post("/api/sessions/", headers=renter, json={"gpu": gpu_id}).status_code == 400  # balance 0
    client.post("/api/wallets/add_funds/", headers=renter, json={"amount": 300})
    sid = client.post("/api/sessions/", headers=renter, json={"gpu": gpu_id}).json()["id"]
    _start(client, host, sid)

    client.get("/api/sessions/pending_for_host/", headers=host)  # the agent's poll
    assert client.get(f"/api/sessions/{sid}/", headers=renter).json()["status"] == "ACTIVE"

    _backdate_start(sid, 1.5)  # Rs 450 owed, Rs 300 in the wallet
    client.get("/api/sessions/pending_for_host/", headers=host)
    s = client.get(f"/api/sessions/{sid}/", headers=renter).json()
    assert s["status"] == "COMPLETED"
    assert _balance(client, renter) < 0  # the debt is recorded, and blocks new rentals
    assert client.post("/api/sessions/", headers=renter, json={"gpu": gpu_id}).status_code == 400


def test_tokens(client, tokens):
    renter = tokens["renter"]
    r = client.post("/api/auth/refresh/", json={"refresh": renter["refresh"]})
    assert r.status_code == 200 and r.json()["access"]
    assert client.post("/api/auth/refresh/", json={"refresh": renter["access"]}).status_code == 401
    assert client.get("/api/wallets/", headers=auth(renter["refresh"])).status_code == 401
    assert client.get("/api/wallets/", headers=auth("not-a-token")).status_code == 401


def test_logout_revokes_tokens(client):
    t = register(client, "renter", "leaver@example.com")
    assert client.post("/api/auth/logout/", headers=auth(t["access"])).status_code == 204
    assert client.get("/api/auth/me/", headers=auth(t["access"])).status_code == 401
    assert client.post("/api/auth/refresh/", json={"refresh": t["refresh"]}).status_code == 401


def test_login_lockout(client):
    register(client, "renter", "Locked@Example.com")
    bad = {"email": "locked@example.com", "password": "wrong-password"}
    assert [client.post("/api/auth/login/", json=bad).status_code for _ in range(5)] == [401] * 5
    good = {"email": "LOCKED@example.com", "password": "pw-123456"}
    assert client.post("/api/auth/login/", json=good).status_code == 429


def test_me_and_validation(client, tokens):
    host = client.get("/api/auth/me/", headers=auth(tokens["host"]["access"])).json()
    assert host["role"] == "HOST" and host["profile_id"]
    assert client.get("/api/auth/me/").status_code == 401
    assert client.post("/api/auth/register/renter/", json={"name": "x", "email": "a@example.com", "password": "short"}).status_code == 422
    assert client.post("/api/auth/register/renter/", json={"name": "x", "email": "renter@example.com", "password": "pw-123456"}).status_code == 400
    renter = auth(tokens["renter"]["access"])
    assert client.post("/api/wallets/add_funds/", headers=renter, json={"amount": -5}).status_code == 422
    assert client.post("/api/wallets/withdraw_funds/", headers=renter, json={"amount": 5}).status_code == 403
    r = client.get("/api/gpus/available/")
    assert r.headers["x-content-type-options"] == "nosniff"


def test_tunnel_routes_follow_sessions(client, cf):
    host = auth(register(client, "host", "h3@example.com")["access"])
    renter = auth(register(client, "renter", "r3@example.com")["access"])
    client.post("/api/wallets/add_funds/", headers=renter, json={"amount": 1000})
    assert client.post("/api/hosts/tunnel/", headers=renter).status_code == 403

    t = client.post("/api/hosts/tunnel/", headers=host).json()
    assert t["token"].startswith("token-for-")
    tunnel = t["token"].removeprefix("token-for-")
    assert client.post("/api/hosts/tunnel/", headers=host).json() == t  # one tunnel per host, reused

    a = client.post("/api/sessions/", headers=renter, json={"gpu": _gpu(client, host)}).json()["id"]
    b = client.post("/api/sessions/", headers=renter, json={"gpu": _gpu(client, host)}).json()["id"]
    assert client.get(f"/api/sessions/{a}/", headers=renter).json()["ssh_connection_string"] is None  # not started

    _start(client, host, a, 22001)
    _start(client, host, b, 22002)
    sa = client.get(f"/api/sessions/{a}/", headers=renter).json()
    assert sa["ssh_host"] == f"sess-{a.replace('-', '')[:12]}.labhya.test"
    assert "cloudflared access ssh" in sa["ssh_connection_string"] and "labuser@" + sa["ssh_host"] in sa["ssh_connection_string"]
    assert cf.routes[tunnel] == {sa["ssh_host"]: 22001, sa["ssh_host"].replace(a.replace('-', '')[:12], b.replace('-', '')[:12]): 22002}
    assert f"rec-{sa['ssh_host']}" in cf.dns

    client.post(f"/api/sessions/{a}/end_session/", headers=renter)
    assert sa["ssh_host"] not in cf.routes[tunnel] and len(cf.routes[tunnel]) == 1
    assert f"rec-{sa['ssh_host']}" not in cf.dns
    assert client.get(f"/api/sessions/{a}/", headers=renter).json()["ssh_connection_string"] is None
    client.post(f"/api/sessions/{b}/end_session/", headers=host)
    assert cf.routes[tunnel] == {}


def test_cloudflare_outage_doesnt_block_billing(client, cf, monkeypatch):
    import app.cloudflare as real
    host = auth(register(client, "host", "h4@example.com")["access"])
    renter = auth(register(client, "renter", "r4@example.com")["access"])
    client.post("/api/wallets/add_funds/", headers=renter, json={"amount": 1000})
    sid = client.post("/api/sessions/", headers=renter, json={"gpu": _gpu(client, host)}).json()["id"]
    _start(client, host, sid)

    def down(*a, **k):
        raise real.CloudflareError("down")
    monkeypatch.setattr(real, "set_routes", down)
    r = client.post(f"/api/sessions/{sid}/end_session/", headers=renter)
    assert r.status_code == 200 and r.json()["status"] == "COMPLETED"

    sid2 = client.post("/api/sessions/", headers=renter, json={"gpu": _gpu(client, host)}).json()["id"]
    assert _start(client, host, sid2).status_code == 502  # the agent retries
    assert client.get(f"/api/sessions/{sid2}/", headers=renter).json()["status"] == "PENDING"
