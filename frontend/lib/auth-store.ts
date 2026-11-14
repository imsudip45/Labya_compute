import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { Me, UserRole } from "./types"
import { api } from "./api"

interface AuthState {
  user: Me | null
  role: UserRole | null
  isAuthenticated: boolean
  accessToken: string | null
  refreshToken: string | null
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string, role: UserRole) => Promise<void>
  /** Forget the tokens on this device. */
  logout: () => void
  /** Revoke the tokens on the server (all devices), then forget them here. */
  signOut: () => Promise<void>
  refreshAccessToken: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => {
      // Store tokens, then ask the API who this is. Roll back if that fails.
      const start = async (tokens: { access: string; refresh: string }) => {
        set({ accessToken: tokens.access, refreshToken: tokens.refresh })
        try {
          const me = await api.me()
          set({ user: me, role: me.role, isAuthenticated: true })
        } catch (e) {
          get().logout()
          throw e
        }
      }
      return {
        user: null,
        role: null,
        isAuthenticated: false,
        accessToken: null,
        refreshToken: null,
        login: async (email, password) => start(await api.login(email, password)),
        register: async (name, email, password, role) => start(await api.register(name, email, password, role)),
        logout: () => set({ user: null, role: null, isAuthenticated: false, accessToken: null, refreshToken: null }),
        signOut: async () => {
          await api.logout().catch(() => {}) // already expired is fine
          get().logout()
        },
        refreshAccessToken: async () => {
          const refresh = get().refreshToken
          if (!refresh) throw new Error("Not logged in")
          const data = await api.refreshToken(refresh)
          set({ accessToken: data.access, refreshToken: data.refresh })
        },
      }
    },
    {
      name: "auth-storage",
      partialize: ({ user, role, isAuthenticated, accessToken, refreshToken }) => ({ user, role, isAuthenticated, accessToken, refreshToken }),
    },
  ),
)
