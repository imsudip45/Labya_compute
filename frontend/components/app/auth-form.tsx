"use client"

import { useState, type ComponentProps, type FormEvent } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Cpu } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAuthStore } from "@/lib/auth-store"
import type { UserRole } from "@/lib/types"

type Mode = "login" | UserRole

const COPY: Record<Mode, { title: string; body: string; submit: string }> = {
  login: { title: "Log in", body: "Use the email and password you signed up with.", submit: "Log in" },
  RENTER: { title: "Create a renter account", body: "Rent GPUs by the hour and connect over SSH.", submit: "Create account" },
  HOST: { title: "Create a host account", body: "List your GPU and earn when someone rents it.", submit: "Create account" },
}

// Only follow same-site paths after login, never full URLs.
function nextPath() {
  const next = new URLSearchParams(window.location.search).get("next")
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard"
}

export function AuthForm({ mode }: { mode: Mode }) {
  const { login, register } = useAuthStore()
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const copy = COPY[mode]

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const f = new FormData(e.currentTarget)
    const email = String(f.get("email")).trim()
    const password = String(f.get("password"))
    setError(null)
    if (mode !== "login" && password.length < 8) return setError("Use at least 8 characters for your password.")
    setBusy(true)
    try {
      if (mode === "login") await login(email, password)
      else await register(String(f.get("name")).trim(), email, password, mode)
      router.replace(mode === "login" ? nextPath() : "/dashboard")
    } catch (err) {
      const msg = err instanceof Error ? err.message : ""
      setError(
        msg === "Invalid email or password" ? "That email and password don't match an account."
        : msg === "User already exists" ? "An account with this email already exists. Log in instead."
        : msg || "Something went wrong. Try again.",
      )
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-blackout px-4 text-whiteout">
      <header className="mx-auto flex h-16 w-full max-w-[1200px] items-center">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid h-7 w-7 place-items-center rounded-sm bg-whiteout">
            <Cpu className="h-4 w-4 text-blackout" strokeWidth={2.25} />
          </span>
          <span className="text-body font-medium">Labhya Compute</span>
        </Link>
      </header>

      <main className="flex flex-1 items-center justify-center py-12">
        <div className="w-full max-w-sm">
          <h1 className="text-heading font-medium">{copy.title}</h1>
          <p className="mt-2 text-body-sm text-ash">{copy.body}</p>

          <form onSubmit={submit} className="mt-8 space-y-5" noValidate={false}>
            {mode !== "login" && (
              <Field label="Full name" name="name" autoComplete="name" required />
            )}
            <Field label="Email" name="email" type="email" autoComplete="email" required />
            <Field
              label="Password"
              name="password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              hint={mode === "login" ? undefined : "At least 8 characters."}
              required
            />
            {error && <p role="alert" className="text-body-sm text-system-warning">{error}</p>}
            <Button type="submit" size="lg" className="w-full" disabled={busy}>
              {busy ? "Please wait…" : copy.submit}
            </Button>
          </form>

          <div className="mt-8 space-y-2 border-t border-graphite-light pt-6 text-body-sm text-ash">
            {mode === "login" ? (
              <>
                <p>New here? <Link href="/register/renter" className="text-whiteout underline decoration-graphite-light underline-offset-4 hover:decoration-whiteout">Create a renter account</Link></p>
                <p>Have a GPU to share? <Link href="/register/host" className="text-whiteout underline decoration-graphite-light underline-offset-4 hover:decoration-whiteout">Create a host account</Link></p>
              </>
            ) : (
              <>
                <p>Already have an account? <Link href="/login" className="text-whiteout underline decoration-graphite-light underline-offset-4 hover:decoration-whiteout">Log in</Link></p>
                <p>
                  {mode === "RENTER" ? "Want to share your GPU instead? " : "Want to rent GPUs instead? "}
                  <Link href={mode === "RENTER" ? "/register/host" : "/register/renter"} className="text-whiteout underline decoration-graphite-light underline-offset-4 hover:decoration-whiteout">
                    {mode === "RENTER" ? "Create a host account" : "Create a renter account"}
                  </Link>
                </p>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

function Field({ label, name, hint, ...props }: { label: string; name: string; hint?: string } & ComponentProps<"input">) {
  return (
    <div>
      <label htmlFor={name} className="mb-1.5 block text-body-sm">{label}</label>
      <Input id={name} name={name} {...props} />
      {hint && <p className="mt-1.5 text-caption text-pewter">{hint}</p>}
    </div>
  )
}
