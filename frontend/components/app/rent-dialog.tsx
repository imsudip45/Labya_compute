"use client"

import { useState, type ReactNode } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import type { GPU } from "@/lib/types"
import { rs } from "./ui"

export function RentDialog({ gpu, children }: { gpu: GPU; children: ReactNode }) {
  const router = useRouter()
  const { toast } = useToast()
  const [open, setOpen] = useState(false)
  const [balance, setBalance] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const onOpenChange = (o: boolean) => {
    setOpen(o)
    setError(null)
    if (o) api.getWallet().then((w) => setBalance(Number(w.balance))).catch(() => setBalance(null))
  }

  // The API needs at least one hour's price in the wallet to start a session.
  const short = balance !== null && balance < gpu.gpu_price

  const rent = async () => {
    setBusy(true)
    setError(null)
    try {
      await api.createSession(gpu.id)
      toast({ title: "Session requested", description: `${gpu.gpu_name} will start when the host's agent picks it up.` })
      router.push("/sessions")
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't start the session. Try again.")
      setBusy(false)
    }
  }

  const rows: [string, ReactNode][] = [
    ["GPU", <>{gpu.gpu_name}{gpu.gpu_model && <span className="text-ash"> · {gpu.gpu_model}</span>}</>],
    ["VRAM", `${gpu.gpu_memory} GB`],
    ["Location", gpu.gpu_location],
    ["Host", gpu.host_name],
    ["Price", `${rs(gpu.gpu_price)}/hr`],
    ["Your balance", balance === null ? "—" : rs(balance)],
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Rent {gpu.gpu_name}</DialogTitle>
          <DialogDescription className="text-body-sm text-ash">
            You pay {rs(gpu.gpu_price)} for each hour the session runs. The cost is taken from your wallet when you end the session.
          </DialogDescription>
        </DialogHeader>

        <dl className="divide-y divide-graphite-light rounded-sm border border-graphite-light text-body-sm">
          {rows.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 px-4 py-2.5">
              <dt className="text-ash">{k}</dt>
              <dd className="text-right">{v}</dd>
            </div>
          ))}
        </dl>

        {short && (
          <p className="text-body-sm text-system-warning">
            You need at least {rs(gpu.gpu_price)} in your wallet to start this session.{" "}
            <Link href="/wallet" className="text-whiteout underline underline-offset-4">Add funds</Link>
          </p>
        )}
        {error && <p role="alert" className="text-body-sm text-system-warning">{error}</p>}

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={rent} disabled={busy || short || balance === null}>{busy ? "Starting…" : "Rent GPU"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
