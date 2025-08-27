import { create } from "zustand"
import type { GPU, Session, Wallet, Transaction, DashboardStats } from "./types"
import { api } from "./api"
import { useAuthStore } from "./auth-store"

interface AppState {
  gpus: GPU[]
  sessions: Session[]
  wallet: Wallet | null
  transactions: Transaction[]
  dashboardStats: DashboardStats | null
  loading: boolean
  error: string | null
  setGPUs: (gpus: GPU[]) => void
  setSessions: (sessions: Session[]) => void
  setWallet: (wallet: Wallet) => void
  setTransactions: (transactions: Transaction[]) => void
  setDashboardStats: (stats: DashboardStats) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  fetchGPUs: () => Promise<void>
  fetchSessions: () => Promise<void>
  fetchWallet: () => Promise<void>
  fetchTransactions: () => Promise<void>
  fetchDashboardStats: () => Promise<void>
  rentGPU: (gpuId: string) => Promise<Session>
  endSession: (sessionId: string) => Promise<void>
  markSessionStarted: (sessionId: string, sshPassword?: string) => Promise<void>
  addFunds: (amount: number) => Promise<void>
  withdrawFunds: (amount: number) => Promise<void>
}

export const useAppStore = create<AppState>()((set, get) => ({
  gpus: [],
  sessions: [],
  wallet: null,
  transactions: [],
  dashboardStats: null,
  loading: false,
  error: null,

  setGPUs: (gpus) => set({ gpus }),
  setSessions: (sessions) => set({ sessions }),
  setWallet: (wallet) => set({ wallet }),
  setTransactions: (transactions) => set({ transactions }),
  setDashboardStats: (stats) => set({ dashboardStats: stats }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),

  fetchGPUs: async () => {
    try {
      set({ loading: true, error: null })
      // If host, fetch only host's GPUs from the nested endpoint; else fetch all
      const role = useAuthStore.getState().role
      const user = useAuthStore.getState().user
      let gpus
      if (role === 'HOST' && user && (user as any).id) {
        // user.id here is Django user id; our host id is returned by getHostProfile in auth flow
        // Since we don't store host id directly in auth store, fallback to general query filtered server-side
        try {
          // Try host-specific endpoint if we can get host id from API quickly
          const hostProfile = await api.getHostProfile()
          gpus = await api.getHostGPUs(hostProfile.id)
        } catch {
          // Fallback to general list (backend filters by host for host users)
          gpus = await api.getGPUs()
        }
      } else {
        gpus = await api.getGPUs()
      }
      set({ gpus, loading: false })
    } catch (error) {
      console.error('Failed to fetch GPUs:', error)
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch GPUs', 
        loading: false 
      })
    }
  },

  fetchSessions: async () => {
    try {
      set({ loading: true, error: null })
      const sessions = await api.getSessions()
      set({ sessions, loading: false })
    } catch (error) {
      console.error('Failed to fetch sessions:', error)
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch sessions', 
        loading: false 
      })
    }
  },

  fetchWallet: async () => {
    try {
      set({ loading: true, error: null })
      const wallet = await api.getWallet()
      set({ wallet, loading: false })
    } catch (error) {
      console.error('Failed to fetch wallet:', error)
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch wallet', 
        loading: false 
      })
    }
  },

  fetchTransactions: async () => {
    try {
      set({ loading: true, error: null })
      const transactions = await api.getTransactions()
      set({ transactions, loading: false })
    } catch (error) {
      console.error('Failed to fetch transactions:', error)
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch transactions', 
        loading: false 
      })
    }
  },

  fetchDashboardStats: async () => {
    try {
      set({ loading: true, error: null })
      const stats = await api.getDashboardStats()
      set({ dashboardStats: stats, loading: false })
    } catch (error) {
      console.error('Failed to fetch dashboard stats:', error)
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch dashboard stats', 
        loading: false 
      })
    }
  },

  rentGPU: async (gpuId: string) => {
    try {
      set({ loading: true, error: null })
      const newSession = await api.createSession({ gpu: gpuId })
      
      // Update sessions list
      const { sessions } = get()
      set({ 
        sessions: [...sessions, newSession], 
        loading: false 
      })
      
      // Refresh GPUs to update availability
      await get().fetchGPUs()
      return newSession
    } catch (error) {
      console.error('Failed to rent GPU:', error)
      set({ 
        error: error instanceof Error ? error.message : 'Failed to rent GPU', 
        loading: false 
      })
      throw error
    }
  },

  endSession: async (sessionId: string) => {
    try {
      set({ loading: true, error: null })
      const updatedSession = await api.endSession(sessionId)
      
      // Update sessions list
      const { sessions } = get()
      const updatedSessions = sessions.map(session => 
        session.id === sessionId ? updatedSession : session
      )
      set({ sessions: updatedSessions, loading: false })
      
      // Refresh GPUs to update availability
      await get().fetchGPUs()
    } catch (error) {
      console.error('Failed to end session:', error)
      set({ 
        error: error instanceof Error ? error.message : 'Failed to end session', 
        loading: false 
      })
      throw error
    }
  },

  markSessionStarted: async (sessionId: string, sshPassword?: string) => {
    try {
      set({ loading: true, error: null })
      await api.markSessionStarted(sessionId, sshPassword)
      // Refresh sessions to reflect ACTIVE state
      await get().fetchSessions()
      set({ loading: false })
    } catch (error) {
      console.error('Failed to mark session started:', error)
      set({
        error: error instanceof Error ? error.message : 'Failed to mark session started',
        loading: false
      })
      throw error
    }
  },

  addFunds: async (amount: number) => {
    try {
      set({ loading: true, error: null })
      await api.addFunds(amount)
      // Refresh wallet and transactions after server-side creation
      await Promise.all([get().fetchWallet(), get().fetchTransactions()])
      set({ loading: false })
    } catch (error) {
      console.error('Failed to add funds:', error)
      set({ 
        error: error instanceof Error ? error.message : 'Failed to add funds', 
        loading: false 
      })
      throw error
    }
  },

  withdrawFunds: async (amount: number) => {
    try {
      set({ loading: true, error: null })
      await api.withdrawFunds(amount)
      await Promise.all([get().fetchWallet(), get().fetchTransactions()])
      set({ loading: false })
    } catch (error) {
      console.error('Failed to withdraw funds:', error)
      set({ 
        error: error instanceof Error ? error.message : 'Failed to withdraw funds', 
        loading: false 
      })
      throw error
    }
  },
}))
