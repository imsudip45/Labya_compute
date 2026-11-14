"use client"

import { useState, type FormEvent } from "react"
import { Download } from "lucide-react"
import { AppShell } from "@/components/app/shell"
import { Empty, LoadError, PageHeader, Section, Skeleton, Table, rs } from "@/components/app/ui"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import type { GPU } from "@/lib/types"
import { useLoad } from "@/lib/use-load"
import { AGENT_INSTALLER, AGENT_PORTABLE } from "@/lib/downloads"

export default function GPUsPage() {
  return (
    <AppShell only="HOST">
      <MyGPUs />
    </AppShell>
  )
}

function MyGPUs() {
  const { data: gpus, error, loading, reload } = useLoad(api.getMyGPUs, 15_000)
  const [editing, setEditing] = useState<GPU | null>(null)
  const [removing, setRemoving] = useState<GPU | null>(null)

  const header = <PageHeader title="My GPUs" description="GPUs your desktop agent has listed. Set the price and whether each one can be rented." />
  if (loading) return <>{header}<Skeleton /></>
  if (!gpus) return <>{header}<LoadError message={error ?? ""} onRetry={reload} /></>

  const status = (g: GPU) => (g.is_rented ? "Rented" : g.gpu_availability ? "Available" : "Not for rent")

  return (
    <>
      {header}
      {gpus.length === 0 ? (
        <Empty
          title="No GPUs listed yet"
          body="Install the desktop agent on the PC with your GPU and log in with this account. The agent detects your GPU and lists it here."
          action={<Button asChild><a href={AGENT_INSTALLER} download><Download aria-hidden /> Download agent for Windows</a></Button>}
        />
      ) : (
        <Table head={[{ label: "GPU" }, { label: "VRAM", right: true }, { label: "Location" }, { label: "Price", right: true }, { label: "Status" }, { label: "" }]}>
          {gpus.map((g) => {
            const rented = g.is_rented
            return (
              <tr key={g.id} className="hover:bg-graphite">
                <td className="px-5 py-4">
                  <div className="font-medium">{g.gpu_name}</div>
                  {g.gpu_model && <div className="font-mono text-caption text-pewter">{g.gpu_model}</div>}
                </td>
                <td className="px-5 py-4 text-right font-mono tabular-nums">{g.gpu_memory} GB</td>
                <td className="px-5 py-4 text-ash">{g.gpu_location}</td>
                <td className="px-5 py-4 text-right font-mono tabular-nums">{rs(g.gpu_price)}<span className="text-ash">/hr</span></td>
                <td className="px-5 py-4">
                  <span className="inline-flex items-center gap-2 text-caption text-cloud">
                    <span className={`h-1.5 w-1.5 rounded-full ${rented ? "bg-cloud" : g.gpu_availability ? "bg-neon-glow" : "bg-ash"}`} aria-hidden />
                    {status(g)}
                  </span>
                </td>
                <td className="whitespace-nowrap px-5 py-4 text-right">
                  <Button variant="ghost" size="sm" onClick={() => setEditing(g)}>Edit</Button>
                  <Button variant="ghost" size="sm" className="text-system-warning hover:text-system-warning" onClick={() => setRemoving(g)} disabled={rented} title={rented ? "End the session before removing this GPU" : undefined}>
                    Remove
                  </Button>
                </td>
              </tr>
            )
          })}
        </Table>
      )}

      <Section title="Desktop agent">
        <div className="rounded-sm border border-graphite-light bg-graphite-deep p-5 text-body-sm text-ash sm:p-6">
          <p>
            The agent runs on your Windows PC. It lists your GPU, starts a Docker container when someone rents it, and reports GPU use while the session runs.
            Keep it open whenever your GPU is available to rent. It needs Windows 10 or 11, WSL2 and Docker Desktop.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button variant="outline" size="sm" asChild><a href={AGENT_INSTALLER} download><Download aria-hidden /> Installer (.exe)</a></Button>
            <Button variant="outline" size="sm" asChild><a href={AGENT_PORTABLE} download><Download aria-hidden /> Portable (.exe)</a></Button>
          </div>
        </div>
      </Section>

      {editing && <EditGPU gpu={editing} onClose={() => setEditing(null)} onSaved={reload} />}
      {removing && <RemoveGPU gpu={removing} onClose={() => setRemoving(null)} onRemoved={reload} />}
    </>
  )
}

function EditGPU({ gpu, onClose, onSaved }: { gpu: GPU; onClose: () => void; onSaved: () => void }) {
  const { toast } = useToast()
  const [available, setAvailable] = useState(gpu.gpu_availability)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    const price = Number(f.get("price"))
    const location = String(f.get("location")).trim()
    if (!Number.isInteger(price) || price < 1) return setError("Enter a whole number of rupees, 1 or more.")
    if (!location) return setError("Enter where this GPU is located.")
    setBusy(true)
    setError(null)
    try {
      await api.updateGPU(gpu.id, { gpu_price: price, gpu_location: location, gpu_availability: available })
      toast({ title: `${gpu.gpu_name} updated` })
      onSaved()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save. Try again.")
      setBusy(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <form onSubmit={submit} className="grid gap-6">
          <DialogHeader>
            <DialogTitle>Edit {gpu.gpu_name}</DialogTitle>
            <DialogDescription className="text-body-sm text-ash">Changes apply to new sessions. A session that's already running keeps its price.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-5">
            <div>
              <label htmlFor="price" className="mb-1.5 block text-body-sm">Price per hour (NPR)</label>
              <Input id="price" name="price" type="number" min="1" step="1" defaultValue={gpu.gpu_price} required />
            </div>
            <div>
              <label htmlFor="location" className="mb-1.5 block text-body-sm">Location</label>
              <Input id="location" name="location" defaultValue={gpu.gpu_location} required />
              <p className="mt-1.5 text-caption text-pewter">City or area. Renters see this.</p>
            </div>
            <div className="flex items-start justify-between gap-4 rounded-sm border border-graphite-light p-4">
              <div>
                <label htmlFor="available" className="text-body-sm">Available to rent</label>
                <p className="mt-0.5 text-caption text-ash">
                  {gpu.is_rented ? "Turn off to stop new rentals. The running session isn't affected." : "Turn off to hide this GPU from renters."}
                </p>
              </div>
              <Switch id="available" checked={available} onCheckedChange={setAvailable} />
            </div>
          </div>
          {error && <p role="alert" className="text-body-sm text-system-warning">{error}</p>}
          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={busy}>{busy ? "Saving…" : "Save changes"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function RemoveGPU({ gpu, onClose, onRemoved }: { gpu: GPU; onClose: () => void; onRemoved: () => void }) {
  const { toast } = useToast()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const remove = async () => {
    setBusy(true)
    try {
      await api.deleteGPU(gpu.id)
      toast({ title: `${gpu.gpu_name} removed` })
      onRemoved()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't remove it. Try again.")
      setBusy(false)
    }
  }
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Remove {gpu.gpu_name}?</DialogTitle>
          <DialogDescription className="text-body-sm text-ash">
            Renters won't see it any more. To list it again, register it from the desktop agent.
          </DialogDescription>
        </DialogHeader>
        {error && <p role="alert" className="text-body-sm text-system-warning">{error}</p>}
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose}>Keep it</Button>
          <Button variant="destructive" onClick={remove} disabled={busy}>{busy ? "Removing…" : "Remove GPU"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
