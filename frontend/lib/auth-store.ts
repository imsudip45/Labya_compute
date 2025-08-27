import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { User, UserRole } from "./types"
import { api } from "./api"

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  accessToken: string | null
  refreshToken: string | null
  role: UserRole | null
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string, role: UserRole) => Promise<void>
  logout: () => void
  refreshAccessToken: () => Promise<void>
  fetchUserProfile: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      accessToken: null,
      refreshToken: null,
      role: null,

      login: async (email: string, password: string) => {
        try {
          const data = await api.login(email, password)
          
          // First, set the tokens so API calls can use them
          set({
            isAuthenticated: true,
            accessToken: data.access,
            refreshToken: data.refresh,
          })
          
          // After setting tokens, fetch user profile to determine role
          let user: User | null = null
          let role: UserRole | null = null
          
          try {
            // Try to get host profile first
            const hostProfile = await api.getHostProfile()
            user = hostProfile.user
            role = 'HOST'
          } catch (hostError) {
            try {
              // If not host, try renter profile
              const renterProfile = await api.getRenterProfile()
              user = renterProfile.user
              role = 'RENTER'
            } catch (renterError) {
              // If neither works, we'll need to handle this case
              console.warn('Could not determine user role after login')
            }
          }

          // Update with user and role
          set({
            user,
            role,
          })
        } catch (error) {
          console.error('Login error:', error)
          throw new Error(error instanceof Error ? error.message : "Login failed")
        }
      },

      register: async (name: string, email: string, password: string, role: UserRole) => {
        try {
          const data = await api.register(name, email, password, role)
          
          // Create a temporary user object from the registration data
          const user: User = {
            id: role === 'HOST' ? data.host_id! : data.renter_id!,
            username: email,
            email: email,
            first_name: name.split(' ')[0],
            last_name: name.split(' ')[1] || '',
          }

          set({
            user,
            isAuthenticated: true,
            accessToken: data.access,
            refreshToken: data.refresh,
            role,
          })
        } catch (error) {
          console.error('Registration error:', error)
          throw new Error(error instanceof Error ? error.message : "Registration failed")
        }
      },

      logout: () => {
        set({
          user: null,
          isAuthenticated: false,
          accessToken: null,
          refreshToken: null,
          role: null,
        })
      },

      refreshAccessToken: async () => {
        try {
          const { refreshToken } = get()
          if (!refreshToken) throw new Error("No refresh token")

          const data = await api.refreshToken(refreshToken)
          set({ accessToken: data.access })
        } catch (error) {
          console.error('Token refresh error:', error)
          get().logout()
          throw new Error("Token refresh failed")
        }
      },

      fetchUserProfile: async () => {
        try {
          const { role } = get()
          if (!role) return

          let user: User | null = null
          
          if (role === 'HOST') {
            const hostProfile = await api.getHostProfile()
            user = hostProfile.user
          } else if (role === 'RENTER') {
            const renterProfile = await api.getRenterProfile()
            user = renterProfile.user
          }

          if (user) {
            set({ user })
          }
        } catch (error) {
          console.error('Fetch user profile error:', error)
        }
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        role: state.role,
      }),
    },
  ),
)
