import type { 
  User, 
  GPU, 
  Session, 
  Wallet, 
  Transaction, 
  DashboardStats,
  LoginResponse,
  RegisterResponse,
  UserRole,
  ApiError 
} from './types'
import { useAuthStore } from './auth-store'

const API_BASE_URL = 'http://localhost:8000/api'

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

class ApiService {
  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    // Add auth token if available
    const token = useAuthStore.getState().accessToken
    
    if (token) {
      config.headers = {
        ...config.headers,
        'Authorization': `Bearer ${token}`,
      }
    }

    const doFetch = async (): Promise<Response> => {
      return fetch(url, config)
    }

    try {
      let response = await doFetch()
      if (response.ok) {
        return await response.json()
      }

      // Attempt token refresh on auth errors
      const errorData = await response.json().catch(() => ({})) as any
      const message = errorData.error || errorData.detail || `HTTP ${response.status}`
      const isAuthError = response.status === 401 || response.status === 403 || /token not valid/i.test(String(message))
      if (isAuthError) {
        try {
          // Try refresh and retry once
          await useAuthStore.getState().refreshAccessToken()
          // Rebuild headers with new token
          const refreshedToken = useAuthStore.getState().accessToken
          if (refreshedToken) {
            config.headers = {
              ...(config.headers || {}),
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${refreshedToken}`,
            }
          }
          response = await doFetch()
          if (response.ok) {
            return await response.json()
          }
        } catch {
          // fallthrough to logout
        }
        // If still failing, logout and throw
        useAuthStore.getState().logout()
      }

      throw new ApiError(response.status, message)
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError(0, error instanceof Error ? error.message : 'Network error')
    }
  }

  // Authentication
  async login(email: string, password: string): Promise<LoginResponse> {
    return this.request<LoginResponse>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  }

  async register(name: string, email: string, password: string, role: UserRole): Promise<RegisterResponse> {
    const endpoint = role === 'HOST' ? '/auth/register/host/' : '/auth/register/renter/'
    return this.request<RegisterResponse>(endpoint, {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    })
  }

  async refreshToken(refresh: string): Promise<{ access: string }> {
    return this.request<{ access: string }>('/auth/refresh/', {
      method: 'POST',
      body: JSON.stringify({ refresh }),
    })
  }

  // GPUs
  async getGPUs(): Promise<GPU[]> {
    const response = await this.request<{ results: GPU[] }>('/gpus/')
    return response.results || response
  }

  async getHostGPUs(hostId: string): Promise<GPU[]> {
    const response = await this.request<{ results: GPU[] }>(`/hosts/${hostId}/gpus/`)
    return (response as any).results || (response as any)
  }

  async getAvailableGPUs(): Promise<GPU[]> {
    const response = await this.request<{ results: GPU[] }>('/gpus/available/')
    return response.results || response
  }

  async createGPU(gpuData: Partial<GPU>): Promise<GPU> {
    return this.request<GPU>('/gpus/', {
      method: 'POST',
      body: JSON.stringify(gpuData),
    })
  }

  async updateGPU(id: string, gpuData: Partial<GPU>): Promise<GPU> {
    return this.request<GPU>(`/gpus/${id}/`, {
      method: 'PUT',
      body: JSON.stringify(gpuData),
    })
  }

  async deleteGPU(id: string): Promise<void> {
    return this.request<void>(`/gpus/${id}/`, {
      method: 'DELETE',
    })
  }

  // Sessions
  async getSessions(): Promise<Session[]> {
    const response = await this.request<{ results: Session[] }>('/sessions/')
    return response.results || response
  }

  async createSession(sessionData: { gpu: string }): Promise<Session> {
    return this.request<Session>('/sessions/', {
      method: 'POST',
      body: JSON.stringify(sessionData),
    })
  }

  async markSessionStarted(id: string, ssh_password?: string): Promise<{ message: string; session_id: string }> {
    return this.request<{ message: string; session_id: string }>(`/sessions/${id}/mark_started/`, {
      method: 'POST',
      body: JSON.stringify({ ssh_password }),
    })
  }

  async endSession(id: string): Promise<Session> {
    return this.request<Session>(`/sessions/${id}/end_session/`, {
      method: 'POST',
    })
  }

  async cancelSession(id: string): Promise<Session> {
    return this.request<Session>(`/sessions/${id}/cancel_session/`, {
      method: 'POST',
    })
  }

  async updateGPUMetrics(id: string, metrics: {
    gpu_utilization: number
    memory_utilization: number
    temperature: number
  }): Promise<Session> {
    return this.request<Session>(`/sessions/${id}/update_gpu_metrics/`, {
      method: 'POST',
      body: JSON.stringify(metrics),
    })
  }

  async getSessionConnectionInfo(id: string): Promise<{
    ssh_connection_string: string | null
    ssh_host: string | null
    ssh_port: number | null
    ssh_username: string | null
    connection_status: string
    is_connected: boolean
  }> {
    return this.request(`/sessions/${id}/connection_info/`)
  }

  // Wallet
  async getWallet(): Promise<Wallet> {
    return this.request<Wallet>('/wallets/')
  }

  async addFunds(amount: number, description?: string): Promise<{ message: string; new_balance: number; amount_added: number }> {
    return this.request<{ message: string; new_balance: number; amount_added: number }>('/wallets/add_funds/', {
      method: 'POST',
      body: JSON.stringify({ amount, description }),
    })
  }

  async withdrawFunds(amount: number, description?: string): Promise<{ message: string; new_balance: number; amount_withdrawn: number }> {
    return this.request<{ message: string; new_balance: number; amount_withdrawn: number }>('/wallets/withdraw_funds/', {
      method: 'POST',
      body: JSON.stringify({ amount, description }),
    })
  }

  // Transactions
  async getTransactions(): Promise<Transaction[]> {
    const response = await this.request<{ results: Transaction[] }>('/transactions/')
    return response.results || response
  }

  // Dashboard
  async getDashboardStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>('/dashboard/stats/')
  }

  // User Profile
  async getHostProfile(): Promise<{ id: string; user: User; wallet_balance: number }> {
    const response = await this.request<{ id: string; user: User; wallet: { balance: string } }>('/hosts/')
    return {
      id: response.id,
      user: response.user,
      wallet_balance: parseFloat(response.wallet.balance)
    }
  }

  async getRenterProfile(): Promise<{ id: string; user: User; wallet_balance: number }> {
    const response = await this.request<{ id: string; user: User; wallet: { balance: string } }>('/renters/')
    return {
      id: response.id,
      user: response.user,
      wallet_balance: parseFloat(response.wallet.balance)
    }
  }
}

export const api = new ApiService()
export { ApiError }
