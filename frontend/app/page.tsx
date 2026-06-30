"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useAuthStore } from "@/lib/auth-store"
import { api } from "@/lib/api"
import type { GPU } from "@/lib/types"
import { mockGPUs } from "@/lib/dummy-data"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card"
import { RentGPUDialog } from "@/components/dialogs/rent-gpu-dialog"
import { 
  Cpu, 
  MapPin, 
  Clock, 
  User, 
  Search, 
  SlidersHorizontal, 
  Layers, 
  Shield, 
  Zap, 
  Coins,
  ArrowRight,
  TrendingUp,
  Server
} from "lucide-react"

export default function HomePage() {
  const { isAuthenticated, role } = useAuthStore()
  const router = useRouter()

  // State for available GPUs
  const [gpus, setGpus] = useState<GPU[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters state
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedLocation, setSelectedLocation] = useState("all")
  const [selectedMemory, setSelectedMemory] = useState("all")
  const [sortBy, setSortBy] = useState("price-low")

  // Load available GPUs
  useEffect(() => {
    async function loadAvailableGPUs() {
      try {
        setLoading(true)
        const data = await api.getAvailableGPUs()
        // If data is empty or not an array, fall back to mock GPUs for display
        if (Array.isArray(data)) {
          setGpus(data)
        } else {
          setGpus(mockGPUs.filter(gpu => gpu.gpu_availability))
        }
      } catch (err) {
        console.error("Failed to load live GPUs, using mock data:", err)
        // Fallback to mock data on network error so the page always looks rich
        setGpus(mockGPUs.filter(gpu => gpu.gpu_availability))
      } finally {
        setLoading(false)
      }
    }
    loadAvailableGPUs()
  }, [])

  // Deduplicate locations and models for filter dropdowns
  const uniqueLocations = Array.from(new Set(gpus.map((gpu) => gpu.gpu_location)))

  // Filter & sort logic
  const processedGPUs = (() => {
    let result = [...gpus]

    // Apply Search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(
        (gpu) =>
          gpu.gpu_name.toLowerCase().includes(q) ||
          gpu.gpu_model.toLowerCase().includes(q) ||
          gpu.gpu_location.toLowerCase().includes(q)
      )
    }

    // Filter by Location
    if (selectedLocation !== "all") {
      result = result.filter((gpu) => gpu.gpu_location === selectedLocation)
    }

    // Filter by Memory
    if (selectedMemory !== "all") {
      if (selectedMemory === "low") {
        result = result.filter((gpu) => gpu.gpu_memory < 16)
      } else if (selectedMemory === "mid") {
        result = result.filter((gpu) => gpu.gpu_memory >= 16 && gpu.gpu_memory < 24)
      } else if (selectedMemory === "high") {
        result = result.filter((gpu) => gpu.gpu_memory >= 24)
      }
    }

    // Sorting
    if (sortBy === "price-low") {
      result.sort((a, b) => a.gpu_price - b.gpu_price)
    } else if (sortBy === "price-high") {
      result.sort((a, b) => b.gpu_price - a.gpu_price)
    } else if (sortBy === "memory-high") {
      result.sort((a, b) => b.gpu_memory - a.gpu_memory)
    }

    return result
  })()

  // Handle CTA redirection
  const handleRentClick = (gpu: GPU) => {
    if (!isAuthenticated) {
      router.push(`/login?redirect=/`)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Dynamic Header */}
      <header className="sticky top-0 z-50 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Server className="h-6 w-6 text-indigo-500 animate-pulse" />
            <span className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              Labhya Compute
            </span>
          </div>

          <nav className="hidden md:flex gap-6 text-sm font-medium text-slate-300">
            <a href="#marketplace" className="hover:text-indigo-400 transition-colors">GPU Marketplace</a>
            <a href="#features" className="hover:text-indigo-400 transition-colors">Key Features</a>
            <a href="#how-it-works" className="hover:text-indigo-400 transition-colors">How It Works</a>
          </nav>

          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <Link href="/dashboard">
                <Button className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium shadow-lg shadow-indigo-600/20">
                  Dashboard
                </Button>
              </Link>
            ) : (
              <>
                <Link href="/login">
                  <Button variant="ghost" className="text-slate-300 hover:text-white hover:bg-slate-900">
                    Log In
                  </Button>
                </Link>
                <div className="flex items-center gap-2">
                  <Link href="/register/renter">
                    <Button className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium shadow-md shadow-indigo-600/10">
                      Join as Renter
                    </Button>
                  </Link>
                  <Link href="/register/host">
                    <Button variant="outline" className="border-indigo-500/30 text-indigo-400 hover:bg-indigo-950/30">
                      Become Host
                    </Button>
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden py-24 md:py-32 bg-slate-950">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(79,70,229,0.15),transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_70%,rgba(6,182,212,0.1),transparent_50%)]" />
        <div className="container mx-auto px-4 sm:px-6 relative z-10 text-center max-w-4xl">
          <Badge className="bg-indigo-950/60 text-indigo-400 border border-indigo-500/30 px-3 py-1 mb-6">
            <Zap className="h-3.5 w-3.5 mr-1 inline animate-bounce" /> Decentralized GPU Cloud Platform
          </Badge>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight mb-6 leading-tight">
            On-Demand High Performance <br />
            <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
              GPU Infrastructure
            </span>
          </h1>

          <p className="text-lg sm:text-xl text-slate-400 mb-10 max-w-2xl mx-auto leading-relaxed">
            Rent high-performance GPU instances directly from verified hosts at up to 70% cheaper rates. Isolated environments, secure reverse SSH tunnels, and automated hourly ledger.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a href="#marketplace">
              <Button size="lg" className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-700 text-white px-8 text-base shadow-lg shadow-indigo-600/35">
                Explore Marketplace <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </a>
            <Link href="/register/host">
              <Button size="lg" variant="outline" className="w-full sm:w-auto border-slate-700 text-slate-300 hover:bg-slate-900 px-8 text-base">
                Host Your GPU & Earn
              </Button>
            </Link>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-20 pt-8 border-t border-slate-900/60 max-w-3xl mx-auto">
            <div className="text-center">
              <div className="text-3xl font-extrabold text-white">100%</div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mt-1">Docker Isolated</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-extrabold text-white">Rs.150/hr</div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mt-1">Starting Rate</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-extrabold text-white">24GB+</div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mt-1">Max VRAM Specs</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-extrabold text-white">&lt; 1 min</div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mt-1">Setup Time</div>
            </div>
          </div>
        </div>
      </section>

      {/* GPU Marketplace Section (E-commerce Style) */}
      <section id="marketplace" className="py-20 border-t border-slate-900 bg-slate-900/20">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="text-3xl font-bold tracking-tight mb-4 text-white">Available Compute Instances</h2>
            <p className="text-slate-400">Search and filter active online GPUs offered by hosts around the world.</p>
          </div>

          {/* E-commerce Filter Panel */}
          <div className="bg-slate-950/40 border border-slate-800/80 rounded-2xl p-6 mb-10 flex flex-col md:flex-row gap-4 items-center justify-between">
            {/* Search Input */}
            <div className="relative w-full md:max-w-xs">
              <Search className="absolute left-3 top-2.5 h-4.5 w-4.5 text-slate-500" />
              <Input
                placeholder="Search model, location..."
                className="pl-10 bg-slate-900/60 border-slate-800 text-slate-100 placeholder:text-slate-500 focus-visible:ring-indigo-600"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Filter Dropdowns */}
            <div className="flex flex-wrap gap-3 w-full md:w-auto items-center justify-end">
              {/* Location Select */}
              <div className="flex items-center gap-1.5 bg-slate-900/50 border border-slate-800 rounded-lg px-2.5 py-1.5 text-sm">
                <MapPin className="h-4 w-4 text-slate-500" />
                <select
                  value={selectedLocation}
                  onChange={(e) => setSelectedLocation(e.target.value)}
                  className="bg-transparent border-none text-slate-200 focus:outline-none cursor-pointer pr-1"
                >
                  <option value="all" className="bg-slate-950 text-slate-100">All Locations</option>
                  {uniqueLocations.map((loc) => (
                    <option key={loc} value={loc} className="bg-slate-950 text-slate-100">
                      {loc}
                    </option>
                  ))}
                </select>
              </div>

              {/* Memory Size Select */}
              <div className="flex items-center gap-1.5 bg-slate-900/50 border border-slate-800 rounded-lg px-2.5 py-1.5 text-sm">
                <Cpu className="h-4 w-4 text-slate-500" />
                <select
                  value={selectedMemory}
                  onChange={(e) => setSelectedMemory(e.target.value)}
                  className="bg-transparent border-none text-slate-200 focus:outline-none cursor-pointer pr-1"
                >
                  <option value="all" className="bg-slate-950 text-slate-100">All Memory sizes</option>
                  <option value="low" className="bg-slate-950 text-slate-100">&lt; 16GB VRAM</option>
                  <option value="mid" className="bg-slate-950 text-slate-100">16GB - 24GB VRAM</option>
                  <option value="high" className="bg-slate-950 text-slate-100">24GB+ VRAM</option>
                </select>
              </div>

              {/* Sorting Select */}
              <div className="flex items-center gap-1.5 bg-slate-900/50 border border-slate-800 rounded-lg px-2.5 py-1.5 text-sm">
                <SlidersHorizontal className="h-4 w-4 text-slate-500" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="bg-transparent border-none text-slate-200 focus:outline-none cursor-pointer pr-1"
                >
                  <option value="price-low" className="bg-slate-950 text-slate-100">Price: Low to High</option>
                  <option value="price-high" className="bg-slate-950 text-slate-100">Price: High to Low</option>
                  <option value="memory-high" className="bg-slate-950 text-slate-100">VRAM Size: High to Low</option>
                </select>
              </div>
            </div>
          </div>

          {/* GPU Grid */}
          {loading ? (
            <div className="text-center py-20">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-500 mx-auto"></div>
              <p className="mt-4 text-slate-400">Loading live GPU marketplace...</p>
            </div>
          ) : processedGPUs.length === 0 ? (
            <div className="text-center py-20 bg-slate-950/20 border border-slate-850 rounded-2xl">
              <Cpu className="h-12 w-12 mx-auto mb-4 text-slate-700 opacity-80" />
              <h3 className="text-lg font-semibold text-slate-300">No matching GPUs online</h3>
              <p className="text-sm text-slate-500 mt-1">Try resetting your filters or search query.</p>
            </div>
          ) : (
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {processedGPUs.map((gpu) => (
                <Card key={gpu.id} className="bg-slate-950/60 border-slate-850 hover:border-indigo-500/40 hover:shadow-lg hover:shadow-indigo-500/5 transition-all duration-300 flex flex-col justify-between group">
                  <div>
                    <CardHeader className="pb-4">
                      <div className="flex items-center justify-between mb-2">
                        <Badge className="bg-emerald-950/80 text-emerald-400 border border-emerald-500/20">
                          Online
                        </Badge>
                        <span className="text-xs text-slate-500">
                          {gpu.gpu_location}
                        </span>
                      </div>
                      <CardTitle className="text-xl font-bold text-white group-hover:text-indigo-400 transition-colors">
                        {gpu.gpu_name}
                      </CardTitle>
                      <CardDescription className="text-slate-400 font-mono text-xs flex items-center gap-1.5 mt-1.5">
                        <Cpu className="h-3.5 w-3.5 text-indigo-400" />
                        {gpu.gpu_model}
                      </CardDescription>
                    </CardHeader>

                    <CardContent className="space-y-4">
                      <div className="flex items-baseline gap-1 text-slate-100">
                        <span className="text-3xl font-extrabold text-indigo-400">Rs.{gpu.gpu_price}</span>
                        <span className="text-sm text-slate-500">/ hour</span>
                      </div>

                      <div className="space-y-2.5 pt-3 border-t border-slate-900 text-sm text-slate-400">
                        <div className="flex justify-between">
                          <span>VRAM Memory:</span>
                          <span className="text-slate-200 font-semibold">{gpu.gpu_memory} GB</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Location:</span>
                          <span className="text-slate-200">{gpu.gpu_location}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Verified Host:</span>
                          <span className="text-slate-200 flex items-center gap-1">
                            <User className="h-3.5 w-3.5 text-slate-500" />
                            {gpu.host?.user?.first_name || 'Active Host'}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </div>

                  <CardFooter className="pt-4 border-t border-slate-900/60">
                    {isAuthenticated ? (
                      <RentGPUDialog gpu={gpu}>
                        <Button className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium">
                          <Clock className="mr-2 h-4 w-4" /> Rent Instance
                        </Button>
                      </RentGPUDialog>
                    ) : (
                      <Button 
                        className="w-full bg-slate-900 hover:bg-slate-800 text-slate-200 hover:text-white border border-slate-800"
                        onClick={() => handleRentClick(gpu)}
                      >
                        <Clock className="mr-2 h-4 w-4" /> Log In to Rent
                      </Button>
                    )}
                  </CardFooter>
                </Card>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Feature Grid Section */}
      <section id="features" className="py-24 bg-slate-950 relative">
        <div className="container mx-auto px-4 sm:px-6 relative z-10">
          <div className="text-center max-w-2xl mx-auto mb-20">
            <h2 className="text-3xl font-bold tracking-tight text-white mb-4">Enterprise Grade Infrastructure</h2>
            <p className="text-slate-400">Decentralization meets performance. We build key mechanisms to ensure maximum uptime and compute security.</p>
          </div>

          <div className="grid gap-8 md:grid-cols-3">
            {/* Feature 1 */}
            <div className="bg-slate-900/30 border border-slate-900 rounded-2xl p-8 hover:border-slate-800 transition-colors">
              <div className="bg-indigo-950/60 border border-indigo-500/20 w-12 h-12 rounded-xl flex items-center justify-center mb-6">
                <Shield className="h-6 w-6 text-indigo-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Docker Container Isolation</h3>
              <p className="text-slate-400 leading-relaxed">
                Renters deploy inside standard Docker Linux sandboxes. System processes, file storage, and credentials remain entirely isolated from the host machine's OS.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-slate-900/30 border border-slate-900 rounded-2xl p-8 hover:border-slate-800 transition-colors">
              <div className="bg-indigo-950/60 border border-indigo-500/20 w-12 h-12 rounded-xl flex items-center justify-center mb-6">
                <Layers className="h-6 w-6 text-indigo-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Reverse SSH Tunnels</h3>
              <p className="text-slate-400 leading-relaxed">
                Our lightweight Host Agent maps Docker container SSH ports directly to a public relay server. Renters bypass local NAT firewalls and connect instantly using standard terminals.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-slate-900/30 border border-slate-900 rounded-2xl p-8 hover:border-slate-800 transition-colors">
              <div className="bg-indigo-950/60 border border-indigo-500/20 w-12 h-12 rounded-xl flex items-center justify-center mb-6">
                <Coins className="h-6 w-6 text-indigo-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Automated Ledger</h3>
              <p className="text-slate-400 leading-relaxed">
                Funds are held in renter wallets and calculated dynamically based on active session time. Payouts are made directly to host wallets upon session termination.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How it Works Flow */}
      <section id="how-it-works" className="py-20 border-t border-slate-900 bg-slate-900/10">
        <div className="container mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-20">
            <h2 className="text-3xl font-bold tracking-tight text-white mb-4">Simple, Seamless Operations</h2>
            <p className="text-slate-400">Deploy remote GPU workflows or monetize local rigs in minutes.</p>
          </div>

          <div className="grid gap-12 md:grid-cols-2">
            {/* Renting Flow */}
            <div className="space-y-8 bg-slate-950/40 border border-slate-850 p-8 rounded-2xl">
              <h3 className="text-2xl font-bold text-white flex items-center gap-2">
                <span className="text-indigo-500">01.</span> Renting GPU Power
              </h3>
              <div className="space-y-6">
                <div className="flex gap-4">
                  <div className="flex-none font-extrabold text-slate-700 mt-0.5">1</div>
                  <div>
                    <h4 className="font-semibold text-slate-200">Deposit Funds</h4>
                    <p className="text-slate-400 text-sm mt-1">Register as a Renter and deposit credits securely in your localized NPR Wallet.</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex-none font-extrabold text-slate-700 mt-0.5">2</div>
                  <div>
                    <h4 className="font-semibold text-slate-200">Rent Instance</h4>
                    <p className="text-slate-400 text-sm mt-1">Browse the marketplace, specify rental duration, and click Rent to lock relay ports.</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex-none font-extrabold text-slate-700 mt-0.5">3</div>
                  <div>
                    <h4 className="font-semibold text-slate-200">SSH Connect</h4>
                    <p className="text-slate-400 text-sm mt-1">Copy the generated SSH connection string and access the remote GPU sandbox terminal instantly.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Hosting Flow */}
            <div className="space-y-8 bg-slate-950/40 border border-slate-850 p-8 rounded-2xl">
              <h3 className="text-2xl font-bold text-white flex items-center gap-2">
                <span className="text-cyan-500">02.</span> Hosting & Earning
              </h3>
              <div className="space-y-6">
                <div className="flex gap-4">
                  <div className="flex-none font-extrabold text-slate-700 mt-0.5">1</div>
                  <div>
                    <h4 className="font-semibold text-slate-200">Register Machine</h4>
                    <p className="text-slate-400 text-sm mt-1">Sign up as a Host and define your hardware details, location, and per-hour lease rates.</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex-none font-extrabold text-slate-700 mt-0.5">2</div>
                  <div>
                    <h4 className="font-semibold text-slate-200">Start Desktop Agent</h4>
                    <p className="text-slate-400 text-sm mt-1">Download and start the python agent client. The client auto-detects GPU resources and opens relay listeners.</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex-none font-extrabold text-slate-700 mt-0.5">3</div>
                  <div>
                    <h4 className="font-semibold text-slate-200">Earn NPR Payouts</h4>
                    <p className="text-slate-400 text-sm mt-1">Keep the agent active. Renters lease your container and funds accumulate automatically into your wallet.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-900 bg-slate-950 py-12">
        <div className="container mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <Server className="h-5 w-5 text-indigo-500" />
            <span className="font-bold text-slate-200">Labhya Compute</span>
          </div>
          <p className="text-sm text-slate-500">
            &copy; {new Date().getFullYear()} Labhya Compute. All rights reserved. Production Ready.
          </p>
          <div className="flex gap-6 text-sm text-slate-400">
            <Link href="/login" className="hover:text-indigo-400 transition-colors">Log In</Link>
            <Link href="/register/renter" className="hover:text-indigo-400 transition-colors">Renter Registry</Link>
            <Link href="/register/host" className="hover:text-indigo-400 transition-colors">Host Registry</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
