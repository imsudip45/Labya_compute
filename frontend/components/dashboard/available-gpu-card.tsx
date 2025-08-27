"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { GPU } from "@/lib/types"
import { Cpu, MapPin, Clock, User } from "lucide-react"
import { RentGPUDialog } from "@/components/dialogs/rent-gpu-dialog"

interface AvailableGPUCardProps {
  gpu: GPU
  onRent?: (gpu: GPU) => void
}

export function AvailableGPUCard({ gpu, onRent }: AvailableGPUCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">{gpu.gpu_name}</CardTitle>
          <Badge variant="default">Available</Badge>
        </div>
        <div className="text-2xl font-bold text-green-600">Rs.{gpu.gpu_price}/hour</div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center text-sm text-muted-foreground">
            <Cpu className="mr-2 h-4 w-4" />
            {gpu.gpu_model} • {gpu.gpu_memory}GB VRAM
          </div>
          <div className="flex items-center text-sm text-muted-foreground">
            <MapPin className="mr-2 h-4 w-4" />
            {gpu.gpu_location}
          </div>
          <div className="flex items-center text-sm text-muted-foreground">
            <User className="mr-2 h-4 w-4" />
            {gpu.host_name || 'Unknown Host'}
          </div>
        </div>

        <div className="pt-2 border-t">
          <RentGPUDialog gpu={gpu}>
            <Button className="w-full">
              <Clock className="mr-2 h-4 w-4" />
              Rent Now
            </Button>
          </RentGPUDialog>
        </div>
      </CardContent>
    </Card>
  )
}
