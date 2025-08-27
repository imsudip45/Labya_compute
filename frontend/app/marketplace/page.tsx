"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { ProtectedRoute } from "@/components/auth/protected-route"
import { GPUFilters } from "@/components/marketplace/gpu-filters"
import { AvailableGPUCard } from "@/components/dashboard/available-gpu-card"
import { RentGPUDialog } from "@/components/marketplace/rent-gpu-dialog"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAppStore } from "@/lib/app-store"
import { useAuthStore } from "@/lib/auth-store"
import type { GPU } from "@/lib/types"
import { Grid, List, SlidersHorizontal } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

export default function MarketplacePage() {
  const router = useRouter()
  const { role, isAuthenticated } = useAuthStore()
  const { gpus, loading, error, fetchGPUs, wallet, fetchWallet, fetchSessions } = useAppStore()
  const { toast } = useToast()

  const [filteredGPUs, setFilteredGPUs] = useState<GPU[]>([])
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid")
  const [sortBy, setSortBy] = useState("price-low")
  const [selectedGPU, setSelectedGPU] = useState<GPU | null>(null)
  const [rentDialogOpen, setRentDialogOpen] = useState(false)
  const [showFilters, setShowFilters] = useState(true)

  useEffect(() => {
    if (isAuthenticated) {
      fetchGPUs()
      fetchWallet().catch(() => {})
    }
  }, [isAuthenticated, fetchGPUs, fetchWallet])

  useEffect(() => {
    const availableGPUs = gpus.filter((gpu) => gpu.gpu_availability)
    setFilteredGPUs(availableGPUs)
  }, [gpus])

  const handleSearch = (query: string) => {
    if (!query.trim()) {
      setFilteredGPUs(gpus.filter((gpu) => gpu.gpu_availability))
      return
    }

    const filtered = gpus.filter(
      (gpu) =>
        gpu.gpu_availability &&
        (gpu.gpu_name.toLowerCase().includes(query.toLowerCase()) ||
        gpu.gpu_model.toLowerCase().includes(query.toLowerCase()) ||
        gpu.gpu_location.toLowerCase().includes(query.toLowerCase())),
    )
    setFilteredGPUs(filtered)
  }

  const handleFiltersChange = (filters: any) => {
    let filtered = gpus.filter((gpu) => gpu.gpu_availability)

    // Filter by price range
    if (filters.priceRange) {
      filtered = filtered.filter(
        (gpu) => gpu.gpu_price >= filters.priceRange[0] && gpu.gpu_price <= filters.priceRange[1],
      )
    }

    // Filter by memory range
    if (filters.memoryRange) {
      filtered = filtered.filter(
        (gpu) => gpu.gpu_memory >= filters.memoryRange[0] && gpu.gpu_memory <= filters.memoryRange[1],
      )
    }

    // Filter by availability
    if (filters.availability) {
      filtered = filtered.filter((gpu) => gpu.gpu_availability)
    }

    // Filter by locations
    if (filters.locations && filters.locations.length > 0) {
      filtered = filtered.filter((gpu) => filters.locations.includes(gpu.gpu_location))
    }

    // Filter by models
    if (filters.models && filters.models.length > 0) {
      filtered = filtered.filter((gpu) => filters.models.includes(gpu.gpu_model))
    }

    setFilteredGPUs(filtered)
  }

  const handleSort = (sortValue: string) => {
    setSortBy(sortValue)
    const sorted = [...filteredGPUs]

    switch (sortValue) {
      case "price-low":
        sorted.sort((a, b) => a.gpu_price - b.gpu_price)
        break
      case "price-high":
        sorted.sort((a, b) => b.gpu_price - a.gpu_price)
        break
      case "memory-high":
        sorted.sort((a, b) => b.gpu_memory - a.gpu_memory)
        break
      case "memory-low":
        sorted.sort((a, b) => a.gpu_memory - b.gpu_memory)
        break
      case "newest":
        sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        break
      default:
        break
    }

    setFilteredGPUs(sorted)
  }

  const handleRentGPU = (gpu: GPU) => {
    setSelectedGPU(gpu)
    setRentDialogOpen(true)
  }

  const handleConfirmRent = async (gpu: GPU, hours: number) => {
    try {
      // Pre-check wallet funds
      const balance = wallet?.balance ?? 0
      if (balance < gpu.gpu_price) {
        toast({
          title: "Insufficient funds",
          description: `You need at least Rs.${gpu.gpu_price} to rent this GPU. Current balance: Rs.${balance}.`,
          variant: "destructive",
        })
        return
      }
      // Session was created inside the dialog. Refresh sessions and redirect.
      await fetchSessions()
      setRentDialogOpen(false)
      setSelectedGPU(null)
      router.push("/sessions")
      console.log(`Requested rental for ${gpu.gpu_name}. Waiting for agent to start.`)
    } catch (error) {
      console.error("Failed to rent GPU:", error)
      const message = error instanceof Error ? error.message : "Failed to rent GPU"
      toast({ title: "Rental failed", description: message, variant: "destructive" })
    }
  }

  // Add loading state for authentication
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">Loading authentication...</p>
        </div>
      </div>
    )
  }

  if (role === "HOST") {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <h2 className="text-2xl font-bold mb-4">Access Restricted</h2>
              <p className="text-muted-foreground mb-4">
                The marketplace is only available to renters. As a host, you can manage your GPUs from the dashboard.
              </p>
              <Button onClick={() => router.push("/dashboard")}>Go to Dashboard</Button>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  if (loading) {
    return (
      <ProtectedRoute requiredRole="RENTER">
        <DashboardLayout>
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="mt-2 text-muted-foreground">Loading marketplace...</p>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  if (error) {
    return (
      <ProtectedRoute requiredRole="RENTER">
        <DashboardLayout>
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <p className="text-destructive mb-2">Error loading marketplace</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute requiredRole="RENTER">
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">GPU Marketplace</h1>
              <p className="text-muted-foreground">Browse and rent GPU computing power from verified hosts</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)}>
                <SlidersHorizontal className="mr-2 h-4 w-4" />
                Filters
              </Button>
              <div className="flex items-center border rounded-md">
                <Button
                  variant={viewMode === "grid" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("grid")}
                >
                  <Grid className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === "list" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("list")}
                >
                  <List className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {filteredGPUs.length} GPU{filteredGPUs.length !== 1 ? "s" : ""} available
            </p>
            <Select value={sortBy} onValueChange={handleSort}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="price-low">Price: Low to High</SelectItem>
                <SelectItem value="price-high">Price: High to Low</SelectItem>
                <SelectItem value="memory-high">Memory: High to Low</SelectItem>
                <SelectItem value="memory-low">Memory: Low to High</SelectItem>
                <SelectItem value="newest">Newest First</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Main Content */}
          <div className="grid gap-6 lg:grid-cols-4">
            {/* Filters Sidebar */}
            {showFilters && (
              <div className="lg:col-span-1">
                <GPUFilters onFiltersChange={handleFiltersChange} onSearch={handleSearch} />
              </div>
            )}

            {/* GPU Grid */}
            <div className={showFilters ? "lg:col-span-3" : "lg:col-span-4"}>
              {filteredGPUs.length === 0 ? (
                <div className="text-center py-12">
                  <div className="text-muted-foreground">
                    <Grid className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p className="text-lg font-medium">No GPUs found</p>
                    <p className="text-sm">Try adjusting your filters or search terms</p>
                  </div>
                </div>
              ) : (
                <div className={`grid gap-4 ${viewMode === "grid" ? "md:grid-cols-2 xl:grid-cols-3" : "grid-cols-1"}`}>
                  {filteredGPUs.map((gpu) => (
                    <AvailableGPUCard key={gpu.id} gpu={gpu} onRent={handleRentGPU} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Rent GPU Dialog */}
        <RentGPUDialog
          gpu={selectedGPU}
          open={rentDialogOpen}
          onOpenChange={setRentDialogOpen}
          onConfirm={handleConfirmRent}
        />
      </DashboardLayout>
    </ProtectedRoute>
  )
}
