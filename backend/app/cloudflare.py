"""Cloudflare Tunnel: how renters reach containers on hosts' PCs.

Each host gets one tunnel, which its agent runs with `cloudflared`. When a session
starts, the API points `sess-<id>.<TUNNEL_DOMAIN>` at the container's SSH port on that
host; when it ends, the route and DNS record are removed. Hosts never see Cloudflare.
"""
import logging

import httpx

from app.config import settings

log = logging.getLogger(__name__)
API = "https://api.cloudflare.com/client/v4"


class CloudflareError(Exception):
    pass


def _call(method: str, path: str, **kwargs) -> dict | list | str | None:
    try:
        r = httpx.request(
            method, API + path, timeout=15,
            headers={"Authorization": f"Bearer {settings.cloudflare_api_token}"}, **kwargs,
        )
        body = r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise CloudflareError(f"{method} {path}: {e}") from e
    if not body.get("success"):
        raise CloudflareError(f"{method} {path}: {body.get('errors')}")
    return body.get("result")


def _acct(path: str) -> str:
    return f"/accounts/{settings.cloudflare_account_id}/cfd_tunnel{path}"


def create_tunnel(name: str) -> str:
    """Create a remotely configured tunnel and return its ID."""
    return _call("POST", _acct(""), json={"name": name, "config_src": "cloudflare"})["id"]


def tunnel_token(tunnel_id: str) -> str:
    """The token `cloudflared tunnel run` needs. Fetched on demand, never stored."""
    return _call("GET", _acct(f"/{tunnel_id}/token"))


def set_routes(tunnel_id: str, routes: dict[str, int]) -> None:
    """Replace the tunnel's routes with {hostname: local SSH port}. Anything else gets a 404."""
    ingress = [{"hostname": h, "service": f"ssh://localhost:{port}"} for h, port in sorted(routes.items())]
    ingress.append({"service": "http_status:404"})
    _call("PUT", _acct(f"/{tunnel_id}/configurations"), json={"config": {"ingress": ingress}})


def add_dns(hostname: str, tunnel_id: str) -> str:
    rec = _call("POST", f"/zones/{settings.cloudflare_zone_id}/dns_records", json={
        "type": "CNAME", "name": hostname, "content": f"{tunnel_id}.cfargotunnel.com", "proxied": True,
    })
    return rec["id"]


def remove_dns(record_id: str) -> None:
    _call("DELETE", f"/zones/{settings.cloudflare_zone_id}/dns_records/{record_id}")
