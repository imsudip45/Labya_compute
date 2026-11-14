"use client"

import Link from "next/link"
import { AppShell } from "@/components/app/shell"
import { SessionCard } from "@/components/app/session-card"
import { Empty, LoadError, PageHeader, Section, Skeleton, StatusBadge, Table, dateTime, duration, rs } from "@/components/app/ui"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { useAuthStore } from "@/lib/auth-store"
import { useLoad } from "@/lib/use-load"

export default function SessionsPage() {
  return (
    <AppShell>
      <Sessions />
    </AppShell>
  )
}

function Sessions() {
  const role = useAuthStore((s) => s.role)!
  const host = role === "HOST"
  const { data, error, loading, reload } = useLoad(api.getSessions, 10_000)

  const header = (
    <PageHeader
      title="Sessions"
      description={host ? "Every session that has run on your GPUs." : "Every GPU you've rented. Running sessions show their SSH details."}
    />
  )
  if (loading) return <>{header}<Skeleton /></>
  if (!data) return <>{header}<LoadError message={error ?? ""} onRetry={reload} /></>

  const live = data.filter((s) => s.status === "ACTIVE" || s.status === "PENDING")
  const past = data.filter((s) => !live.includes(s))

  if (data.length === 0)
    return (
      <>
        {header}
        <Empty
          title="No sessions yet"
          body={host ? "When someone rents one of your GPUs, it shows up here." : "Rent a GPU to start your first session."}
          action={!host && <Button asChild><Link href="/marketplace">Rent a GPU</Link></Button>}
        />
      </>
    )

  return (
    <>
      {header}
      {error && <div className="mb-6"><LoadError message={error} onRetry={reload} /></div>}

      {live.length > 0 && (
        <div className="space-y-4">
          {live.map((s) => <SessionCard key={s.id} session={s} role={role} onChange={reload} />)}
        </div>
      )}

      {past.length > 0 && (
        <Section title="Past sessions">
          <Table
            head={[
              { label: "GPU" },
              { label: host ? "Renter" : "Host" },
              { label: "Started" },
              { label: "Ran for", right: true },
              { label: host ? "Earned" : "Cost", right: true },
              { label: "Status" },
            ]}
          >
            {past.map((s) => (
              <tr key={s.id} className="hover:bg-graphite">
                <td className="px-5 py-3.5 font-medium">{s.gpu_name}</td>
                <td className="px-5 py-3.5 text-ash">{host ? s.renter_name : s.host_name}</td>
                <td className="px-5 py-3.5 text-ash">{dateTime(s.start_time ?? s.created_at)}</td>
                <td className="px-5 py-3.5 text-right font-mono tabular-nums">{s.start_time ? duration(s.session_duration) : "—"}</td>
                <td className="px-5 py-3.5 text-right font-mono tabular-nums">{rs(s.total_cost)}</td>
                <td className="px-5 py-3.5"><StatusBadge status={s.status} /></td>
              </tr>
            ))}
          </Table>
        </Section>
      )}
    </>
  )
}
