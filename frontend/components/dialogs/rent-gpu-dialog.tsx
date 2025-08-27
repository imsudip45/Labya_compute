"use client"

import type React from "react"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import type { GPU } from "@/lib/types"
import { Clock, Cpu, MapPin, User, CreditCard } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import { useAppStore } from "@/lib/app-store"
import { useRouter } from "next/navigation"

interface RentGPUDialogProps {
  gpu: GPU
  children: React.ReactNode
}

export function RentGPUDialog({ gpu, children }: RentGPUDialogProps) {
  const [duration, setDuration] = useState([1]) // Default 1 hour
  const [isOpen, setIsOpen] = useState(false)
  const [isRenting, setIsRenting] = useState(false)
  const { toast } = useToast()
  const { wallet, fetchSessions, fetchWallet } = useAppStore()
  const router = useRouter()

  const totalCost = Math.round(gpu.gpu_price * duration[0])
  const hours = Math.floor(duration[0])
  const minutes = Math.round((duration[0] - hours) * 60)

  const formatDuration = (hours: number) => {
    const h = Math.floor(hours)
    const m = Math.round((hours - h) * 60)
    if (h === 0) return `${m}m`
    if (m === 0) return `${h}h`
    return `${h}h ${m}m`
  }

  const handleRent = async () => {
    setIsRenting(true)
    try {
      // Pre-check funds
      const balance = wallet?.balance ?? 0
      if (balance < gpu.gpu_price) {
        toast({
          title: "Insufficient funds",
          description: `You need at least Rs.${gpu.gpu_price}. Current balance: Rs.${balance}.`,
          variant: "destructive",
        })
        setIsRenting(false)
        return
      }

      // Create session
      await api.createSession({ gpu: gpu.id })
      await Promise.all([fetchSessions(), fetchWallet()])

      toast({
        title: "GPU Rented Successfully!",
        description: `${gpu.gpu_name} rented for ${formatDuration(duration[0])} - Rs.${totalCost.toLocaleString()}`,
      })

      setIsOpen(false)
      router.push("/sessions")
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to rent GPU"
      toast({ title: "Rental failed", description: msg, variant: "destructive" })
    } finally {
      setIsRenting(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            Rent GPU
          </DialogTitle>
          <DialogDescription>Configure your rental duration and confirm the booking</DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* GPU Details */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-lg">{gpu.gpu_name}</h3>
              <Badge variant="default">Available</Badge>
            </div>

            <div className="space-y-2 text-sm text-muted-foreground">
              <div className="flex items-center">
                <Cpu className="mr-2 h-4 w-4" />
                {gpu.gpu_model} • {gpu.gpu_memory}GB VRAM
              </div>
              <div className="flex items-center">
                <MapPin className="mr-2 h-4 w-4" />
                {gpu.gpu_location}
              </div>
              <div className="flex items-center">
                <User className="mr-2 h-4 w-4" />
                {gpu.host_name || 'Unknown Host'}
              </div>
            </div>
          </div>

          <Separator />

          {/* Duration Selection */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Duration</label>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="font-semibold">{formatDuration(duration[0])}</span>
              </div>
            </div>

            <div className="space-y-3">
              <Slider value={duration} onValueChange={setDuration} max={24} min={0.5} step={0.5} className="w-full" />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>30m</span>
                <span>12h</span>
                <span>24h</span>
              </div>
            </div>
          </div>

          <Separator />

          {/* Cost Breakdown */}
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span>Rate per hour:</span>
              <span>Rs.{gpu.gpu_price.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span>Duration:</span>
              <span>{formatDuration(duration[0])}</span>
            </div>
            <Separator />
            <div className="flex justify-between font-semibold text-lg">
              <span>Total Cost:</span>
              <span className="text-green-600">Rs.{totalCost.toLocaleString()}</span>
            </div>
          </div>
        </div>

        <DialogFooter className="flex gap-2">
          <Button variant="outline" onClick={() => setIsOpen(false)} disabled={isRenting}>
            Cancel
          </Button>
          <Button onClick={handleRent} disabled={isRenting} className="flex-1">
            {isRenting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Renting...
              </>
            ) : (
              <>
                <CreditCard className="mr-2 h-4 w-4" />
                Rent for Rs.{totalCost.toLocaleString()}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
