"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { Session } from "@/lib/types"
import { Clock, User, Cpu } from "lucide-react"

interface RecentSessionsProps {
  sessions: Session[]
  onViewAll?: () => void
}

export function RecentSessions({ sessions, onViewAll }: RecentSessionsProps) {
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
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>Recent Sessions</CardTitle>
        <Button variant="outline" size="sm" onClick={onViewAll}>
          View All
        </Button>
      </CardHeader>
      <CardContent>
        {sessions.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">No recent sessions</p>
        ) : (
          <div className="space-y-4">
            {sessions.map((session) => (
              <div key={session.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <Cpu className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{session.gpu.gpu_name}</span>
                    <Badge variant={getStatusColor(session.status)} size="sm">
                      {session.status}
                    </Badge>
                  </div>
                  <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                    <div className="flex items-center">
                      <User className="mr-1 h-3 w-3" />
                      {session.renter_name || 'Unknown Renter'}
                    </div>
                    <div className="flex items-center">
                      <Clock className="mr-1 h-3 w-3" />
                      {new Date(session.start_time).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                {session.status === "ACTIVE" && (
                  <div className="text-right">
                    <div className="text-sm font-medium text-green-600">Rs.{session.gpu.gpu_price}/hr</div>
                    <div className="text-xs text-muted-foreground">Running</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
