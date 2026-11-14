import type { DashboardStats, GPU, GPUInput, Me, Session, SessionStatus, TokenResponse, UserRole, Wallet } from "./types"
import { useAuthStore } from "./auth-store"

// Same origin in production (the API serves this site); see .env.development for local dev.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api"

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = "ApiError"
  }
}

// FastAPI returns {detail: "..."} or, for validation errors, {detail: [{msg}]}.
function errorMessage(body: any, status: number): string {
  const d = body?.detail
  if (typeof d === "string") return d
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg
  return `Request failed (${status})`
}

async function request<T>(endpoint: string, options: RequestInit = {}, retried = false): Promise<T> {
  const token = useAuthStore.getState().accessToken
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    })
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.")
  }

  if (response.status === 401 && token && !retried) {
    try {
      await useAuthStore.getState().refreshAccessToken()
      return request<T>(endpoint, options, true)
    } catch {
      useAuthStore.getState().logout()
    }
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, errorMessage(body, response.status))
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

const post = <T>(endpoint: string, body?: unknown) => request<T>(endpoint, { method: "POST", body: JSON.stringify(body ?? {}) })

export const api = {
  login: (email: string, password: string) => post<TokenResponse>("/auth/login/", { email, password }),
  register: (name: string, email: string, password: string, role: UserRole) =>
    post<TokenResponse>(role === "HOST" ? "/auth/register/host/" : "/auth/register/renter/", { name, email, password }),
  refreshToken: (refresh: string) => post<TokenResponse>("/auth/refresh/", { refresh }),
  me: () => request<Me>("/auth/me/"),
  // Revokes every token this account holds, on all devices.
  logout: () => post<void>("/auth/logout/"),

  getMyGPUs: () => request<GPU[]>("/gpus/mine/"),
  getAvailableGPUs: () => request<GPU[]>("/gpus/available/"),
  updateGPU: (id: string, gpu: Partial<GPUInput>) => request<GPU>(`/gpus/${id}/`, { method: "PATCH", body: JSON.stringify(gpu) }),
  deleteGPU: (id: string) => request<void>(`/gpus/${id}/`, { method: "DELETE" }),

  getSessions: () => request<Session[]>("/sessions/"),
  createSession: (gpuId: string) => post<{ id: string }>("/sessions/", { gpu: gpuId }),
  endSession: (id: string) => post<{ status: SessionStatus; total_cost: number | string }>(`/sessions/${id}/end_session/`),

  getWallet: () => request<Wallet>("/wallets/"),
  addFunds: (amount: number) => post<{ balance: string }>("/wallets/add_funds/", { amount, description: "Deposit" }),
  withdrawFunds: (amount: number) => post<{ balance: string }>("/wallets/withdraw_funds/", { amount, description: "Withdrawal" }),

  getDashboardStats: () => request<DashboardStats>("/dashboard/stats/"),
}
