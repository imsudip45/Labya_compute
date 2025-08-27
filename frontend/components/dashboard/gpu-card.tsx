"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import type { GPU } from "@/lib/types"
import { Cpu, MapPin, MoreHorizontal, Edit, Trash2, Power } from "lucide-react"

interface GPUCardProps {
  gpu: GPU
  onEdit?: (gpu: GPU) => void
  onDelete?: (gpu: GPU) => void
  onToggleAvailability?: (gpu: GPU) => void
}

export function GPUCard({ gpu, onEdit, onDelete, onToggleAvailability }: GPUCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-lg font-semibold">{gpu.gpu_name}</CardTitle>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onEdit?.(gpu)}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onToggleAvailability?.(gpu)}>
              <Power className="mr-2 h-4 w-4" />
              {gpu.gpu_availability ? "Disable" : "Enable"}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onDelete?.(gpu)} className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <Badge variant={gpu.gpu_availability ? "default" : "secondary"}>
            {gpu.gpu_availability ? "Available" : "Unavailable"}
          </Badge>
          <span className="text-sm font-medium text-green-600">Rs.{gpu.gpu_price}/hour</span>
        </div>

        <div className="space-y-2">
          <div className="flex items-center text-sm text-muted-foreground">
            <Cpu className="mr-2 h-4 w-4" />
            {gpu.gpu_model} • {gpu.gpu_memory}GB VRAM
          </div>
          <div className="flex items-center text-sm text-muted-foreground">
            <MapPin className="mr-2 h-4 w-4" />
            {gpu.gpu_location}
          </div>
        </div>

        <div className="pt-2 border-t">
          <p className="text-xs text-muted-foreground">Created {new Date(gpu.created_at).toLocaleDateString()}</p>
        </div>
      </CardContent>
    </Card>
  )
}
