"use client"

import { Label } from "@/components/ui/label"
import { useToast } from "@/hooks/use-toast"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { ProtectedRoute } from "@/components/auth/protected-route"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useAppStore } from "@/lib/app-store"
import { api } from "@/lib/api"
import { useAuthStore } from "@/lib/auth-store"
import type { Session } from "@/lib/types"
import { Activity, Server, Copy, Terminal, StopCircle, Clock, DollarSign, TrendingUp } from "lucide-react"
import { format } from "date-fns"

export default function SessionsPage() {
  const { role } = useAuthStore()
  const { sessions, loading, error, fetchSessions, endSession } = useAppStore()
  const { toast } = useToast()

  const [selectedSession, setSelectedSession] = useState<Session | null>(null)
  const [endingSession, setEndingSession] = useState<string | null>(null)
  const [connInfo, setConnInfo] = useState<Record<string, {host?: string; port?: number; user?: string}>>({})

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  // Auto-refresh while there are PENDING sessions so renter sees when the agent starts them
  useEffect(() => {
    if (sessions.some((s) => s.status === "PENDING")) {
      const id = setInterval(() => {
        fetchSessions().catch(() => {})
      }, 4000)
      return () => clearInterval(id)
    }
  }, [sessions, fetchSessions])

  // Fetch connection_info for ACTIVE sessions to ensure we show latest host/port/user from server
  useEffect(() => {
    const active = sessions.filter((s) => s.status === "ACTIVE")
    if (active.length === 0) return
    let cancelled = false
    ;(async () => {
      for (const s of active) {
        try {
          const info = await api.getSessionConnectionInfo(s.id)
          if (cancelled) break
          setConnInfo((prev) => ({
            ...prev,
            [s.id]: { host: info.ssh_host || undefined, port: info.ssh_port || undefined, user: info.ssh_username || undefined },
          }))
        } catch {}
      }
    })()
    return () => {
      cancelled = true
    }
  }, [sessions])

  const handleEndSession = async (sessionId: string) => {
    setEndingSession(sessionId)
    try {
      await endSession(sessionId)
    } catch (error) {
      console.error("Failed to end session:", error)
    } finally {
      setEndingSession(null)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast({
      title: "Copied to clipboard",
      description: "SSH connection command copied successfully",
    })
  }

  const getStatusBadge = (status: string) => {
    const variants = {
      ACTIVE: "default",
      COMPLETED: "secondary",
      CANCELLED: "destructive",
    } as const

    const colors = {
      ACTIVE: "bg-green-100 text-green-800",
      COMPLETED: "bg-blue-100 text-blue-800",
      CANCELLED: "bg-red-100 text-red-800",
    } as const

    return <Badge variant={variants[status as keyof typeof variants] || "secondary"}>{status}</Badge>
  }

  const calculateDuration = (startTime: string, endTime?: string) => {
    const start = new Date(startTime)
    const end = endTime ? new Date(endTime) : new Date()

    // Validate dates
    if (isNaN(start.getTime()) || isNaN(end.getTime())) {
      return "Invalid date"
    }

    // Ensure end time is after start time
    if (end.getTime() < start.getTime()) {
      return "0m"
    }

    const diffMs = end.getTime() - start.getTime()
    const totalMinutes = Math.floor(diffMs / (1000 * 60))
    const hours = Math.floor(totalMinutes / 60)
    const minutes = totalMinutes % 60

    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }

  const calculateEarnings = (session: Session) => {
    const start = new Date(session.start_time)
    const end = session.end_time ? new Date(session.end_time) : new Date()
    const diffMs = end.getTime() - start.getTime()
    const totalHours = diffMs / (1000 * 60 * 60) // Convert milliseconds to hours

    const pricePerHour = session.gpu.gpu_price || 0
    return Math.round(pricePerHour * totalHours)
  }

  const totalEarnings = sessions
    .filter((s) => s.status === "COMPLETED")
    .reduce((sum, session) => sum + calculateEarnings(session), 0)

  const currentEarnings = sessions
    .filter((s) => s.status === "ACTIVE")
    .reduce((sum, session) => sum + calculateEarnings(session), 0)

  if (loading) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="mt-2 text-muted-foreground">Loading sessions...</p>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">{role === "HOST" ? "Session Management" : "My Sessions"}</h1>
              <p className="text-muted-foreground">
                {role === "HOST"
                  ? "Monitor your GPU sessions and earnings"
                  : "View your active and completed GPU rental sessions"}
              </p>
            </div>
          </div>

          {role === "HOST" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Current Earnings</CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">Rs. {currentEarnings.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground">From active sessions</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Earnings</CardTitle>
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">Rs. {totalEarnings.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground">From completed sessions</p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Pending Sessions (waiting for agent) */}
          {sessions.filter((s) => s.status === "PENDING").length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Preparing Sessions
                </CardTitle>
                <CardDescription>
                  Waiting for the host agent to start your container and set up SSH
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {sessions
                    .filter((s) => s.status === "PENDING")
                    .map((session) => (
                      <Card key={session.id} className="border-l-4 border-l-yellow-500">
                        <CardContent className="pt-6">
                          <div className="flex items-start justify-between">
                            <div className="space-y-2">
                              <div className="flex items-center gap-2">
                                <h3 className="font-semibold">{session.gpu.gpu_name}</h3>
                                {getStatusBadge(session.status)}
                              </div>
                              <div className="text-sm text-muted-foreground">
                                Preparing your session... This page will update automatically.
                              </div>
                              {session.ssh_host && (
                                <div className="mt-2 p-2 bg-muted rounded">
                                  <div className="text-xs text-muted-foreground">SSH (assigned)</div>
                                  <div className="font-mono text-sm">
                                    ssh {session.ssh_username}@{session.ssh_host} -p {session.ssh_port}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Active Sessions */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Active Sessions
              </CardTitle>
              <CardDescription>
                {role === "HOST" ? "Currently earning from these sessions" : "Currently running GPU sessions"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {sessions.filter((s) => s.status === "ACTIVE").length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Server className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No active sessions</p>
                  <p className="text-sm">
                    {role === "HOST" ? "Your GPUs are available for rent" : "Rent a GPU to get started"}
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {sessions
                    .filter((s) => s.status === "ACTIVE")
                    .map((session) => (
                      <Card key={session.id} className="border-l-4 border-l-green-500">
                        <CardContent className="pt-6">
                          <div className="flex items-start justify-between">
                            <div className="space-y-2">
                              <div className="flex items-center gap-2">
                                <h3 className="font-semibold">{session.gpu.gpu_name}</h3>
                                {getStatusBadge(session.status)}
                              </div>
                              <div className="text-sm text-muted-foreground space-y-1">
                                <p>Duration: {calculateDuration(session.start_time)}</p>
                                <p>Started: {format(new Date(session.start_time), "MMM d, yyyy 'at' h:mm a")}</p>
                                {role === "HOST" ? (
                                  <p className="text-green-600 font-medium">
                                    Current Earnings: Rs. {calculateEarnings(session).toLocaleString()}
                                  </p>
                                ) : (
                                  (connInfo[session.id]?.host || session.ssh_host) && (
                                    <div className="mt-4 p-3 bg-muted rounded-lg">
                                      <div className="flex items-center gap-2 mb-2">
                                        <Terminal className="h-4 w-4" />
                                        <span className="font-medium text-sm">SSH Connection</span>
                                      </div>
                                      <div className="space-y-1 text-sm font-mono">
                                        <div className="flex items-center gap-2">
                                          <span>
                                            ssh {(connInfo[session.id]?.user || session.ssh_username)}@{(connInfo[session.id]?.host || session.ssh_host)} -p {(connInfo[session.id]?.port || session.ssh_port)}
                                          </span>
                                          <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() =>
                                              copyToClipboard(
                                                `ssh ${(connInfo[session.id]?.user || session.ssh_username)}@${(connInfo[session.id]?.host || session.ssh_host)} -p ${(connInfo[session.id]?.port || session.ssh_port)}`,
                                              )
                                            }
                                          >
                                            <Copy className="h-3 w-3" />
                                          </Button>
                                        </div>
                                      </div>
                                    </div>
                                  )
                                )}
                              </div>
                            </div>

                            <div className="flex flex-col gap-2">
                              <Button size="sm" variant="outline" onClick={() => setSelectedSession(session)}>
                                View Details
                              </Button>
                              {role === "HOST" && (
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => handleEndSession(session.id)}
                                  disabled={endingSession === session.id}
                                >
                                  <StopCircle className="mr-2 h-4 w-4" />
                                  {endingSession === session.id ? "Ending..." : "End Session"}
                                </Button>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Session History */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Session History
              </CardTitle>
              <CardDescription>
                {role === "HOST" ? "Previous sessions and earnings" : "Completed and cancelled sessions"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {sessions.filter((s) => s.status !== "ACTIVE").length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No session history</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>GPU</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Status</TableHead>
                      {role === "HOST" && <TableHead>Earnings</TableHead>}
                      <TableHead>Started</TableHead>
                      <TableHead>Ended</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sessions
                      .filter((s) => s.status !== "ACTIVE")
                      .map((session) => (
                        <TableRow key={session.id}>
                          <TableCell>
                            <div>
                              <div className="font-medium">{session.gpu.gpu_name}</div>
                              <div className="text-sm text-muted-foreground">{session.gpu.gpu_model}</div>
                            </div>
                          </TableCell>
                          <TableCell>
                            {session.end_time ? calculateDuration(session.start_time, session.end_time) : "—"}
                          </TableCell>
                          <TableCell>{getStatusBadge(session.status)}</TableCell>
                          {role === "HOST" && (
                            <TableCell>
                              {session.status === "COMPLETED" ? (
                                <span className="text-green-600 font-medium">
                                  Rs. {calculateEarnings(session).toLocaleString()}
                                </span>
                              ) : (
                                "—"
                              )}
                            </TableCell>
                          )}
                          <TableCell>{format(new Date(session.start_time), "MMM d, h:mm a")}</TableCell>
                          <TableCell>
                            {session.end_time ? format(new Date(session.end_time), "MMM d, h:mm a") : "—"}
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Session Details Dialog */}
        <Dialog open={!!selectedSession} onOpenChange={() => setSelectedSession(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Session Details</DialogTitle>
              <DialogDescription>Detailed information about this GPU session</DialogDescription>
            </DialogHeader>
            {selectedSession && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-sm font-medium">GPU</Label>
                    <p className="text-sm">{selectedSession.gpu.gpu_name}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Model</Label>
                    <p className="text-sm">{selectedSession.gpu.gpu_model}</p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Duration</Label>
                    <p className="text-sm">
                      {selectedSession.end_time
                        ? calculateDuration(selectedSession.start_time, selectedSession.end_time)
                        : calculateDuration(selectedSession.start_time)}
                    </p>
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Status</Label>
                    <div className="mt-1">{getStatusBadge(selectedSession.status)}</div>
                  </div>
                  {role === "HOST" ? (
                    <div>
                      <Label className="text-sm font-medium">Earnings</Label>
                      <p className="text-sm text-green-600 font-medium">
                        Rs. {calculateEarnings(selectedSession).toLocaleString()}
                      </p>
                    </div>
                  ) : (
                    selectedSession.ssh_host && (
                      <div className="col-span-2">
                        <Label className="text-sm font-medium">SSH Connection</Label>
                        <div className="mt-1 p-2 bg-muted rounded font-mono text-sm">
                          ssh {selectedSession.ssh_username}@{selectedSession.ssh_host} -p {selectedSession.ssh_port}
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setSelectedSession(null)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
