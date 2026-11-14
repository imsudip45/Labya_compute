import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app import cloudflare
from app.auth_utils import get_current_host
from app.config import settings
from app.db import get_session
from app.models import Host
from app.schemas import TunnelResponse

router = APIRouter(prefix="/api/hosts", tags=["Hosts"])
log = logging.getLogger(__name__)


@router.post("/tunnel/", response_model=TunnelResponse)
def my_tunnel(host: Host = Depends(get_current_host), db: Session = Depends(get_session)):
    """The token the agent passes to `cloudflared tunnel run`. Creates the tunnel on first use."""
    if not settings.tunnels_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Hosting is turned off on this server for now.")
    try:
        if not host.tunnel_id:
            host.tunnel_id = cloudflare.create_tunnel(f"labhya-host-{host.id}")
            db.add(host)
            db.commit()
        return TunnelResponse(token=cloudflare.tunnel_token(host.tunnel_id))
    except cloudflare.CloudflareError:
        log.exception("Couldn't set up the tunnel for host %s", host.id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Couldn't set up your connection. Try again in a minute.")
