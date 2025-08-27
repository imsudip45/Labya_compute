"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import type { Session } from "@/lib/types"
import { Cpu, Terminal, Copy, Activity, Thermometer, MemoryStick, StopCircle } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface ActiveSessionCardProps {
  session: Session
  onEndSession?: (session: Session) => void
}

export function ActiveSessionCard({ session, onEndSession }: ActiveSessionCardProps) {
  const { toast } = useToast()

  const calculateDuration = () => {
    const start = new Date(session.start_time)
    const now = new Date()
    const diffMs = now.getTime() - start.getTime()

    // Prevent negative durations and unrealistic values
    if (diffMs < 0 || diffMs > 24 * 60 * 60 * 1000) {
      return "0h 0m"
    }

    const totalMinutes = Math.floor(diffMs / (1000 * 60))
    const hours = Math.floor(totalMinutes / 60)
    const minutes = totalMinutes % 60

    return `${hours}h ${minutes}m`
  }

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    toast({
      title: "Copied to clipboard",
      description: `${label} copied successfully`,
    })
  }

  const getStatusColor = (status: Session["status"]) => {
    switch (status) {
      case "ACTIVE":
        return "default"
      case "COMPLETED":
        return "secondary"
      case "CANCELLED":
        return "destructive"
      default:
        return "secondary"
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold">{session.gpu.gpu_name}</CardTitle>
          <Badge variant={getStatusColor(session.status)}>{session.status}</Badge>
        </div>
        <div className="text-sm text-muted-foreground">
          Started {new Date(session.start_time).toLocaleString()}
          {session.status === "ACTIVE" && (
            <span className="ml-2 font-medium text-primary">• Duration: {calculateDuration()}</span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* GPU Info */}
        <div className="flex items-center text-sm text-muted-foreground">
          <Cpu className="mr-2 h-4 w-4" />
          {session.gpu.gpu_model} • {session.gpu.gpu_memory}GB VRAM
        </div>

        {session.status === "ACTIVE" && session.ssh_host && (
          <>
            <Separator />

            {/* SSH Connection Details */}
            <div className="space-y-3">
              <div className="flex items-center text-sm font-medium">
                <Terminal className="mr-2 h-4 w-4" />
                SSH Connection
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between bg-muted p-2 rounded">
                  <span className="font-mono">{session.ssh_host}</span>
                  <Button variant="ghost" size="sm" onClick={() => copyToClipboard(session.ssh_host!, "SSH Host")}>
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>

                <div className="flex items-center justify-between bg-muted p-2 rounded">
                  <span className="font-mono">Port: {session.ssh_port}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(session.ssh_port!.toString(), "SSH Port")}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>

                <div className="flex items-center justify-between bg-muted p-2 rounded">
                  <span className="font-mono">User: {session.ssh_username}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(session.ssh_username!, "SSH Username")}
                  >
                    <Copy className="h-3 w-3" />
                  </Button>
                </div>

                {session.ssh_password && (
                  <div className="flex items-center justify-between bg-muted p-2 rounded">
                    <span className="font-mono">Password: ******</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(session.ssh_password!, "SSH Password")}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                )}
              </div>
            </div>

            <Separator />

            {/* GPU Metrics */}
            <div className="space-y-3">
              <div className="text-sm font-medium">GPU Metrics</div>
              <div className="grid grid-cols-3 gap-2 text-sm">
                <div className="text-center p-2 bg-muted rounded">
                  <Activity className="h-4 w-4 mx-auto mb-1" />
                  <div className="font-medium">{session.gpu_utilization}%</div>
                  <div className="text-xs text-muted-foreground">GPU</div>
                </div>
                <div className="text-center p-2 bg-muted rounded">
                  <MemoryStick className="h-4 w-4 mx-auto mb-1" />
                  <div className="font-medium">{session.memory_utilization}%</div>
                  <div className="text-xs text-muted-foreground">Memory</div>
                </div>
                <div className="text-center p-2 bg-muted rounded">
                  <Thermometer className="h-4 w-4 mx-auto mb-1" />
                  <div className="font-medium">{session.temperature}°C</div>
                  <div className="text-xs text-muted-foreground">Temp</div>
                </div>
              </div>
            </div>

            <Button variant="destructive" size="sm" className="w-full" onClick={() => onEndSession?.(session)}>
              <StopCircle className="mr-2 h-4 w-4" />
              End Session
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  )
}
