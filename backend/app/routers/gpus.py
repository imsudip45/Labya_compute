from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.db import get_session
from app.models import GPU, Host, User
from app.schemas import GPUCreate, GPUResponse
from app.auth_utils import get_current_user, get_current_host

router = APIRouter(prefix="/api/gpus", tags=["GPUs"])

def make_gpu_response(gpu: GPU, db: Session) -> GPUResponse:
    stmt = select(Host).where(Host.id == gpu.host_id)
    host = db.exec(stmt).first()
    stmt_user = select(User).where(User.id == host.user_id)
    user = db.exec(stmt_user).first()
    host_name = user.first_name + " " + user.last_name if user.last_name else user.first_name
    if not host_name.strip():
        host_name = user.email
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

@router.get("/available/", response_model=List[GPUResponse])
def get_available_gpus(db: Session = Depends(get_session)):
    stmt = select(GPU).where(GPU.gpu_availability == True)
    gpus = db.exec(stmt).all()
    return [make_gpu_response(gpu, db) for gpu in gpus]

@router.get("/", response_model=List[GPUResponse])
def get_all_gpus(db: Session = Depends(get_session)):
    stmt = select(GPU)
    gpus = db.exec(stmt).all()
    return [make_gpu_response(gpu, db) for gpu in gpus]

@router.post("/", response_model=GPUResponse, status_code=status.HTTP_201_CREATED)
def create_gpu(payload: GPUCreate, host: Host = Depends(get_current_host), db: Session = Depends(get_session)):
    gpu = GPU(
        host_id=host.id,
        gpu_name=payload.gpu_name,
        gpu_model=payload.gpu_model,
        gpu_memory=payload.gpu_memory,
        gpu_price=payload.gpu_price,
        gpu_availability=payload.gpu_availability,
        gpu_location=payload.gpu_location
    )
    db.add(gpu)
    db.commit()
    db.refresh(gpu)
    return make_gpu_response(gpu, db)

@router.get("/{gpu_id}/", response_model=GPUResponse)
def get_gpu(gpu_id: uuid.UUID, db: Session = Depends(get_session)):
    gpu = db.get(GPU, gpu_id)
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")
    return make_gpu_response(gpu, db)

@router.patch("/{gpu_id}/", response_model=GPUResponse)
def update_gpu(gpu_id: uuid.UUID, payload: GPUCreate, host: Host = Depends(get_current_host), db: Session = Depends(get_session)):
    gpu = db.get(GPU, gpu_id)
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")
    if gpu.host_id != host.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this GPU")
        
    for key, val in payload.dict(exclude_unset=True).items():
        setattr(gpu, key, val)
    db.add(gpu)
    db.commit()
    db.refresh(gpu)
    return make_gpu_response(gpu, db)

@router.delete("/{gpu_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_gpu(gpu_id: uuid.UUID, host: Host = Depends(get_current_host), db: Session = Depends(get_session)):
    gpu = db.get(GPU, gpu_id)
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")
    if gpu.host_id != host.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this GPU")
    db.delete(gpu)
    db.commit()
