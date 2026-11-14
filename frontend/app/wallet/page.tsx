"use client"

import { useState, type FormEvent } from "react"
import { AppShell } from "@/components/app/shell"
import { Empty, LoadError, PageHeader, Section, Skeleton, Stats, Table, dateTime, rs } from "@/components/app/ui"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useToast } from "@/hooks/use-toast"
import { api } from "@/lib/api"
import { useAuthStore } from "@/lib/auth-store"
import type { TransactionType } from "@/lib/types"
import { useLoad } from "@/lib/use-load"

const TYPE: Record<TransactionType, { label: string; sign: 1 | -1 }> = {
  DEPOSIT: { label: "Added funds", sign: 1 },
  WITHDRAWAL: { label: "Withdrawal", sign: -1 },
  RENTAL_PAYMENT: { label: "Session payment", sign: -1 },
  RENTAL_EARNING: { label: "Session earning", sign: 1 },
}

export default function WalletPage() {
  return (
    <AppShell>
      <WalletView />
    </AppShell>
  )
}

function WalletView() {
  const host = useAuthStore((s) => s.role) === "HOST"
  const { data: wallet, error, loading, reload } = useLoad(api.getWallet)

  const header = (
    <PageHeader
      title="Wallet"
      description={host ? "Earnings from sessions on your GPUs." : "Session costs are taken from this balance when a session ends."}
      action={wallet && <MoveFunds host={host} balance={Number(wallet.balance)} onDone={reload} />}
    />
  )
  if (loading) return <>{header}<Skeleton /></>
  if (!wallet) return <>{header}<LoadError message={error ?? ""} onRetry={reload} /></>

  const txs = wallet.transactions
  const sum = (t: TransactionType) => txs.filter((x) => x.transaction_type === t).reduce((a, x) => a + Number(x.amount), 0)

  return (
    <>
      {header}
      <Stats
        items={
          host
            ? [
                { label: "Balance", value: rs(wallet.balance) },
                { label: "Earned in total", value: rs(sum("RENTAL_EARNING")) },
              ]
            : [
                { label: "Balance", value: rs(wallet.balance) },
                { label: "Spent on sessions", value: rs(sum("RENTAL_PAYMENT")) },
              ]
        }
      />

      <Section title="History">
        {txs.length === 0 ? (
          <Empty
            title="No transactions yet"
            body={host ? "Earnings appear here when a renter ends a session on one of your GPUs." : "Funds you add and sessions you pay for appear here."}
          />
        ) : (
          <Table head={[{ label: "Date" }, { label: "Type" }, { label: "Details" }, { label: "Amount", right: true }]}>
            {txs.map((t) => {
              const type = TYPE[t.transaction_type] ?? { label: t.transaction_type, sign: 1 }
              return (
                <tr key={t.id} className="hover:bg-graphite">
                  <td className="whitespace-nowrap px-5 py-3.5 text-ash">{dateTime(t.created_at)}</td>
                  <td className="px-5 py-3.5">{type.label}</td>
                  <td className="px-5 py-3.5 text-ash">{t.description}</td>
                  <td className="px-5 py-3.5 text-right font-mono tabular-nums">
                    {type.sign > 0 ? "+" : "−"}{rs(t.amount)}
                  </td>
                </tr>
              )
            })}
          </Table>
        )}
      </Section>
    </>
  )
}

function MoveFunds({ host, balance, onDone }: { host: boolean; balance: number; onDone: () => void }) {
  const { toast } = useToast()
  const [open, setOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const amount = Number(new FormData(e.currentTarget).get("amount"))
    if (!(amount > 0)) return setError("Enter an amount above zero.")
    if (host && amount > balance) return setError(`You can withdraw up to ${rs(balance)}.`)
    setBusy(true)
    setError(null)
    try {
      await (host ? api.withdrawFunds(amount) : api.addFunds(amount))
      toast({ title: host ? `${rs(amount)} withdrawn` : `${rs(amount)} added to your wallet` })
      setOpen(false)
      onDone()
    } catch (err) {
      setError(err instanceof Error ? err.message : "That didn't work. Try again.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { setOpen(o); setError(null) }}>
      <DialogTrigger asChild>
        <Button disabled={host && balance <= 0}>{host ? "Withdraw" : "Add funds"}</Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={submit} className="grid gap-6">
          <DialogHeader>
            <DialogTitle>{host ? "Withdraw earnings" : "Add funds"}</DialogTitle>
            <DialogDescription className="text-body-sm text-ash">
              {host
                ? `Your balance is ${rs(balance)}. Payouts aren't connected yet, so the withdrawal is recorded but no money is sent.`
                : "Payments aren't connected yet, so this adds test balance without charging you."}
            </DialogDescription>
          </DialogHeader>
          <div>
            <label htmlFor="amount" className="mb-1.5 block text-body-sm">Amount in NPR</label>
            <Input id="amount" name="amount" type="number" inputMode="decimal" min="1" step="1" max={host ? balance : undefined} required autoFocus />
          </div>
          {error && <p role="alert" className="text-body-sm text-system-warning">{error}</p>}
          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={busy}>{busy ? "Saving…" : host ? "Withdraw" : "Add funds"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
