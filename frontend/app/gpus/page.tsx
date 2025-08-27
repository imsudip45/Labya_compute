"use client"

import { useEffect } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { ProtectedRoute } from "@/components/auth/protected-route"
import { GPUCard } from "@/components/dashboard/gpu-card"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAppStore } from "@/lib/app-store"
import { Plus, Cpu } from "lucide-react"
import { LabhyaAgentDialog } from "@/components/dialogs/labhya-agent-dialog"
import type { GPU } from "@/lib/types"

export default function GPUsPage() {
  const { gpus, loading, error, fetchGPUs } = useAppStore()

  useEffect(() => {
    fetchGPUs()
  }, [fetchGPUs])

  // gpus already filtered to current host in fetchGPUs (for host role)

  if (loading) {
    return (
      <ProtectedRoute requiredRole="HOST">
        <DashboardLayout>
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="mt-2 text-muted-foreground">Loading your GPUs...</p>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  if (error) {
    return (
      <ProtectedRoute requiredRole="HOST">
        <DashboardLayout>
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <p className="text-destructive mb-2">Error loading GPUs</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute requiredRole="HOST">
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">My GPUs</h1>
              <p className="text-muted-foreground">Manage your GPU resources and monitor their performance</p>
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
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total GPUs</CardTitle>
                <Cpu className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{gpus.length}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Available</CardTitle>
                <div className="h-2 w-2 bg-green-500 rounded-full" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{gpus.filter((gpu) => gpu.gpu_availability).length}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">In Use</CardTitle>
                <div className="h-2 w-2 bg-blue-500 rounded-full" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{gpus.filter((gpu) => !gpu.gpu_availability).length}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg. Price</CardTitle>
                <span className="text-xs text-muted-foreground">NPR/hr</span>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  Rs.{" "}
                  {gpus.length > 0
                    ? Math.round(gpus.reduce((sum, gpu) => sum + gpu.gpu_price, 0) / gpus.length)
                    : 0}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* GPU Grid */}
          {gpus.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Cpu className="h-12 w-12 text-muted-foreground mb-4" />
                <CardTitle className="mb-2">No GPUs Added</CardTitle>
                <CardDescription className="text-center mb-4">
                  Start earning by adding your GPU resources to the platform
                </CardDescription>
                <LabhyaAgentDialog>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Add Your First GPU
                  </Button>
                </LabhyaAgentDialog>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {gpus.map((gpu) => (
                <GPUCard key={gpu.id} gpu={gpu} />
              ))}
            </div>
          )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
