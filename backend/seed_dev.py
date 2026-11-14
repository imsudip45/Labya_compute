"""Fill a local dev API with a test host (two GPUs) and a test renter (with funds).

Run against a local API only:  python seed_dev.py [http://localhost:8000]
Accounts (local testing only):
  host:   host@example.com   / devpass123
  renter: renter@example.com / devpass123
"""
import json
import sys
import urllib.error
import urllib.request

API = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/") + "/api"
PASSWORD = "devpass123"


def call(method, path, body=None, token=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "labhya-seed/1.0")  # FastAPI Cloud rejects urllib's default agent
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read() or "null")
    except urllib.error.HTTPError as e:
        if e.code == 400 and b"already exists" in e.read():
            return None
        raise


def account(role, name, email):
    call("POST", f"/auth/register/{role}/", {"name": name, "email": email, "password": PASSWORD})
    return call("POST", "/auth/login/", {"email": email, "password": PASSWORD})["access"]


host = account("host", "Test Host", "host@example.com")
mine = call("GET", "/gpus/mine/", token=host)
if not mine:
    for gpu in [
        {"gpu_name": "RTX 4090", "gpu_model": "NVIDIA GeForce RTX 4090", "gpu_memory": 24, "gpu_price": 350, "gpu_location": "Kathmandu"},
        {"gpu_name": "RTX 3060", "gpu_model": "NVIDIA GeForce RTX 3060", "gpu_memory": 12, "gpu_price": 120, "gpu_location": "Pokhara"},
    ]:
        call("POST", "/gpus/", gpu, host)

renter = account("renter", "Test Renter", "renter@example.com")
call("POST", "/wallets/add_funds/", {"amount": 2000, "description": "Deposit"}, renter)
print("Seeded. Log in as host@example.com or renter@example.com (password in this file).")
