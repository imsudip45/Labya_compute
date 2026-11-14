"use client"

import { useMemo, useState } from "react"
import { Search } from "lucide-react"
import { AppShell } from "@/components/app/shell"
import { RentDialog } from "@/components/app/rent-dialog"
import { Empty, LoadError, PageHeader, Skeleton, Table, rs } from "@/components/app/ui"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api"
import { useLoad } from "@/lib/use-load"
import { cn } from "@/lib/utils"

const VRAM = [
  { id: "all", label: "All", test: () => true },
  { id: "low", label: "< 16 GB", test: (m: number) => m < 16 },
  { id: "mid", label: "16–24 GB", test: (m: number) => m >= 16 && m < 24 },
  { id: "high", label: "24 GB+", test: (m: number) => m >= 24 },
]

const SORT = {
  price: { label: "Lowest price", fn: (a: { gpu_price: number }, b: { gpu_price: number }) => a.gpu_price - b.gpu_price },
  vram: { label: "Most VRAM", fn: (a: { gpu_memory: number }, b: { gpu_memory: number }) => b.gpu_memory - a.gpu_memory },
}

export default function MarketplacePage() {
  return (
    <AppShell only="RENTER">
      <Marketplace />
    </AppShell>
  )
}

function Marketplace() {
  const { data, error, loading, reload } = useLoad(api.getAvailableGPUs, 15_000)
  const [query, setQuery] = useState("")
  const [vram, setVram] = useState("all")
  const [sort, setSort] = useState<keyof typeof SORT>("price")

  const gpus = useMemo(() => {
    const q = query.trim().toLowerCase()
    const test = VRAM.find((v) => v.id === vram)!.test
    return (data ?? [])
      .filter((g) => !q || [g.gpu_name, g.gpu_model, g.gpu_location, g.host_name].some((s) => s?.toLowerCase().includes(q)))
      .filter((g) => test(g.gpu_memory))
      .sort(SORT[sort].fn)
  }, [data, query, vram, sort])

  return (
    <>
      <PageHeader title="Rent a GPU" description="These GPUs are online and free right now. Prices are per hour." />

      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Filter by VRAM">
          {VRAM.map((v) => (
            <button
              key={v.id}
              aria-pressed={vram === v.id}
              onClick={() => setVram(v.id)}
              className={cn("rounded-sm border px-3 py-1.5 text-caption transition-colors", vram === v.id ? "border-neon-glow text-whiteout" : "border-graphite-light text-ash hover:text-whiteout")}
            >
              {v.label}
            </button>
          ))}
          <span className="mx-2 h-5 w-px bg-graphite-light" aria-hidden />
          {(Object.keys(SORT) as (keyof typeof SORT)[]).map((k) => (
            <button
              key={k}
              aria-pressed={sort === k}
              onClick={() => setSort(k)}
              className={cn("rounded-sm border px-3 py-1.5 text-caption transition-colors", sort === k ? "border-neon-glow text-whiteout" : "border-graphite-light text-ash hover:text-whiteout")}
            >
              {SORT[k].label}
            </button>
          ))}
        </div>
        <label className="relative md:w-72">
          <span className="sr-only">Search GPUs</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-pewter" aria-hidden />
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search model, location or host" className="pl-9" />
        </label>
      </div>

      {loading ? (
        <Skeleton rows={4} />
      ) : !data ? (
        <LoadError message={error ?? ""} onRetry={reload} />
      ) : gpus.length === 0 ? (
        <Empty
          title={data.length ? "No GPUs match these filters" : "No GPUs are free right now"}
          body={data.length ? "Choose a different VRAM range or clear the search." : "GPUs appear here when a host's agent is running and the GPU isn't rented. This list refreshes on its own."}
        />
      ) : (
        <Table head={[{ label: "GPU" }, { label: "VRAM", right: true }, { label: "Location" }, { label: "Host" }, { label: "Price", right: true }, { label: "" }]}>
          {gpus.map((g) => (
            <tr key={g.id} className="transition-colors hover:bg-graphite">
              <td className="px-5 py-4">
                <div className="font-medium">{g.gpu_name}</div>
                {g.gpu_model && <div className="font-mono text-caption text-pewter">{g.gpu_model}</div>}
              </td>
              <td className="px-5 py-4 text-right font-mono tabular-nums">{g.gpu_memory} GB</td>
              <td className="px-5 py-4 text-ash">{g.gpu_location}</td>
              <td className="px-5 py-4 text-ash">{g.host_name}</td>
              <td className="px-5 py-4 text-right font-mono tabular-nums">{rs(g.gpu_price)}<span className="text-ash">/hr</span></td>
              <td className="px-5 py-4 text-right">
                <RentDialog gpu={g}><Button size="sm">Rent GPU</Button></RentDialog>
              </td>
            </tr>
          ))}
        </Table>
      )}
    </>
  )
}
