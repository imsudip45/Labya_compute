"use client"

// Building blocks for the logged-in app. Styling and wording follow CLAUDE.md.

import { useState, type ReactNode } from "react"
import { Check, Copy, Eye, EyeOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { SessionStatus } from "@/lib/types"
import { cn } from "@/lib/utils"

export const rs = (n: number | string | null | undefined) => {
  const v = Number(n ?? 0)
  return `Rs ${v.toLocaleString("en-IN", { minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 })}`
}

export function duration(hours: number) {
  const mins = Math.round(hours * 60)
  if (mins < 60) return `${mins} min`
  return `${Math.floor(mins / 60)} h ${mins % 60} min`
}

export function dateTime(iso: string | null) {
  if (!iso) return "—"
  // API timestamps are UTC; older ones may lack the zone suffix.
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`)
  return d.toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
}

export function PageHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-heading font-medium">{title}</h1>
        {description && <p className="mt-1 text-body-sm text-ash">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function Section({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="mt-10">
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-subheading font-medium">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}

export function Stats({ items }: { items: { label: string; value: ReactNode; hint?: string }[] }) {
  return (
    <dl className={cn("grid gap-px overflow-hidden rounded-sm border border-graphite-light bg-graphite-light", items.length > 2 ? "grid-cols-2 lg:grid-cols-4" : "grid-cols-2")}>
      {items.map((s) => (
        <div key={s.label} className="flex flex-col bg-graphite-deep p-5">
          <dt className="order-2 mt-1 text-body-sm text-ash">{s.label}</dt>
          <dd className="font-mono text-heading-sm tabular-nums">{s.value}</dd>
          {s.hint && <p className="order-3 mt-1 text-caption text-pewter">{s.hint}</p>}
        </div>
      ))}
    </dl>
  )
}

export function Panel({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn("rounded-sm border border-graphite-light bg-graphite-deep", className)}>{children}</div>
}

const STATUS: Record<SessionStatus, { label: string; dot: string }> = {
  PENDING: { label: "Starting", dot: "bg-cloud animate-pulse" },
  ACTIVE: { label: "Running", dot: "bg-neon-glow" },
  COMPLETED: { label: "Ended", dot: "bg-ash" },
  CANCELLED: { label: "Cancelled", dot: "bg-ash" },
}

export function StatusBadge({ status }: { status: SessionStatus }) {
  const s = STATUS[status] ?? { label: status, dot: "bg-ash" }
  return (
    <span className="inline-flex items-center gap-2 text-caption text-cloud">
      <span className={cn("h-1.5 w-1.5 rounded-full", s.dot)} aria-hidden />
      {s.label}
    </span>
  )
}

export function Empty({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <Panel className="px-6 py-12 text-center">
      <p className="text-body font-medium">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-body-sm text-ash">{body}</p>
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </Panel>
  )
}

export function LoadError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Panel className="flex flex-col gap-4 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-body-sm font-medium text-system-warning">Couldn't load this page</p>
        <p className="mt-1 text-body-sm text-ash">{message}</p>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry}>Try again</Button>
    </Panel>
  )
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <Panel className="divide-y divide-graphite-light" aria-busy>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex animate-pulse items-center gap-4 px-5 py-5">
          <div className="h-4 w-40 rounded-sm bg-graphite" />
          <div className="ml-auto h-4 w-20 rounded-sm bg-graphite" />
        </div>
      ))}
    </Panel>
  )
}

/** A read-only value with a copy button; `secret` hides it until revealed. */
export function CopyField({ label, value, secret }: { label: string; value: string; secret?: boolean }) {
  const [copied, setCopied] = useState(false)
  const [shown, setShown] = useState(!secret)
  const copy = async () => {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div>
      <p className="mb-1.5 text-caption text-ash">{label}</p>
      <div className="flex items-center gap-1 rounded-sm border border-graphite-light bg-blackout pl-3">
        <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap py-2.5 font-mono text-body-sm">
          {shown ? value : "•".repeat(Math.min(value.length, 16))}
        </code>
        {secret && (
          <button className="grid h-9 w-9 shrink-0 place-items-center rounded-sm text-ash hover:text-whiteout" onClick={() => setShown((s) => !s)} aria-label={shown ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}>
            {shown ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        )}
        <button className="grid h-9 w-9 shrink-0 place-items-center rounded-sm text-ash hover:text-whiteout" onClick={copy} aria-label={`Copy ${label.toLowerCase()}`}>
          {copied ? <Check className="h-4 w-4 text-neon-glow" /> : <Copy className="h-4 w-4" />}
        </button>
      </div>
    </div>
  )
}

/** Table wrapper: horizontal scroll inside the panel on narrow screens. */
export function Table({ head, children }: { head: { label: string; right?: boolean }[]; children: ReactNode }) {
  return (
    <Panel className="overflow-x-auto">
      <table className="w-full min-w-[640px] text-left text-body-sm">
        <thead className="text-caption text-ash">
          <tr className="border-b border-graphite-light">
            {head.map((h, i) => (
              <th key={i} className={cn("px-5 py-3 font-normal", h.right && "text-right")}>{h.label}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-graphite-light">{children}</tbody>
      </table>
    </Panel>
  )
}
