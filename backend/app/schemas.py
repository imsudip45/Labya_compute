import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str = ""

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: uuid.UUID
    username: str  # Maps to email

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access: str
    refresh: str
    message: Optional[str] = None
    renter_id: Optional[uuid.UUID] = None
    host_id: Optional[uuid.UUID] = None

class RenterResponse(BaseModel):
    id: uuid.UUID
    user: UserResponse
    wallet_balance: Decimal

class HostResponse(BaseModel):
    id: uuid.UUID
    user: UserResponse
    wallet_balance: Decimal

class WalletResponse(BaseModel):
    id: uuid.UUID
    balance: Decimal
    currency: str
    owner_name: str
    owner_type: str
    created_at: datetime
    updated_at: datetime

class TransactionResponse(BaseModel):
    id: uuid.UUID
    wallet_id: uuid.UUID
    transaction_type: str
    amount: Decimal
    status: str
    description: Optional[str] = None
    wallet_owner: str
    created_at: datetime
    updated_at: datetime

class GPUCreate(BaseModel):
    gpu_name: str
    gpu_model: Optional[str] = None
    gpu_memory: int
    gpu_price: int
    gpu_availability: bool = True
    gpu_location: str

class GPUResponse(BaseModel):
    id: uuid.UUID
    host_id: uuid.UUID
    host_name: str
    gpu_name: str
    gpu_model: Optional[str] = None
    gpu_memory: int
    gpu_price: int
    gpu_availability: bool
    gpu_location: str
    created_at: datetime
    updated_at: datetime

class SessionCreate(BaseModel):
    gpu_id: uuid.UUID

class SessionResponse(BaseModel):
    id: uuid.UUID
    gpu_id: uuid.UUID
    gpu_name: str
    renter_id: uuid.UUID
    renter_name: str
    host_id: uuid.UUID
    host_name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str
    connection_status: str
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = 22
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    connection_error: Optional[str] = None
    last_connected: Optional[datetime] = None
    gpu_utilization: int
    memory_utilization: int
    temperature: int
    is_auto_reconnect: bool
    payment_transaction_id: Optional[uuid.UUID] = None
    total_cost: Decimal
    ssh_connection_string: Optional[str] = None
    session_duration: float
    created_at: datetime
    updated_at: datetime

class SessionDetailResponse(BaseModel):
    id: uuid.UUID
    gpu: GPUResponse
    renter: RenterResponse
    host: HostResponse
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str
    connection_status: str
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = 22
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    connection_error: Optional[str] = None
    last_connected: Optional[datetime] = None
    gpu_utilization: int
    memory_utilization: int
    temperature: int
    is_auto_reconnect: bool
    payment_transaction: Optional[TransactionResponse] = None
    total_cost: Decimal
    ssh_connection_string: Optional[str] = None
    session_duration: float
    created_at: datetime
    updated_at: datetime

class WalletDetailResponse(BaseModel):
    id: uuid.UUID
    balance: Decimal
    currency: str
    owner_name: str
    transactions: List[TransactionResponse]
    created_at: datetime
    updated_at: datetime

class RegisterPayload(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginPayload(BaseModel):
    email: EmailStr
    password: str

class WalletUpdatePayload(BaseModel):
    amount: float
    description: Optional[str] = "Transaction"

class SessionStatusUpdate(BaseModel):
    connection_status: str
    ssh_password: Optional[str] = None

class ConnectionStatusUpdate(BaseModel):
    status: str
    error_message: Optional[str] = None

class GPUMetricsUpdate(BaseModel):
    gpu_utilization: int
    memory_utilization: int
    temperature: int

class DashboardStatsResponse(BaseModel):
    totalGPUs: Optional[int] = 0
    activeSessions: Optional[int] = 0
    todaysEarnings: Optional[float] = 0.0
    availableGPUs: Optional[int] = 0
    totalSessions: Optional[int] = 0
    totalSpent: Optional[float] = 0.0
