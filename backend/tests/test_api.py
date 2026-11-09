from tests.conftest import auth


def test_rental_flow_and_access_control(client, tokens):
    host, renter, other = (auth(tokens[k]["access"]) for k in ("host", "renter", "other"))

    r = client.post("/api/gpus/", headers=host, json={"gpu_name": "RTX 3060", "gpu_memory": 12, "gpu_price": 100, "gpu_location": "Kathmandu"})
    assert r.status_code == 201, r.text
    gpu_id = r.json()["id"]
    assert any(g["id"] == gpu_id for g in client.get("/api/gpus/available/").json())

    assert client.post("/api/wallets/add_funds/", headers=renter, json={"amount": 1000}).status_code == 200

    # The web app sends {"gpu": id}
    r = client.post("/api/sessions/", headers=renter, json={"gpu": gpu_id})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]

    # Only the session's renter or host can read it (it contains SSH details)
    assert client.get(f"/api/sessions/{sid}/").status_code == 401
    assert client.get(f"/api/sessions/{sid}/", headers=other).status_code == 403
    assert client.get(f"/api/sessions/{sid}/", headers=renter).status_code == 200

    # Only the host running the session can report its state
    started = {"connection_status": "CONNECTED", "ssh_password": "pw"}
    assert client.post(f"/api/sessions/{sid}/mark_started/", json=started).status_code == 401
    assert client.post(f"/api/sessions/{sid}/mark_started/", headers=renter, json=started).status_code == 403
    assert client.post(f"/api/sessions/{sid}/mark_started/", headers=host, json=started).status_code == 200
    metrics = {"gpu_utilization": 50, "memory_utilization": 40, "temperature": 60}
    assert client.post(f"/api/sessions/{sid}/update_gpu_metrics/", headers=host, json=metrics).status_code == 200

    # Only a participant can end (and so trigger payment for) a session
    assert client.post(f"/api/sessions/{sid}/end_session/").status_code == 401
    assert client.post(f"/api/sessions/{sid}/end_session/", headers=other).status_code == 403
    assert client.post(f"/api/sessions/{sid}/end_session/", headers=renter).status_code == 200

    assert client.get("/api/wallets/", headers=renter).json()["owner_name"].startswith("Renter")


def test_refresh_tokens_are_not_access_tokens(client, tokens):
    renter = tokens["renter"]
    r = client.post("/api/auth/refresh/", json={"refresh": renter["refresh"]})
    assert r.status_code == 200 and r.json()["access"]
    assert client.post("/api/auth/refresh/", json={"refresh": renter["access"]}).status_code == 401
    assert client.get("/api/wallets/", headers=auth(renter["refresh"])).status_code == 401
