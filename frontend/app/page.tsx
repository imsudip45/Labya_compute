"use client"

import { useEffect, useMemo, useState, type ReactNode } from "react"
import Link from "next/link"
import { useAuthStore } from "@/lib/auth-store"
import { api } from "@/lib/api"
import type { GPU } from "@/lib/types"
import { RentDialog } from "@/components/app/rent-dialog"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Cpu, Download, Menu, Search, X } from "lucide-react"

// Copy and styling follow CLAUDE.md ("Design system", "Writing for the UI").

const NAV = [
  { href: "#gpus", label: "GPUs" },
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#hosts", label: "Hosting" },
  { href: "#faq", label: "FAQ" },
]

const VRAM_FILTERS = [
  { id: "all", label: "All" },
  { id: "low", label: "< 16 GB" },
  { id: "mid", label: "16–24 GB" },
  { id: "high", label: "24 GB+" },
] as const

const FEATURES = [
  { title: "Your own container", body: "Each session runs in a separate Docker container on the host's machine, away from the host's files." },
  { title: "Plain SSH access", body: "Hosts connect out through Cloudflare, so neither side needs port forwarding. You connect with your usual SSH client and cloudflared." },
  { title: "Nothing to install", body: "The host's agent builds the container and opens the tunnel. You get an SSH command when it's ready." },
  { title: "Pay for running time", body: "Cost is the hourly price times how long the session ran, charged from your wallet when it ends." },
  { title: "GPU metrics", body: "The agent reports GPU utilization, memory use and temperature while your session runs." },
  { title: "New password each session", body: "Every session gets a newly generated password and a fresh container. Nothing carries over." },
]

const STEPS = [
  { title: "Add funds", body: "Create a renter account and add money to your wallet." },
  { title: "Rent a GPU", body: "Pick a GPU below. The host's agent starts your container and opens the tunnel." },
  { title: "Connect over SSH", body: "Copy the SSH command from your session page. End the session when you're done." },
]

const HOST_POINTS = [
  ["You set the price", "Choose your hourly rate in NPR and change it when you want."],
  ["Renters stay in a container", "Each session runs in Docker and the container is removed when it ends."],
  ["No port forwarding", "The agent connects out through Cloudflare, so your router stays as it is."],
  ["What you need", "Windows 10 or 11, an NVIDIA GPU, WSL2 and Docker Desktop."],
]

const FAQ = [
  { q: "How do I connect to a GPU I rent?", a: "When the host's agent has started your container, your session page shows an SSH command and a password. Run the command in any terminal on Linux, macOS or Windows." },
  { q: "How is the cost calculated?", a: "The GPU's hourly price multiplied by the time the session was running. It is charged from your wallet when the session ends." },
  { q: "What do I need to host a GPU?", a: "A Windows 10 or 11 PC with an NVIDIA GPU, WSL2 and Docker Desktop. The desktop agent checks each of these and helps you set them up." },
  { q: "Can a renter access the rest of my PC?", a: "Renters get a shell inside a Docker container started for their session. The container is removed when the session ends." },
  { q: "Which currency do you use?", a: "Nepalese rupees (NPR). Prices on the marketplace are per hour." },
]

const pill = "inline-flex items-center justify-center gap-2 rounded-full text-body-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-glow focus-visible:ring-offset-2 focus-visible:ring-offset-blackout"
const primaryCls = `${pill} bg-whiteout px-7 py-3 text-graphite-deep hover:bg-cloud`
const secondaryCls = `${pill} border border-graphite-light px-[18px] py-3 text-whiteout hover:border-ash`

function ButtonLink({ href, variant = "primary", children, download }: { href: string; variant?: "primary" | "secondary"; children: ReactNode; download?: boolean }) {
  const cls = variant === "primary" ? primaryCls : secondaryCls
  return href.startsWith("/") && !download ? (
    <Link href={href} className={cls}>{children}</Link>
  ) : (
    <a href={href} className={cls} download={download}>{children}</a>
  )
}


function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5 text-whiteout">
      <span className="grid h-7 w-7 place-items-center rounded-sm bg-whiteout">
        <Cpu className="h-4 w-4 text-blackout" strokeWidth={2.25} />
      </span>
      <span className="text-body font-medium">Labhya Compute</span>
    </Link>
  )
}

// Abstract "data stream" lines behind the hero. Deterministic so server and client render match.
function DataLines() {
  const lines = Array.from({ length: 140 }, (_, i) => {
    const h = 0.15 + 0.85 * Math.abs(Math.sin(i * 0.37) * Math.cos(i * 0.11))
    return { x: i * 10 + 5, h: Math.round(h * 220), bright: i % 9 === 0 || i % 13 === 0 }
  })
  return (
    <svg className="pointer-events-none absolute inset-x-0 bottom-0 h-[220px] w-full" viewBox="0 0 1400 220" preserveAspectRatio="none" aria-hidden>
      {lines.map((l) => (
        <line key={l.x} x1={l.x} x2={l.x} y1={220} y2={220 - l.h} stroke={l.bright ? "var(--neon-glow)" : "var(--neon-muted)"} strokeWidth={1} opacity={l.bright ? 0.9 : 0.55} />
      ))}
    </svg>
  )
}

function TerminalBlock() {
  const prompt = <span className="text-neon-glow">labuser@session:~$ </span>
  return (
    <div className="min-w-0 rounded-sm border border-graphite-light bg-graphite-deep text-left">
      <pre className="overflow-x-auto p-6 font-mono text-body-sm text-whiteout">
        <span className="text-pewter">$ </span>ssh labuser@sess-5f0e67a1b2c3.labhya.dev{"\n"}
        {prompt}nvidia-smi --query-gpu=name,memory.total --format=csv{"\n"}
        <span className="text-pewter">name, memory.total [MiB]</span>{"\n"}
        NVIDIA GeForce RTX 4090, 24564 MiB{"\n"}
        {prompt}python train.py --epochs 20{"\n"}
        <span className="text-pewter">epoch 1/20  loss 0.412</span>{"\n"}
        {prompt}<span className="inline-block h-4 w-2 translate-y-0.5 animate-pulse bg-neon-glow" />
      </pre>
    </div>
  )
}

export default function HomePage() {
  const { isAuthenticated } = useAuthStore()
  const [menuOpen, setMenuOpen] = useState(false)

  const [gpus, setGpus] = useState<GPU[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [query, setQuery] = useState("")
  const [vram, setVram] = useState<(typeof VRAM_FILTERS)[number]["id"]>("all")

  useEffect(() => {
    api
      .getAvailableGPUs()
      .then((data) => setGpus(Array.isArray(data) ? data : []))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return gpus
      .filter((g) => !q || [g.gpu_name, g.gpu_model, g.gpu_location].some((s) => s?.toLowerCase().includes(q)))
      .filter((g) =>
        vram === "low" ? g.gpu_memory < 16 : vram === "mid" ? g.gpu_memory >= 16 && g.gpu_memory < 24 : vram === "high" ? g.gpu_memory >= 24 : true,
      )
      .sort((a, b) => a.gpu_price - b.gpu_price)
  }, [gpus, query, vram])

  const has = !loading && !error && gpus.length > 0
  const stats = [
    { label: "GPUs online", value: loading || error ? "—" : String(gpus.length) },
    { label: "Lowest price", value: has ? `Rs ${Math.min(...gpus.map((g) => g.gpu_price))}/hr` : "—" },
    { label: "Most VRAM", value: has ? `${Math.max(...gpus.map((g) => g.gpu_memory))} GB` : "—" },
    { label: "Host locations", value: loading || error ? "—" : String(new Set(gpus.map((g) => g.gpu_location)).size) },
  ]

  const wrap = "mx-auto max-w-[1200px] px-4 sm:px-6"

  return (
    <div className="min-h-screen bg-blackout text-whiteout">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-graphite-light bg-blackout/80 backdrop-blur">
        <div className={`${wrap} flex h-16 items-center justify-between`}>
          <Logo />
          <nav className="hidden items-center gap-8 text-body-sm text-ash lg:flex" aria-label="Main">
            {NAV.map((n) => (
              <a key={n.href} href={n.href} className="transition hover:text-whiteout">{n.label}</a>
            ))}
          </nav>
          <div className="hidden items-center gap-3 lg:flex">
            {isAuthenticated ? (
              <ButtonLink href="/dashboard">Dashboard</ButtonLink>
            ) : (
              <>
                <ButtonLink href="/login" variant="secondary">Log in</ButtonLink>
                <ButtonLink href="/register/renter">Sign up</ButtonLink>
              </>
            )}
          </div>
          <button
            className="grid h-10 w-10 place-items-center rounded-sm text-cloud hover:bg-graphite lg:hidden"
            onClick={() => setMenuOpen((o) => !o)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
        {menuOpen && (
          <div className="border-t border-graphite-light px-4 pb-5 pt-2 lg:hidden">
            {NAV.map((n) => (
              <a key={n.href} href={n.href} onClick={() => setMenuOpen(false)} className="block py-2.5 text-body-sm text-cloud">{n.label}</a>
            ))}
            <div className="mt-3 flex gap-3">
              {isAuthenticated ? (
                <ButtonLink href="/dashboard">Dashboard</ButtonLink>
              ) : (
                <>
                  <ButtonLink href="/login" variant="secondary">Log in</ButtonLink>
                  <ButtonLink href="/register/renter">Sign up</ButtonLink>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden pb-[220px]">
        <div className={`${wrap} relative z-10 pt-24 text-center sm:pt-32`}>
          <h1 className="mx-auto max-w-4xl text-heading-lg font-medium sm:text-display">Rent a GPU by the hour.</h1>
          <p className="mx-auto mt-6 max-w-2xl text-subheading text-ash">
            Pick a GPU from a host on the Labhya network. You get a Docker container and an SSH command, and you pay for the time it runs.
          </p>
          <div className="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
            <ButtonLink href="#gpus">Browse GPUs</ButtonLink>
            <ButtonLink href="/register/host" variant="secondary">Host your GPU</ButtonLink>
          </div>
          <div className="mx-auto mt-20 max-w-3xl">
            <TerminalBlock />
          </div>
        </div>
        <DataLines />
      </section>

      {/* Live stats */}
      <section className={`${wrap} pt-24`} aria-label="Marketplace right now">
        <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-sm border border-graphite-light bg-graphite-light md:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="flex flex-col bg-blackout p-6">
              <dt className="order-2 mt-1 text-body-sm text-ash">{s.label}</dt>
              <dd className="text-heading-sm font-medium tabular-nums">{s.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* GPUs */}
      <section id="gpus" className="scroll-mt-16 py-24 sm:py-32">
        <div className={wrap}>
          <div className="mb-12 max-w-2xl">
            <h2 className="text-heading font-medium sm:text-heading-lg">GPUs online right now</h2>
            <p className="mt-4 text-body text-ash">Hosts set their own prices. All prices are per hour in NPR.</p>
          </div>

          <div className="overflow-hidden rounded-sm border border-graphite-light bg-graphite-deep">
            <div className="flex flex-col gap-3 border-b border-graphite-light p-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex flex-wrap gap-1" role="group" aria-label="Filter by VRAM">
                {VRAM_FILTERS.map((f) => (
                  <button
                    key={f.id}
                    aria-pressed={vram === f.id}
                    onClick={() => setVram(f.id)}
                    className={`rounded-sm border px-3 py-1.5 font-mono text-caption transition ${
                      vram === f.id ? "border-neon-glow text-whiteout" : "border-transparent text-ash hover:text-whiteout"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
              <label className="relative sm:w-72">
                <span className="sr-only">Search GPUs</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-pewter" aria-hidden />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by model or location"
                  className="h-9 w-full rounded-sm border border-graphite-light bg-graphite pl-9 pr-3 text-body-sm text-whiteout placeholder:text-pewter focus:border-neon-glow focus:outline-none"
                />
              </label>
            </div>

            {loading ? (
              <div className="divide-y divide-graphite-light" aria-busy>
                {[0, 1, 2].map((i) => (
                  <div key={i} className="flex animate-pulse items-center gap-4 px-6 py-5">
                    <div className="h-8 w-8 rounded-sm bg-graphite" />
                    <div className="h-4 w-48 rounded-sm bg-graphite" />
                    <div className="ml-auto h-4 w-20 rounded-sm bg-graphite" />
                  </div>
                ))}
              </div>
            ) : visible.length === 0 ? (
              <div className="px-6 py-16 text-center">
                <p className="text-body font-medium">
                  {error ? "Couldn't load GPUs" : gpus.length ? "No GPUs match these filters" : "No GPUs are online right now"}
                </p>
                <p className="mt-2 text-body-sm text-ash">
                  {error
                    ? "The marketplace didn't respond. Refresh the page to try again."
                    : gpus.length
                      ? "Choose a different VRAM range or clear the search."
                      : "Hosts come online when their agent is running. Check back later, or host your own GPU."}
                </p>
              </div>
            ) : (
              <table className="w-full text-left text-body-sm">
                <thead className="hidden text-caption text-ash md:table-header-group">
                  <tr className="border-b border-graphite-light">
                    <th className="px-6 py-3 font-normal">GPU</th>
                    <th className="px-6 py-3 text-right font-normal">VRAM</th>
                    <th className="px-6 py-3 font-normal">Location</th>
                    <th className="px-6 py-3 text-right font-normal">Price</th>
                    <th className="px-6 py-3"><span className="sr-only">Action</span></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-graphite-light">
                  {visible.map((gpu) => (
                    <tr key={gpu.id} className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 px-6 py-4 transition hover:bg-graphite md:table-row md:p-0">
                      <td className="md:px-6 md:py-4">
                        <div className="font-medium">{gpu.gpu_name}</div>
                        {gpu.gpu_model && <div className="font-mono text-caption text-pewter">{gpu.gpu_model}</div>}
                      </td>
                      <td className="order-3 font-mono tabular-nums text-cloud md:px-6 md:py-4 md:text-right">
                        <span className="text-ash md:hidden">VRAM </span>{gpu.gpu_memory} GB
                      </td>
                      <td className="order-4 text-ash md:px-6 md:py-4">{gpu.gpu_location}</td>
                      <td className="order-2 text-right font-mono tabular-nums md:px-6 md:py-4">
                        Rs {gpu.gpu_price}<span className="text-ash">/hr</span>
                      </td>
                      <td className="order-5 col-span-2 pt-2 md:px-6 md:py-4 md:text-right">
                        {isAuthenticated ? (
                          <RentDialog gpu={gpu}>
                            <button className={`${pill} w-full bg-whiteout px-5 py-2 text-graphite-deep hover:bg-cloud md:w-auto`}>Rent GPU</button>
                          </RentDialog>
                        ) : (
                          <Link href="/login?next=/" className={`${pill} w-full border border-graphite-light px-5 py-2 text-whiteout hover:border-ash md:w-auto`}>
                            Log in to rent
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="scroll-mt-16 py-24 sm:py-32">
        <div className={wrap}>
          <div className="mb-12 max-w-2xl">
            <h2 className="text-heading font-medium sm:text-heading-lg">What you get with each session</h2>
          </div>
          <dl className="grid gap-x-12 sm:grid-cols-2">
            {FEATURES.map(({ title, body }) => (
              <div key={title} className="border-t border-graphite-light py-6">
                <dt className="text-subheading font-medium">{title}</dt>
                <dd className="mt-2 text-body-sm text-ash">{body}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="scroll-mt-16 py-24 sm:py-32">
        <div className={`${wrap} grid gap-12 lg:grid-cols-2 lg:items-start`}>
          <div>
            <h2 className="text-heading font-medium sm:text-heading-lg">From sign-up to SSH in three steps</h2>
          </div>
          <ol className="space-y-px overflow-hidden rounded-sm border border-graphite-light bg-graphite-light">
            {STEPS.map((s, i) => (
              <li key={s.title} className="flex gap-6 bg-graphite-deep p-6">
                <span className="text-subheading text-ash">{i + 1}</span>
                <div>
                  <h3 className="text-subheading font-medium">{s.title}</h3>
                  <p className="mt-1 text-body-sm text-ash">{s.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Hosting */}
      <section id="hosts" className="scroll-mt-16 py-24 sm:py-32">
        <div className={`${wrap} grid gap-12 lg:grid-cols-2 lg:items-start`}>
          <div>
            <h2 className="text-heading font-medium sm:text-heading-lg">Earn from your GPU when you're not using it</h2>
            <p className="mt-4 text-body text-ash">
              Install the desktop agent, set an hourly price, and keep the agent running. When someone rents your GPU, the earnings go to your host wallet.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <ButtonLink href="/register/host">Become a host</ButtonLink>
              <ButtonLink href="/downloads/LabhyaComputeAgentSetup.exe" variant="secondary" download>
                <Download className="h-4 w-4" aria-hidden /> Download agent
              </ButtonLink>
            </div>
            <p className="mt-4 text-caption text-pewter">
              Windows installer. Also available as a{" "}
              <a href="/downloads/LabhyaComputeAgent.exe" download className="text-cloud underline decoration-graphite-light underline-offset-4 hover:decoration-whiteout">portable .exe</a>.
            </p>
          </div>
          <ul className="space-y-px overflow-hidden rounded-sm border border-graphite-light bg-graphite-light">
            {HOST_POINTS.map(([t, d]) => (
              <li key={t} className="bg-graphite-deep p-6">
                <div>
                  <p className="font-medium">{t}</p>
                  <p className="mt-1 text-body-sm text-ash">{d}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="scroll-mt-16 py-24 sm:py-32">
        <div className="mx-auto max-w-3xl px-4 sm:px-6">
          <h2 className="mb-10 text-heading font-medium">Common questions</h2>
          <Accordion type="single" collapsible className="border-y border-graphite-light">
            {FAQ.map((f, i) => (
              <AccordionItem key={f.q} value={`q${i}`} className="border-graphite-light">
                <AccordionTrigger className="py-5 text-left text-body font-medium hover:no-underline">{f.q}</AccordionTrigger>
                <AccordionContent className="pb-5 text-body-sm text-ash">{f.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>

      {/* Closing */}
      <section className="py-24 sm:py-32">
        <div className={`${wrap} text-center`}>
          <h2 className="text-heading font-medium sm:text-heading-lg">Rent a GPU or list yours</h2>
          <p className="mx-auto mt-4 max-w-xl text-body text-ash">Accounts are free. You only pay for the sessions you run.</p>
          <div className="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
            <ButtonLink href={isAuthenticated ? "/dashboard" : "/register/renter"}>{isAuthenticated ? "Dashboard" : "Create account"}</ButtonLink>
            <ButtonLink href="/register/host" variant="secondary">Host your GPU</ButtonLink>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-graphite-light">
        <div className={`${wrap} grid gap-10 py-14 md:grid-cols-[1.5fr_1fr_1fr_1fr]`}>
          <div>
            <Logo />
            <p className="mt-4 max-w-xs text-body-sm text-ash">Hourly GPU rental from independent hosts in Nepal.</p>
          </div>
          {[
            { title: "Renters", links: [["GPUs", "#gpus"], ["How it works", "#how-it-works"], ["FAQ", "#faq"]] },
            { title: "Hosts", links: [["Become a host", "/register/host"], ["Download agent", "/downloads/LabhyaComputeAgentSetup.exe"]] },
            { title: "Account", links: [["Log in", "/login"], ["Sign up", "/register/renter"], ["Dashboard", "/dashboard"]] },
          ].map((col) => (
            <div key={col.title}>
              <p className="text-body-sm font-medium text-whiteout">{col.title}</p>
              <ul className="mt-4 space-y-2.5 text-body-sm text-cloud">
                {col.links.map(([label, href]) => (
                  <li key={label}><a href={href} className="transition hover:text-whiteout">{label}</a></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className={`${wrap} border-t border-graphite-light py-6 text-caption text-pewter`}>
          © {new Date().getFullYear()} Labhya Compute
        </div>
      </footer>
    </div>
  )
}
