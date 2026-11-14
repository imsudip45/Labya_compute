import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session as DB, select

from app.auth_utils import get_current_host, get_current_renter, get_current_user
from app import cloudflare
from app.billing import close_session, end_overdue_sessions, host_routes, wallet_of
from app.config import settings
from app.db import get_session
from app.models import GPU, OPEN_STATUSES, Host, Renter, Session, User, utcnow
from app.schemas import (
    ConnectionStatusUpdate, EndSessionResponse, GPUMetricsUpdate, SessionCreate, SessionResponse, SessionStarted,
)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])
log = logging.getLogger(__name__)


def _out(db: DB, sessions: list[Session]) -> list[SessionResponse]:
    gpus = {g.id: g for g in db.exec(select(GPU).where(GPU.id.in_({s.gpu_id for s in sessions}))).all()} if sessions else {}
    renters = dict(db.exec(select(Renter.id, User).join(User, User.id == Renter.user_id).where(Renter.id.in_({s.renter_id for s in sessions}))).all()) if sessions else {}
    hosts = dict(db.exec(select(Host.id, User).join(User, User.id == Host.user_id).where(Host.id.in_({s.host_id for s in sessions}))).all()) if sessions else {}
    return [
        SessionResponse(
            **s.model_dump(exclude={"total_cost"}),
            gpu_name=gpus[s.gpu_id].gpu_name,
            renter_name=renters[s.renter_id].display_name,
            host_name=hosts[s.host_id].display_name,
            total_cost=s.cost_so_far(),
            ssh_connection_string=s.ssh_connection_string,
            session_duration=round(s.hours, 2),
        )
        for s in sessions
    ]


def _for_participant(session_id: uuid.UUID, user: User, db: DB) -> Session:
    s = db.get(Session, session_id)
    if s:
        renter = db.get(Renter, s.renter_id)
        host = db.get(Host, s.host_id)
        if user.id in (renter.user_id, host.user_id):
            return s
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")


def _for_host(session_id: uuid.UUID, host: Host, db: DB, lock: bool = False) -> Session:
    q = select(Session).where(Session.id == session_id, Session.host_id == host.id)
    s = db.exec(q.with_for_update() if lock else q).first()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return s


@router.get("/", response_model=list[SessionResponse])
def my_sessions(user: User = Depends(get_current_user), db: DB = Depends(get_session)):
    renter = db.exec(select(Renter).where(Renter.user_id == user.id)).first()
    host = None if renter else db.exec(select(Host).where(Host.user_id == user.id)).first()
    if not renter and not host:
        return []
    col = Session.renter_id if renter else Session.host_id
    rows = db.exec(select(Session).where(col == (renter or host).id).order_by(Session.created_at.desc()).limit(200)).all()
    return _out(db, list(rows))


@router.get("/pending_for_host/", response_model=list[SessionResponse])
def pending_for_host(host: Host = Depends(get_current_host), db: DB = Depends(get_session)):
    """Polled by the host agent. Also ends running sessions the renter can no longer pay for."""
    end_overdue_sessions(db, host.id)
    db.commit()
    rows = db.exec(select(Session).where(Session.host_id == host.id, Session.status == "PENDING").order_by(Session.created_at)).all()
    return _out(db, list(rows))


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, renter: Renter = Depends(get_current_renter), db: DB = Depends(get_session)):
    gpu = db.exec(select(GPU).where(GPU.id == payload.gpu_id).with_for_update()).first()
    if not gpu or not gpu.gpu_availability:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This GPU isn't available to rent.")
    if db.exec(select(Session.id).where(Session.gpu_id == gpu.id, Session.status.in_(OPEN_STATUSES))).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Someone else is renting this GPU right now.")
    if not settings.tunnels_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Renting is turned off on this server for now.")
    if wallet_of(db, renter_id=renter.id).balance < gpu.gpu_price:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your balance is too low to rent this GPU for one hour.")

    s = Session(gpu_id=gpu.id, renter_id=renter.id, host_id=gpu.host_id, hourly_price=gpu.gpu_price, ssh_username="labuser")
    db.add(s)
    db.commit()
    db.refresh(s)
    return _out(db, [s])[0]


@router.get("/{session_id}/", response_model=SessionResponse)
def get_session_detail(session_id: uuid.UUID, user: User = Depends(get_current_user), db: DB = Depends(get_session)):
    return _out(db, [_for_participant(session_id, user, db)])[0]


@router.post("/{session_id}/mark_started/")
def mark_started(session_id: uuid.UUID, payload: SessionStarted, host: Host = Depends(get_current_host), db: DB = Depends(get_session)):
    """The agent's container is up: route a hostname to it and start billing."""
    s = _for_host(session_id, host, db, lock=True)
    if s.status != "PENDING":
        raise HTTPException(status.HTTP_409_CONFLICT, "This session isn't waiting to start.")
    if not host.tunnel_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Start the agent's tunnel before starting sessions.")
    hostname = f"sess-{s.id.hex[:12]}.{settings.tunnel_domain}"
    try:
        cloudflare.set_routes(host.tunnel_id, {**host_routes(db, host.id), hostname: payload.host_port})
        s.dns_record_id = cloudflare.add_dns(hostname, host.tunnel_id)
    except cloudflare.CloudflareError:
        log.exception("Couldn't route session %s", s.id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Couldn't connect this session. The agent will try again.")
    now = utcnow()
    s.start_time = now
    s.status, s.ssh_password, s.ssh_host, s.host_port = "ACTIVE", payload.ssh_password, hostname, payload.host_port
    s.connection_status, s.connection_error, s.last_connected = "CONNECTED", None, now
    db.add(s)
    db.commit()
    return {"session_id": s.id, "status": s.status}


@router.post("/{session_id}/update_connection_status/")
def update_connection_status(session_id: uuid.UUID, payload: ConnectionStatusUpdate, host: Host = Depends(get_current_host), db: DB = Depends(get_session)):
    s = _for_host(session_id, host, db)
    s.connection_status = payload.status
    s.connection_error = payload.error_message
    if payload.status == "CONNECTED":
        s.last_connected = utcnow()
    db.add(s)
    db.commit()
    return {"connection_status": s.connection_status}


@router.post("/{session_id}/update_gpu_metrics/")
def update_gpu_metrics(session_id: uuid.UUID, payload: GPUMetricsUpdate, host: Host = Depends(get_current_host), db: DB = Depends(get_session)):
    s = _for_host(session_id, host, db)
    if s.status != "ACTIVE":
        raise HTTPException(status.HTTP_409_CONFLICT, "This session isn't running.")
    for k, v in payload.model_dump().items():
        setattr(s, k, v)
    db.add(s)
    db.commit()
    return {"ok": True}


@router.post("/{session_id}/end_session/", response_model=EndSessionResponse)
def end_session(session_id: uuid.UUID, user: User = Depends(get_current_user), db: DB = Depends(get_session)):
    s = _for_participant(session_id, user, db)
    db.refresh(s, with_for_update=True)  # one end per session even if both sides click at once
    if s.status not in OPEN_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, "This session has already ended.")
    cost = close_session(db, s, db.get(GPU, s.gpu_id).gpu_name)
    db.commit()
    return EndSessionResponse(session_id=s.id, status=s.status, total_cost=cost)
