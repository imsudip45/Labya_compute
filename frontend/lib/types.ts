// Updated to match backend API response types

export interface User {
  id: string
  username: string
  email: string
  first_name: string
  last_name: string
}

export interface Host {
  id: string
  user: User
  wallet_balance: number
}

export interface Renter {
  id: string
  user: User
  wallet_balance: number
}

export interface GPU {
  id: string
  host: Host
  host_name: string
  gpu_name: string
  gpu_model: string
  gpu_memory: number
  gpu_price: number
  gpu_location: string
  gpu_availability: boolean
  created_at: string
  updated_at: string
}

export interface Session {
  id: string
  gpu: GPU
  gpu_name: string
  renter: Renter
  renter_name: string
  host: Host
  host_name: string
  start_time: string
  end_time?: string
  status: "ACTIVE" | "COMPLETED" | "CANCELLED"
  total_cost: number
  ssh_connection_string?: string
  session_duration?: string
  ssh_host?: string
  ssh_port?: number
  ssh_username?: string
  gpu_utilization?: number
  memory_utilization?: number
  temperature?: number
  created_at: string
  updated_at: string
}

export interface Wallet {
  id: string
  balance: number
  currency: string
  owner_name: string
  owner_type: string
  created_at: string
  updated_at: string
}

export interface Transaction {
  id: string
  wallet: Wallet
  amount: number
  transaction_type: "DEPOSIT" | "WITHDRAWAL" | "PAYMENT"
  status: "PENDING" | "COMPLETED" | "FAILED"
  description?: string
  wallet_owner: string
  created_at: string
  updated_at: string
}

export interface DashboardStats {
  totalGPUs: number
  activeSessions: number
  todaysEarnings: number
  totalSessions: number
  totalSpent: number
}

export type UserRole = "HOST" | "RENTER"

// API Response types
export interface LoginResponse {
  access: string
  refresh: string
}

export interface RegisterResponse {
  message: string
  renter_id?: string
  host_id?: string
  access: string
  refresh: string
}

export interface ApiError {
  error: string
  detail?: string
}
