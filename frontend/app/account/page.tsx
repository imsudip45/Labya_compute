"use client"

import { useRouter } from "next/navigation"
import { AppShell } from "@/components/app/shell"
import { PageHeader, Panel } from "@/components/app/ui"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/lib/auth-store"

export default function AccountPage() {
  return (
    <AppShell>
      <Account />
    </AppShell>
  )
}

function Account() {
  const { user, role, signOut } = useAuthStore()
  const router = useRouter()
  const rows: [string, string][] = [
    ["Name", [user?.first_name, user?.last_name].filter(Boolean).join(" ") || "—"],
    ["Email", user?.email ?? "—"],
    ["Account type", role === "HOST" ? "Host: you list GPUs and earn from sessions" : "Renter: you rent GPUs and pay per hour"],
  ]
  return (
    <>
      <PageHeader title="Account" />
      <Panel>
        <dl className="divide-y divide-graphite-light text-body-sm">
          {rows.map(([k, v]) => (
            <div key={k} className="grid gap-1 px-5 py-4 sm:grid-cols-[180px_1fr]">
              <dt className="text-ash">{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      </Panel>
      <p className="mt-4 text-body-sm text-ash">
        To change your name or email, contact support. Changing them from here isn't available yet.
      </p>
      <div className="mt-8">
        <Button variant="outline" onClick={async () => { await signOut(); router.replace("/login") }}>Log out</Button>
      </div>
    </>
  )
}
