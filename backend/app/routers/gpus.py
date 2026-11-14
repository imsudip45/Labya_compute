import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth_utils import get_current_host
from app.db import get_session
from app.models import GPU, OPEN_STATUSES, Host, Session as RentalSession, User
from app.schemas import GPUCreate, GPUResponse, GPUUpdate

router = APIRouter(prefix="/api/gpus", tags=["GPUs"])


def _rented_ids(db: Session, gpu_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not gpu_ids:
        return set()
    rows = db.exec(select(RentalSession.gpu_id).where(RentalSession.gpu_id.in_(gpu_ids), RentalSession.status.in_(OPEN_STATUSES)))
    return set(rows.all())


def _out(db: Session, gpus: list[GPU]) -> list[GPUResponse]:
    rented = _rented_ids(db, [g.id for g in gpus])
    names = {
        h.id: u.display_name
        for h, u in db.exec(select(Host, User).join(User, User.id == Host.user_id).where(Host.id.in_({g.host_id for g in gpus}))).all()
    } if gpus else {}
    return [GPUResponse(**g.model_dump(), host_name=names[g.host_id], is_rented=g.id in rented) for g in gpus]


def _own_gpu(gpu_id: uuid.UUID, host: Host, db: Session) -> GPU:
    gpu = db.get(GPU, gpu_id)
    if not gpu or gpu.host_id != host.id:  # same answer for "missing" and "not yours"
        raise HTTPException(status.HTTP_404_NOT_FOUND, "GPU not found")
    return gpu


@router.get("/available/", response_model=list[GPUResponse])
def available_gpus(db: Session = Depends(get_session)):
    """Public: GPUs listed for rent and not rented right now."""
    listed = db.exec(select(GPU).where(GPU.gpu_availability == True).order_by(GPU.gpu_price)).all()  # noqa: E712
    return [g for g in _out(db, list(listed)) if not g.is_rented]


@router.get("/mine/", response_model=list[GPUResponse])
def my_gpus(host: Host = Depends(get_current_host), db: Session = Depends(get_session)):
    return _out(db, list(db.exec(select(GPU).where(GPU.host_id == host.id).order_by(GPU.created_at)).all()))


@router.post("/", response_model=GPUResponse, status_code=status.HTTP_201_CREATED)
def create_gpu(payload: GPUCreate, host: Host = Depends(get_current_host), db: Session = Depends(get_session)):
    gpu = GPU(host_id=host.id, **payload.model_dump())
    db.add(gpu)
    db.commit()
    db.refresh(gpu)
    return _out(db, [gpu])[0]


@router.patch("/{gpu_id}/", response_model=GPUResponse)
def update_gpu(gpu_id: uuid.UUID, payload: GPUUpdate, host: Host = Depends(get_current_host), db: Session = Depends(get_session)):
    gpu = _own_gpu(gpu_id, host, db)
    for key, val in payload.model_dump(exclude_unset=True).items():
        if val is None and key != "gpu_model":
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{key} can't be empty")
        setattr(gpu, key, val)
    db.add(gpu)
    db.commit()
    db.refresh(gpu)
    return _out(db, [gpu])[0]


@router.delete("/{gpu_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_gpu(gpu_id: uuid.UUID, host: Host = Depends(get_current_host), db: Session = Depends(get_session)):
    gpu = _own_gpu(gpu_id, host, db)
    # Sessions reference the GPU for billing history, so it can't be deleted once rented.
    if db.exec(select(RentalSession.id).where(RentalSession.gpu_id == gpu.id)).first():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'This GPU has session history, so it can\'t be removed. Turn off "Available to rent" instead.',
        )
    db.delete(gpu)
    db.commit()
