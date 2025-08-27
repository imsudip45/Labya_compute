"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Alert, AlertDescription } from "@/components/ui/alert"
import type { GPU } from "@/lib/types"
import { Cpu, MapPin, User, Clock, AlertTriangle } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"

interface RentGPUDialogProps {
  gpu: GPU | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: (gpu: GPU, hours: number) => void
}

export function RentGPUDialog({ gpu, open, onOpenChange, onConfirm }: RentGPUDialogProps) {
  const [hours, setHours] = useState(1)
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  if (!gpu) return null

  const totalCost = gpu.gpu_price * hours
  const estimatedCost = totalCost * 1.1 // Add 10% buffer

  const handleConfirm = async () => {
    setLoading(true)
    try {
      // Create session immediately; delegate store updates to caller
      await api.createSession({ gpu: gpu.id })
      await onConfirm(gpu, hours)
      onOpenChange(false)
      toast({
        title: "GPU Rented Successfully",
        description: `${gpu.gpu_name} has been rented for ${hours} hour${hours > 1 ? "s" : ""}`,
      })
    } catch (error) {
      toast({
        title: "Rental Failed",
        description: error instanceof Error ? error.message : "Failed to rent GPU. Please try again.",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Rent GPU</DialogTitle>
          <DialogDescription>Configure your GPU rental session</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* GPU Details */}
          <div className="space-y-3">
            <h3 className="font-semibold">{gpu.gpu_name}</h3>
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

          {/* Rental Configuration */}
          <div className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="hours">Rental Duration (hours)</Label>
              <Input
                id="hours"
                type="number"
                min="1"
                max="24"
                value={hours}
                onChange={(e) => setHours(Math.max(1, Number.parseInt(e.target.value) || 1))}
              />
            </div>

            {/* Cost Breakdown */}
            <div className="space-y-2 p-3 bg-muted rounded-lg">
              <div className="flex justify-between text-sm">
                <span>Hourly Rate:</span>
                <span>Rs.{gpu.gpu_price}/hour</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Duration:</span>
                <span>
                  {hours} hour{hours > 1 ? "s" : ""}
                </span>
              </div>
              <Separator />
              <div className="flex justify-between font-medium">
                <span>Total Cost:</span>
                <span>Rs.{totalCost.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>Estimated (with buffer):</span>
                <span>Rs.{estimatedCost.toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Warning */}
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              You will be charged based on actual usage. The session can be ended early to save costs.
            </AlertDescription>
          </Alert>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={loading}>
            {loading ? (
              <>
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Renting...
              </>
            ) : (
              <>
                <Clock className="mr-2 h-4 w-4" />
                Rent for Rs.{totalCost.toLocaleString()}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
