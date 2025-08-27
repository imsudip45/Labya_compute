"use client"

import { useEffect } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { ProtectedRoute } from "@/components/auth/protected-route"
import { StatsCard } from "@/components/dashboard/stats-card"
import { GPUCard } from "@/components/dashboard/gpu-card"
import { RecentSessions } from "@/components/dashboard/recent-sessions"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/lib/auth-store"
import { useAppStore } from "@/lib/app-store"
import { Cpu, Activity, DollarSign, Wallet, Plus, Store, CreditCard } from "lucide-react"
import { AvailableGPUCard } from "@/components/dashboard/available-gpu-card"
import { ActiveSessionCard } from "@/components/dashboard/active-session-card"
import { LabhyaAgentDialog } from "@/components/dialogs/labhya-agent-dialog"

export default function DashboardPage() {
  const { role } = useAuthStore()
  const {
    gpus,
    sessions,
    wallet,
    dashboardStats,
    loading,
    error,
    fetchGPUs,
    fetchSessions,
    fetchWallet,
    fetchDashboardStats,
  } = useAppStore()

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        await Promise.all([fetchGPUs(), fetchSessions(), fetchWallet(), fetchDashboardStats()])
      } catch (error) {
        console.error("Failed to load dashboard data:", error)
      }
    }

    loadDashboardData()
  }, [role, fetchGPUs, fetchSessions, fetchWallet, fetchDashboardStats])

  if (loading) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="mt-2 text-muted-foreground">Loading dashboard...</p>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  if (error) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <p className="text-destructive mb-2">Error loading dashboard</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  if (role === "HOST") {
    return (
      <ProtectedRoute requiredRole="HOST">
        <DashboardLayout>
          <div className="space-y-6">
            {/* Welcome Section */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold">Host Dashboard</h1>
                <p className="text-muted-foreground">Manage your GPU resources and monitor earnings</p>
              </div>
              <LabhyaAgentDialog>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Add GPU
                </Button>
              </LabhyaAgentDialog>
            </div>

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <StatsCard
                title="Total GPUs"
                value={dashboardStats?.totalGPUs || 0}
                description={`${(gpus || []).filter((g) => g.gpu_availability).length} available`}
                icon={Cpu}
              />
              <StatsCard
                title="Active Sessions"
                value={dashboardStats?.activeSessions || 0}
                description="Currently running"
                icon={Activity}
              />
              <StatsCard
                title="Today's Earnings"
                value={`Rs.${dashboardStats?.todaysEarnings?.toLocaleString() || "0"}`}
                description="Revenue today"
                icon={DollarSign}
                trend={{ value: 12.5, isPositive: true }}
              />
              <StatsCard
                title="Wallet Balance"
                value={`Rs.${wallet?.balance?.toLocaleString() || "0"}`}
                description="Available funds"
                icon={Wallet}
              />
            </div>

            {/* Main Content Grid */}
            <div className="grid gap-6 lg:grid-cols-3">
              {/* My GPUs Section */}
              <div className="lg:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold">My GPUs</h2>
                  <Button variant="outline" size="sm">
                    View All
                  </Button>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  {(gpus || []).slice(0, 4).map((gpu) => (
                    <GPUCard
                      key={gpu.id}
                      gpu={gpu}
                      onEdit={(gpu) => console.log("Edit GPU:", gpu)}
                      onDelete={(gpu) => console.log("Delete GPU:", gpu)}
                      onToggleAvailability={(gpu) => console.log("Toggle availability:", gpu)}
                    />
                  ))}
                </div>
              </div>

              {/* Recent Sessions */}
              <div>
                <RecentSessions sessions={sessions} onViewAll={() => console.log("View all sessions")} />
              </div>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  if (role === "RENTER") {
    return (
      <ProtectedRoute requiredRole="RENTER">
        <DashboardLayout>
          <div className="space-y-6">
            {/* Welcome Section */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold">Renter Dashboard</h1>
                <p className="text-muted-foreground">Browse and rent GPU computing power</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline">
                  <CreditCard className="mr-2 h-4 w-4" />
                  Add Funds
                </Button>
                <Button>
                  <Store className="mr-2 h-4 w-4" />
                  Browse GPUs
                </Button>
              </div>
            </div>

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <StatsCard
                title="Active Sessions"
                value={(sessions || []).filter((s) => s.status === "ACTIVE").length}
                description="Currently running"
                icon={Activity}
              />
              <StatsCard
                title="Total Sessions"
                value={dashboardStats?.totalSessions || (sessions || []).length}
                description="All time"
                icon={Cpu}
              />
              <StatsCard
                title="Total Spent"
                value={`Rs.${dashboardStats?.totalSpent?.toLocaleString() || "0"}`}
                description="All time spending"
                icon={DollarSign}
              />
              <StatsCard
                title="Wallet Balance"
                value={`Rs.${wallet?.balance?.toLocaleString() || "0"}`}
                description="Available funds"
                icon={Wallet}
              />
            </div>

            {/* Main Content Grid */}
            <div className="grid gap-6 lg:grid-cols-3">
              {/* Available GPUs Section */}
              <div className="lg:col-span-2 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold">Available GPUs</h2>
                  <Button variant="outline" size="sm">
                    View All
                  </Button>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  {(gpus || [])
                    .filter((gpu) => gpu.gpu_availability)
                    .slice(0, 4)
                    .map((gpu) => (
                      <AvailableGPUCard
                        key={gpu.id}
                        gpu={gpu}
                        onRent={(gpu) => {
                          // The RentGPUDialog component handles the rental process
                        }}
                      />
                    ))}
                </div>
              </div>

              {/* Active Sessions */}
              <div className="space-y-4">
                <h2 className="text-xl font-semibold">My Sessions</h2>
                {(sessions || []).filter((session) => session.status === "ACTIVE").length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No active sessions</p>
                    <p className="text-sm">Rent a GPU to get started</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {(sessions || [])
                      .filter((session) => session.status === "ACTIVE")
                      .map((session) => (
                        <ActiveSessionCard
                          key={session.id}
                          session={session}
                          onEndSession={(session) => console.log("End session:", session)}
                        />
                      ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  // Placeholder for other roles (will be built in future tasks)
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="text-center py-12">
          <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
          <p className="text-muted-foreground">Coming soon...</p>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
