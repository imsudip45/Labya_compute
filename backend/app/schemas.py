"""Request and response bodies. frontend/lib/types.ts mirrors the response models."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Money = Annotated[Decimal, Field(gt=0, le=1_000_000, max_digits=12, decimal_places=2)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Auth ---

class RegisterPayload(Strict):
    name: Name
    email: EmailStr
    password: Annotated[str, Field(min_length=8, max_length=128)]

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode()) > 72:  # bcrypt ignores everything after 72 bytes
            raise ValueError("Password must be at most 72 bytes")
        return v


class LoginPayload(Strict):
    email: EmailStr
    password: Annotated[str, Field(max_length=128)]


class RefreshPayload(Strict):
    refresh: str


class TokenResponse(BaseModel):
    access: str
    refresh: str


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: Optional[Literal["HOST", "RENTER"]]
    profile_id: Optional[uuid.UUID]


# --- GPUs ---

class GPUCreate(Strict):
    gpu_name: Name
    gpu_model: Optional[Name] = None
    gpu_memory: Annotated[int, Field(ge=1, le=1024)]
    gpu_price: Annotated[int, Field(ge=1, le=100_000)]
    gpu_availability: bool = True
    gpu_location: Name


class GPUUpdate(Strict):
    gpu_name: Optional[Name] = None
    gpu_model: Optional[Name] = None
    gpu_memory: Optional[Annotated[int, Field(ge=1, le=1024)]] = None
    gpu_price: Optional[Annotated[int, Field(ge=1, le=100_000)]] = None
    gpu_availability: Optional[bool] = None
    gpu_location: Optional[Name] = None


class GPUResponse(BaseModel):
    id: uuid.UUID
    host_id: uuid.UUID
    host_name: str
    gpu_name: str
    gpu_model: Optional[str]
    gpu_memory: int
    gpu_price: int
    gpu_availability: bool
    is_rented: bool
    gpu_location: str
    created_at: datetime
    updated_at: datetime


# --- Sessions ---

class SessionCreate(Strict):
    # The web app sends {"gpu": "<id>"}; "gpu_id" is accepted too.
    gpu_id: uuid.UUID = Field(validation_alias=AliasChoices("gpu_id", "gpu"))


class SessionResponse(BaseModel):
    id: uuid.UUID
    gpu_id: uuid.UUID
    gpu_name: str
    renter_id: uuid.UUID
    renter_name: str
    host_id: uuid.UUID
    host_name: str
    hourly_price: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: str
    connection_status: str
    connection_error: Optional[str]
    ssh_host: Optional[str]
    ssh_username: Optional[str]
    ssh_password: Optional[str]
    ssh_connection_string: Optional[str]
    gpu_utilization: int
    memory_utilization: int
    temperature: int
    total_cost: Decimal
    payment_transaction_id: Optional[uuid.UUID]
    session_duration: float  # hours
    created_at: datetime
    updated_at: datetime


class SessionStarted(Strict):
    ssh_password: Annotated[str, Field(min_length=8, max_length=128)]
    host_port: Annotated[int, Field(ge=1024, le=65535)]  # the container's SSH port on the host's PC


class TunnelResponse(BaseModel):
    token: str


class ConnectionStatusUpdate(Strict):
    status: Literal["CONNECTING", "CONNECTED", "DISCONNECTED", "ERROR"]
    error_message: Optional[Annotated[str, Field(max_length=500)]] = None


class GPUMetricsUpdate(Strict):
    gpu_utilization: Annotated[int, Field(ge=0, le=100)]
    memory_utilization: Annotated[int, Field(ge=0, le=100)]
    temperature: Annotated[int, Field(ge=0, le=150)]


class EndSessionResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    total_cost: Decimal


# --- Wallets ---

class TransactionResponse(BaseModel):
    id: uuid.UUID
    wallet_id: uuid.UUID
    transaction_type: str
    amount: Decimal
    status: str
    description: Optional[str]
    created_at: datetime


class WalletResponse(BaseModel):
    id: uuid.UUID
    balance: Decimal
    currency: str
    owner_name: str
    transactions: list[TransactionResponse]


class WalletUpdatePayload(Strict):
    amount: Money
    description: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]] = None


class BalanceResponse(BaseModel):
    balance: Decimal


# --- Dashboard ---

class DashboardStatsResponse(BaseModel):
    totalGPUs: int = 0
    activeSessions: int = 0
    todaysEarnings: float = 0.0
    availableGPUs: int = 0
    totalSessions: int = 0
    totalSpent: float = 0.0

