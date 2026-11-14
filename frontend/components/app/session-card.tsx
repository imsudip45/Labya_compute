"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import type { Session, UserRole } from "@/lib/types"
import { CopyField, Panel, StatusBadge, dateTime, duration, rs } from "./ui"

/** One running or starting session, with connection details for the renter and an end button for both sides. */
export function SessionCard({ session: s, role, onChange }: { session: Session; role: UserRole; onChange: () => void }) {
  const { toast } = useToast()
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pending = s.status === "PENDING"
  const other = role === "RENTER" ? `Host: ${s.host_name}` : `Renter: ${s.renter_name}`

  const end = async () => {
    setBusy(true)
    setError(null)
    try {
      const r = await api.endSession(s.id)
      toast({
        title: pending ? "Request cancelled" : "Session ended",
        description: pending ? undefined : role === "RENTER" ? `${rs(r.total_cost)} charged to your wallet.` : `${rs(r.total_cost)} added to your wallet.`,
      })
      setConfirm(false)
      onChange()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't end the session. Try again.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <Panel className="p-5 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-subheading font-medium">{s.gpu_name}</h3>
            <StatusBadge status={s.status} />
          </div>
          <p className="mt-1 text-body-sm text-ash">
            {other} · {pending ? `Requested ${dateTime(s.created_at)}` : `Started ${dateTime(s.start_time)}`}
          </p>
        </div>
        <Button variant="destructive" size="sm" onClick={() => setConfirm(true)}>
          {pending ? "Cancel request" : "End session"}
        </Button>
      </div>

      {pending ? (
        <p className="mt-5 text-body-sm text-cloud">
          {role === "RENTER"
            ? "Waiting for the host's agent to start your container. This page refreshes on its own, and the SSH details appear here when it's ready."
            : "Your agent will pick this up on its next check. Make sure the desktop agent is running."}
        </p>
      ) : (
        <>
          {s.connection_status === "ERROR" && (
            <p className="mt-5 text-body-sm text-system-warning">Connection problem: {s.connection_error || "the host's agent lost its connection."}</p>
          )}
          {role === "RENTER" && s.ssh_connection_string && (
            <div className="mt-5 grid gap-4 md:grid-cols-[2fr_1fr]">
              <CopyField label="SSH command" value={s.ssh_connection_string} />
              {s.ssh_password && <CopyField label="Password" value={s.ssh_password} secret />}
              <p className="text-caption text-ash md:col-span-2">
                The command needs <code className="font-mono">cloudflared</code> on your computer. Install it once from{" "}
                <a
                  href="https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/"
                  target="_blank"
                  rel="noreferrer"
                  className="text-whiteout underline decoration-graphite-light underline-offset-4 hover:decoration-whiteout"
                >
                  Cloudflare&apos;s download page
                </a>
                .
              </p>
            </div>
          )}
          <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-graphite-light pt-5 sm:grid-cols-5">
            {[
              ["Running for", duration(s.session_duration)],
              [role === "RENTER" ? "Cost so far" : "Earned so far", rs(s.total_cost)],
              ["GPU use", `${s.gpu_utilization}%`],
              ["Memory use", `${s.memory_utilization}%`],
              ["Temperature", `${s.temperature} °C`],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="text-caption text-ash">{k}</dt>
                <dd className="mt-0.5 font-mono text-body-sm tabular-nums">{v}</dd>
              </div>
            ))}
          </dl>
        </>
      )}

      <Dialog open={confirm} onOpenChange={setConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{pending ? "Cancel this request?" : "End this session?"}</DialogTitle>
            <DialogDescription className="text-body-sm text-ash">
              {pending
                ? "The session hasn't started, so nothing is charged."
                : role === "RENTER"
                  ? `Billing stops now. About ${rs(s.total_cost)} will be charged for ${duration(s.session_duration)}. Save your work first: you can't reconnect to this container.`
                  : `The renter loses access and is charged about ${rs(s.total_cost)} for ${duration(s.session_duration)}, which goes to your wallet.`}
            </DialogDescription>
          </DialogHeader>
          {error && <p role="alert" className="text-body-sm text-system-warning">{error}</p>}
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setConfirm(false)}>{pending ? "Go back" : "Keep running"}</Button>
            <Button variant="destructive" onClick={end} disabled={busy}>
              {busy ? "Ending…" : pending ? "Cancel request" : "End session"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Panel>
  )
}
