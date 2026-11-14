// Mirrors backend/app/schemas.py. Decimal fields arrive as strings or numbers; use Number() when doing maths.

export type UserRole = "HOST" | "RENTER"

export interface Me {
  id: string
  email: string
  first_name: string
  last_name: string
  role: UserRole | null
  profile_id: string | null
}

export interface GPU {
  id: string
  host_id: string
  host_name: string
  gpu_name: string
  gpu_model: string | null
  gpu_memory: number
  gpu_price: number
  gpu_availability: boolean // the host lists it for rent
  is_rented: boolean // a session is starting or running on it
  gpu_location: string
  created_at: string
  updated_at: string
}

export type GPUInput = Pick<GPU, "gpu_name" | "gpu_model" | "gpu_memory" | "gpu_price" | "gpu_availability" | "gpu_location">

export type SessionStatus = "PENDING" | "ACTIVE" | "COMPLETED" | "CANCELLED"

export interface Session {
  id: string
  gpu_id: string
  gpu_name: string
  renter_id: string
  renter_name: string
  host_id: string
  host_name: string
  hourly_price: number
  start_time: string | null
  end_time: string | null
  status: SessionStatus
  connection_status: "CONNECTING" | "CONNECTED" | "DISCONNECTED" | "ERROR"
  connection_error: string | null
  ssh_host: string | null
  ssh_username: string | null
  ssh_password: string | null
  ssh_connection_string: string | null
  gpu_utilization: number
  memory_utilization: number
  temperature: number
  total_cost: number | string
  session_duration: number // hours
  created_at: string
  updated_at: string
}

export type TransactionType = "DEPOSIT" | "WITHDRAWAL" | "RENTAL_PAYMENT" | "RENTAL_EARNING"

export interface Transaction {
  id: string
  wallet_id: string
  transaction_type: TransactionType
  amount: number | string
  status: "COMPLETED"
  description: string | null
  created_at: string
}

export interface Wallet {
  id: string
  balance: number | string
  currency: string
  owner_name: string
  transactions: Transaction[]
}

export interface DashboardStats {
  totalGPUs: number
  availableGPUs: number
  activeSessions: number
  todaysEarnings: number
  totalSessions: number
  totalSpent: number
}

export interface TokenResponse {
  access: string
  refresh: string
}
