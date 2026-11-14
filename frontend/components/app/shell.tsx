"use client"

import { useEffect, useState, type ReactNode } from "react"
import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { Cpu, LogOut, Menu, X } from "lucide-react"
import { useAuthStore } from "@/lib/auth-store"
import type { UserRole } from "@/lib/types"
import { cn } from "@/lib/utils"

const NAV: Record<UserRole, { href: string; label: string }[]> = {
  RENTER: [
    { href: "/dashboard", label: "Overview" },
    { href: "/marketplace", label: "Rent a GPU" },
    { href: "/sessions", label: "Sessions" },
    { href: "/wallet", label: "Wallet" },
    { href: "/account", label: "Account" },
  ],
  HOST: [
    { href: "/dashboard", label: "Overview" },
    { href: "/gpus", label: "My GPUs" },
    { href: "/sessions", label: "Sessions" },
    { href: "/wallet", label: "Wallet" },
    { href: "/account", label: "Account" },
  ],
}

/**
 * Wraps every logged-in page. Sends logged-out visitors to /login and
 * people with the wrong role (e.g. a renter opening /gpus) to /dashboard.
 */
export function AppShell({ only, children }: { only?: UserRole; children: ReactNode }) {
  const { isAuthenticated, role, user, signOut: revokeAndForget } = useAuthStore()
  const router = useRouter()
  const pathname = usePathname()
  const [mounted, setMounted] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => setMounted(true), [])
  const allowed = isAuthenticated && role && (!only || only === role)
  useEffect(() => {
    if (!mounted) return
    if (!isAuthenticated || !role) router.replace(`/login?next=${encodeURIComponent(pathname)}`)
    else if (only && only !== role) router.replace("/dashboard")
  }, [mounted, isAuthenticated, role, only, pathname, router])
  useEffect(() => setOpen(false), [pathname])

  // Auth state lives in localStorage, so render nothing until the client has read it.
  if (!mounted || !allowed) return <div className="min-h-screen bg-blackout" />

  const signOut = async () => {
    await revokeAndForget()
    router.replace("/login")
  }
  const name = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.email

  const nav = (
    <nav className="flex flex-col gap-0.5" aria-label="App">
      {NAV[role].map((n) => {
        const active = pathname === n.href
        return (
          <Link
            key={n.href}
            href={n.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "rounded-sm px-3 py-2 text-body-sm transition-colors",
              active ? "bg-graphite text-whiteout" : "text-ash hover:bg-graphite/60 hover:text-whiteout",
            )}
          >
            {n.label}
          </Link>
        )
      })}
    </nav>
  )

  const account = (
    <div className="border-t border-graphite-light pt-4">
      <p className="truncate text-body-sm">{name}</p>
      <p className="truncate text-caption text-ash">{role === "HOST" ? "Host" : "Renter"} · {user?.email}</p>
      <button onClick={signOut} className="mt-3 inline-flex items-center gap-2 text-body-sm text-ash hover:text-whiteout">
        <LogOut className="h-4 w-4" aria-hidden /> Log out
      </button>
    </div>
  )

  const logo = (
    <Link href="/dashboard" className="flex items-center gap-2.5">
      <span className="grid h-7 w-7 place-items-center rounded-sm bg-whiteout">
        <Cpu className="h-4 w-4 text-blackout" strokeWidth={2.25} />
      </span>
      <span className="text-body font-medium">Labhya Compute</span>
    </Link>
  )

  return (
    <div className="min-h-screen bg-blackout text-whiteout">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col justify-between border-r border-graphite-light bg-depth p-4 lg:flex">
        <div>
          <div className="mb-8 px-2 pt-1">{logo}</div>
          {nav}
        </div>
        {account}
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-graphite-light bg-blackout/90 px-4 backdrop-blur lg:hidden">
        {logo}
        <button
          onClick={() => setOpen((o) => !o)}
          className="grid h-9 w-9 place-items-center rounded-sm text-cloud hover:bg-graphite"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>
      {open && (
        <div className="fixed inset-x-0 top-14 bottom-0 z-30 flex flex-col justify-between overflow-y-auto bg-depth p-4 lg:hidden">
          {nav}
          {account}
        </div>
      )}

      <main className="lg:pl-60">
        <div className="mx-auto max-w-[1100px] px-4 py-8 sm:px-8 sm:py-10">{children}</div>
      </main>
    </div>
  )
}
