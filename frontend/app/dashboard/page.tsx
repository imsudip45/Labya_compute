"use client"

import Link from "next/link"
import { Download } from "lucide-react"
import { AppShell } from "@/components/app/shell"
import { SessionCard } from "@/components/app/session-card"
import { Empty, LoadError, PageHeader, Section, Skeleton, Stats, rs } from "@/components/app/ui"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { useAuthStore } from "@/lib/auth-store"
import { useLoad } from "@/lib/use-load"
import { AGENT_INSTALLER } from "@/lib/downloads"

const load = () => Promise.all([api.getDashboardStats(), api.getWallet(), api.getSessions()])

export default function OverviewPage() {
  return (
    <AppShell>
      <Overview />
    </AppShell>
  )
}

function Overview() {
  const role = useAuthStore((s) => s.role)!
  const { data, error, loading, reload } = useLoad(load, 10_000)
  const host = role === "HOST"

  const header = (
    <PageHeader
      title="Overview"
      action={
        host ? (
          <Button variant="outline" asChild><Link href="/gpus">Manage GPUs</Link></Button>
        ) : (
          <Button asChild><Link href="/marketplace">Rent a GPU</Link></Button>
        )
      }
    />
  )

  if (loading) return <>{header}<Skeleton rows={2} /></>
  if (!data) return <>{header}<LoadError message={error ?? ""} onRetry={reload} /></>

  const [stats, wallet, sessions] = data
  const live = sessions.filter((s) => s.status === "ACTIVE" || s.status === "PENDING")
  const balance = Number(wallet.balance)

  return (
    <>
      {header}
      {error && <div className="mb-6"><LoadError message={error} onRetry={reload} /></div>}

      <Stats
        items={
          host
            ? [
                { label: "Wallet balance", value: rs(balance) },
                { label: "Earned today", value: rs(stats.todaysEarnings) },
                { label: "GPUs available to rent", value: `${stats.availableGPUs ?? 0} of ${stats.totalGPUs ?? 0}` },
                { label: "Sessions running", value: stats.activeSessions ?? 0 },
              ]
            : [
                { label: "Wallet balance", value: rs(balance) },
                { label: "Sessions running", value: stats.activeSessions ?? 0 },
                { label: "Sessions so far", value: stats.totalSessions ?? 0 },
                { label: "Total spent", value: rs(stats.totalSpent) },
              ]
        }
      />

      {!host && balance <= 0 && (
        <p className="mt-4 text-body-sm text-ash">
          Your wallet is empty. <Link href="/wallet" className="text-whiteout underline decoration-graphite-light underline-offset-4 hover:decoration-whiteout">Add funds</Link> before you rent a GPU.
        </p>
      )}

      {host && (stats.totalGPUs ?? 0) === 0 && (
        <Section title="List your first GPU">
          <Empty
            title="You haven't listed a GPU yet"
            body="Install the desktop agent on the PC with your GPU and log in with this account. The agent detects your GPU and lists it here."
            action={
              <Button asChild>
                <a href={AGENT_INSTALLER} download><Download aria-hidden /> Download agent for Windows</a>
              </Button>
            }
          />
        </Section>
      )}

      <Section title={host ? "Sessions on your GPUs" : "Your running sessions"} action={sessions.length > 0 && <Link href="/sessions" className="text-body-sm text-ash hover:text-whiteout">All sessions</Link>}>
        {live.length === 0 ? (
          <Empty
            title="Nothing running right now"
            body={host ? "When someone rents one of your GPUs, the session shows up here." : "Rent a GPU and its SSH details will show up here."}
            action={!host && <Button variant="outline" asChild><Link href="/marketplace">Browse GPUs</Link></Button>}
          />
        ) : (
          <div className="space-y-4">
            {live.map((s) => <SessionCard key={s.id} session={s} role={role} onChange={reload} />)}
          </div>
        )}
      </Section>
    </>
  )
}
