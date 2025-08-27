"use client"

import type React from "react"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/lib/auth-store"
import { Loader2 } from "lucide-react"

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: "HOST" | "RENTER"
}

export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { isAuthenticated, role, refreshAccessToken } = useAuthStore()
  const router = useRouter()

  useEffect(() => {
    const ensureAuth = async () => {
      if (!isAuthenticated) {
        try {
          // Try to refresh access token from persisted refresh token
          await refreshAccessToken()
          return
        } catch {
          router.push("/login")
          return
        }
      }

      if (requiredRole && role !== requiredRole) {
        router.push("/dashboard")
        return
      }
    }
    ensureAuth()
  }, [isAuthenticated, role, requiredRole, router, refreshAccessToken])

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (requiredRole && role !== requiredRole) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Access Denied</h1>
          <p className="text-muted-foreground">You don't have permission to access this page.</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
