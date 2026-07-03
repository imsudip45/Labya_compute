from datetime import datetime
from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session as Session_DB, select
from app.db import get_session
from app.models import Session, GPU, Renter, Host, User, RelayPort, Transaction, Wallet
from app.schemas import (
    SessionResponse, SessionDetailResponse, SessionCreate, SessionStatusUpdate,
    ConnectionStatusUpdate, GPUMetricsUpdate, GPUResponse, RenterResponse, HostResponse, TransactionResponse, UserResponse
)
from app.auth_utils import get_current_user, get_current_renter, get_current_host
from app.config import settings

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

def make_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.email,
        first_name=user.first_name,
        last_name=user.last_name
    )

def make_renter_response(renter: Renter, db: Session_DB) -> RenterResponse:
    user = db.get(User, renter.user_id)
    wallet = renter.get_wallet(db)
    return RenterResponse(
        id=renter.id,
        user=make_user_response(user),
        wallet_balance=wallet.balance
    )

def make_host_response(host: Host, db: Session_DB) -> HostResponse:
    user = db.get(User, host.user_id)
    wallet = host.get_wallet(db)
    return HostResponse(
        id=host.id,
        user=make_user_response(user),
        wallet_balance=wallet.balance
    )

def make_gpu_response(gpu: GPU, db: Session_DB) -> GPUResponse:
    host = db.get(Host, gpu.host_id)
    user = db.get(User, host.user_id)
    host_name = f"{user.first_name} {user.last_name}".strip() or user.email
    return GPUResponse(
        id=gpu.id,
        host_id=gpu.host_id,
        host_name=host_name,
        gpu_name=gpu.gpu_name,
        gpu_model=gpu.gpu_model,
        gpu_memory=gpu.gpu_memory,
        gpu_price=gpu.gpu_price,
        gpu_availability=gpu.gpu_availability,
        gpu_location=gpu.gpu_location,
        created_at=gpu.created_at,
        updated_at=gpu.updated_at
    )

def make_transaction_response(tx: Transaction, db: Session_DB) -> TransactionResponse:
    wallet = db.get(Wallet, tx.wallet_id)
    owner_name = wallet.get_owner_name() if wallet else "Unknown"
    return TransactionResponse(
        id=tx.id,
        wallet_id=tx.wallet_id,
        transaction_type=tx.transaction_type,
        amount=tx.amount,
        status=tx.status,
        description=tx.description,
        wallet_owner=owner_name,
        created_at=tx.created_at,
        updated_at=tx.updated_at
    )

def make_session_detail_response(session: Session, db: Session_DB) -> SessionDetailResponse:
    gpu = db.get(GPU, session.gpu_id)
    renter = db.get(Renter, session.renter_id)
    host = db.get(Host, session.host_id)
    tx = db.get(Transaction, session.payment_transaction_id) if session.payment_transaction_id else None
    
    duration = 0.0
    if session.start_time:
        end = session.end_time or datetime.utcnow()
        duration = (end - session.start_time).total_seconds() / 3600
        
    return SessionDetailResponse(
        id=session.id,
        gpu=make_gpu_response(gpu, db),
        renter=make_renter_response(renter, db),
        host=make_host_response(host, db),
        start_time=session.start_time,
        end_time=session.end_time,
        status=session.status,
        connection_status=session.connection_status,
        ssh_host=session.ssh_host,
        ssh_port=session.ssh_port,
        ssh_username=session.ssh_username,
        ssh_password=session.ssh_password,
        connection_error=session.connection_error,
        last_connected=session.last_connected,
        gpu_utilization=session.gpu_utilization,
        memory_utilization=session.memory_utilization,
        temperature=session.temperature,
        is_auto_reconnect=session.is_auto_reconnect,
        payment_transaction=make_transaction_response(tx, db) if tx else None,
        total_cost=session.total_cost,
        ssh_connection_string=session.get_ssh_connection_string(),
        session_duration=round(duration, 2),
        created_at=session.created_at,
        updated_at=session.updated_at
    )

def make_session_response(session: Session, db: Session_DB) -> SessionResponse:
    gpu = db.get(GPU, session.gpu_id)
    renter = db.get(Renter, session.renter_id)
    host = db.get(Host, session.host_id)
    renter_user = db.get(User, renter.user_id)
    host_user = db.get(User, host.user_id)
    
    duration = 0.0
    if session.start_time:
        end = session.end_time or datetime.utcnow()
        duration = (end - session.start_time).total_seconds() / 3600
        
    return SessionResponse(
        id=session.id,
        gpu_id=session.gpu_id,
        gpu_name=gpu.gpu_name,
        renter_id=session.renter_id,
        renter_name=f"{renter_user.first_name} {renter_user.last_name}".strip() or renter_user.email,
        host_id=session.host_id,
        host_name=f"{host_user.first_name} {host_user.last_name}".strip() or host_user.email,
        start_time=session.start_time,
        end_time=session.end_time,
        status=session.status,
        connection_status=session.connection_status,
        ssh_host=session.ssh_host,
        ssh_port=session.ssh_port,
        ssh_username=session.ssh_username,
        ssh_password=session.ssh_password,
        connection_error=session.connection_error,
        last_connected=session.last_connected,
        gpu_utilization=session.gpu_utilization,
        memory_utilization=session.memory_utilization,
        temperature=session.temperature,
        is_auto_reconnect=session.is_auto_reconnect,
        payment_transaction_id=session.payment_transaction_id,
        total_cost=session.total_cost,
        ssh_connection_string=session.get_ssh_connection_string(),
        session_duration=round(duration, 2),
        created_at=session.created_at,
        updated_at=session.updated_at
    )

@router.get("/", response_model=List[SessionResponse])
def get_user_sessions(user: User = Depends(get_current_user), db: Session_DB = Depends(get_session)):
    stmt_renter = select(Renter).where(Renter.user_id == user.id)
    renter = db.exec(stmt_renter).first()
    if renter:
        stmt = select(Session).where(Session.renter_id == renter.id).order_by(Session.created_at.desc())
        sessions = db.exec(stmt).all()
        return [make_session_response(s, db) for s in sessions]
        
    stmt_host = select(Host).where(Host.user_id == user.id)
    host = db.exec(stmt_host).first()
    if host:
        stmt = select(Session).where(Session.host_id == host.id).order_by(Session.created_at.desc())
        sessions = db.exec(stmt).all()
        return [make_session_response(s, db) for s in sessions]
        
    return []

@router.get("/pending_for_host/", response_model=List[SessionResponse])
def get_pending_sessions_for_host(host: Host = Depends(get_current_host), db: Session_DB = Depends(get_session)):
    stmt = select(Session).where(Session.host_id == host.id, Session.status == "PENDING").order_by(Session.created_at)
    sessions = db.exec(stmt).all()
    return [make_session_response(s, db) for s in sessions]

@router.post("/", response_model=SessionDetailResponse, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, renter: Renter = Depends(get_current_renter), db: Session_DB = Depends(get_session)):
    gpu = db.get(GPU, payload.gpu_id)
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")
    if not gpu.gpu_availability:
        raise HTTPException(status_code=400, detail="GPU is not available for rent")
        
    wallet = renter.get_wallet(db)
    if wallet.balance < gpu.gpu_price:
        raise HTTPException(status_code=400, detail="Insufficient balance to rent this GPU")
        
    try:
        session = Session(
            gpu_id=gpu.id,
            renter_id=renter.id,
            host_id=gpu.host_id,
            status="PENDING"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        leased = RelayPort.lease_free_port(db, session, settings.relay_port_range_start, settings.relay_port_range_end)
        
        session.ssh_host = settings.relay_host
        session.ssh_port = leased.port
        session.ssh_username = f"sess_{str(session.id)[:8]}"
        
        gpu.gpu_availability = False
        db.add(gpu)
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return make_session_detail_response(session, db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{session_id}/", response_model=SessionDetailResponse)
def get_session_detail(session_id: uuid.UUID, db: Session_DB = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return make_session_detail_response(session, db)

@router.post("/{session_id}/mark_started/")
def mark_session_started(session_id: uuid.UUID, payload: SessionStatusUpdate, db: Session_DB = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in ["PENDING", "ACTIVE"]:
        raise HTTPException(status_code=400, detail="Invalid session state")
        
    if not session.start_time:
        session.start_time = datetime.utcnow()
    session.status = "ACTIVE"
    if payload.ssh_password:
        session.ssh_password = payload.ssh_password
    session.connection_status = "CONNECTED"
    session.last_connected = datetime.utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return {"message": "Session marked as started", "session_id": str(session.id)}

@router.post("/{session_id}/update_connection_status/")
def update_connection_status(session_id: uuid.UUID, payload: ConnectionStatusUpdate, db: Session_DB = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session.update_connection_status(payload.status, payload.error_message)
    db.add(session)
    db.commit()
    return {"message": "Connection status updated", "connection_status": session.connection_status}

@router.post("/{session_id}/update_gpu_metrics/")
def update_gpu_metrics(session_id: uuid.UUID, payload: GPUMetricsUpdate, db: Session_DB = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session.update_gpu_metrics(payload.gpu_utilization, payload.memory_utilization, payload.temperature)
    db.add(session)
    db.commit()
    return {"message": "GPU metrics updated"}

@router.post("/{session_id}/end_session/")
def end_session(session_id: uuid.UUID, db: Session_DB = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Session is already completed")
        
    try:
        session.end_time = datetime.utcnow()
        session.status = "COMPLETED"
        db.add(session)
        db.commit()
        db.refresh(session)
        
        total_cost = session.process_payment(db)
        
        gpu = db.get(GPU, session.gpu_id)
        gpu.gpu_availability = True
        db.add(gpu)
        
        stmt_port = select(RelayPort).where(RelayPort.leased_to_session_id == session.id)
        relay_port = db.exec(stmt_port).first()
        if relay_port:
            relay_port.release(db)
            
        db.commit()
        return {
            "message": "Session ended successfully",
            "total_cost": float(total_cost),
            "session_id": str(session.id)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
