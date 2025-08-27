"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { ProtectedRoute } from "@/components/auth/protected-route"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { useAppStore } from "@/lib/app-store"
import { useAuthStore } from "@/lib/auth-store"
import { Wallet, Plus, ArrowUpRight, ArrowDownLeft, CreditCard, DollarSign, Minus } from "lucide-react"
import { format } from "date-fns"
import { useToast } from "@/hooks/use-toast"

export default function WalletPage() {
  const { role } = useAuthStore()
  const { wallet, transactions, loading, error, fetchWallet, fetchTransactions, addFunds, withdrawFunds } =
    useAppStore()

  const [addFundsOpen, setAddFundsOpen] = useState(false)
  const [withdrawFundsOpen, setWithdrawFundsOpen] = useState(false)
  const [amount, setAmount] = useState("")
  const [withdrawAmount, setWithdrawAmount] = useState("")
  const [addingFunds, setAddingFunds] = useState(false)
  const [withdrawingFunds, setWithdrawingFunds] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    const loadWalletData = async () => {
      await Promise.all([fetchWallet(), fetchTransactions()])
    }

    loadWalletData()
  }, [fetchWallet, fetchTransactions])

  const handleAddFunds = async () => {
    const fundAmount = Number.parseFloat(amount)
    if (isNaN(fundAmount) || fundAmount <= 0) {
      toast({
        title: "Invalid amount",
        description: "Please enter a valid amount greater than 0",
        variant: "destructive",
      })
      return
    }

    setAddingFunds(true)
    try {
      await addFunds(fundAmount)
      setAmount("")
      setAddFundsOpen(false)
      toast({
        title: "Funds added successfully",
        description: `Rs.${fundAmount.toLocaleString()} has been added to your wallet`,
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to add funds. Please try again.",
        variant: "destructive",
      })
    } finally {
      setAddingFunds(false)
    }
  }

  const handleWithdrawFunds = async () => {
    const withdrawalAmount = Number.parseFloat(withdrawAmount)
    if (isNaN(withdrawalAmount) || withdrawalAmount <= 0) {
      toast({
        title: "Invalid amount",
        description: "Please enter a valid amount greater than 0",
        variant: "destructive",
      })
      return
    }

    if (wallet && withdrawalAmount > wallet.balance) {
      toast({
        title: "Insufficient balance",
        description: "You don't have enough balance for this withdrawal",
        variant: "destructive",
      })
      return
    }

    setWithdrawingFunds(true)
    try {
      await withdrawFunds(withdrawalAmount)
      setWithdrawAmount("")
      setWithdrawFundsOpen(false)
      toast({
        title: "Withdrawal successful",
        description: `Rs.${withdrawalAmount.toLocaleString()} has been withdrawn from your wallet`,
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to withdraw funds. Please try again.",
        variant: "destructive",
      })
    } finally {
      setWithdrawingFunds(false)
    }
  }

  const getTransactionIcon = (type: string) => {
    const safe = (type || '').toUpperCase()
    switch (safe) {
      case "DEPOSIT":
        return <ArrowDownLeft className="h-4 w-4 text-green-500" />
      case "WITHDRAWAL":
        return <ArrowUpRight className="h-4 w-4 text-red-500" />
      case "RENTAL_PAYMENT":
        return <CreditCard className="h-4 w-4 text-blue-500" />
      default:
        return <DollarSign className="h-4 w-4" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variants = {
      COMPLETED: "default",
      PENDING: "secondary",
      FAILED: "destructive",
    } as const

    return <Badge variant={variants[status as keyof typeof variants] || "secondary"}>{status}</Badge>
  }

  if (loading) {
    return (
      <ProtectedRoute>
        <DashboardLayout>
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="mt-2 text-muted-foreground">Loading wallet...</p>
            </div>
          </div>
        </DashboardLayout>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">Wallet</h1>
              <p className="text-muted-foreground">
                {role === "HOST"
                  ? "Manage your earnings and withdraw funds from GPU rentals"
                  : "Manage your funds and view transaction history"}
              </p>
            </div>
            <div className="flex gap-2">
              {role === "RENTER" && (
                <Dialog open={addFundsOpen} onOpenChange={setAddFundsOpen}>
                  <DialogTrigger asChild>
                    <Button>
                      <Plus className="mr-2 h-4 w-4" />
                      Add Funds
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Add Funds to Wallet</DialogTitle>
                      <DialogDescription>
                        Add money to your wallet to rent GPU resources.{" "}
                        {/* TODO: Replace with real payment integration */}
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="amount">Amount (NPR)</Label>
                        <Input
                          id="amount"
                          type="number"
                          placeholder="Enter amount"
                          value={amount}
                          onChange={(e) => setAmount(e.target.value)}
                          min="100"
                          step="100"
                        />
                      </div>
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setAddFundsOpen(false)}>
                        Cancel
                      </Button>
                      <Button onClick={handleAddFunds} disabled={addingFunds}>
                        {addingFunds ? "Processing..." : "Add Funds"}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              )}

              {role === "HOST" && (
                <Dialog open={withdrawFundsOpen} onOpenChange={setWithdrawFundsOpen}>
                  <DialogTrigger asChild>
                    <Button>
                      <Minus className="mr-2 h-4 w-4" />
                      Withdraw Funds
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Withdraw Funds</DialogTitle>
                      <DialogDescription>
                        Withdraw your earnings to your bank account. {/* TODO: Replace with real bank integration */}
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="withdrawAmount">Amount (NPR)</Label>
                        <Input
                          id="withdrawAmount"
                          type="number"
                          placeholder="Enter amount"
                          value={withdrawAmount}
                          onChange={(e) => setWithdrawAmount(e.target.value)}
                          min="100"
                          step="100"
                          max={wallet?.balance || 0}
                        />
                        <p className="text-sm text-muted-foreground mt-1">
                          Available balance: Rs.{wallet?.balance?.toLocaleString() || "0"}
                        </p>
                      </div>
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setWithdrawFundsOpen(false)}>
                        Cancel
                      </Button>
                      <Button
                        onClick={handleWithdrawFunds}
                        disabled={
                          withdrawingFunds ||
                          !withdrawAmount ||
                          Number.parseFloat(withdrawAmount) > (wallet?.balance || 0)
                        }
                      >
                        {withdrawingFunds ? "Processing..." : "Withdraw Funds"}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              )}
            </div>
          </div>

          {/* Wallet Balance Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Wallet className="h-5 w-5" />
                {role === "HOST" ? "Total Earnings" : "Current Balance"}
              </CardTitle>
              <CardDescription>
                {role === "HOST" ? "Total earnings from GPU rentals" : "Available funds in your wallet"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-primary">Rs.{wallet?.balance?.toLocaleString() || "0"}</div>
              <p className="text-sm text-muted-foreground mt-1">
                {wallet?.currency || "NPR"} • Last updated{" "}
                {wallet?.updated_at ? format(new Date(wallet.updated_at), "MMM d, yyyy 'at' h:mm a") : "Never"}
              </p>
            </CardContent>
          </Card>

          {/* Transaction History */}
          <Card>
            <CardHeader>
              <CardTitle>Transaction History</CardTitle>
              <CardDescription>
                {role === "HOST" ? "Your earnings and withdrawal history" : "Your recent wallet transactions"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {transactions.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <DollarSign className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No transactions yet</p>
                  <p className="text-sm">
                    {role === "HOST" ? "Start renting out your GPUs to earn" : "Add funds to get started"}
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Type</TableHead>
                      <TableHead>Amount</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Reference</TableHead>
                      <TableHead>Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {transactions.map((transaction) => (
                      <TableRow key={transaction.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getTransactionIcon(transaction.transaction_type)}
                            <span className="capitalize">
                              {transaction.transaction_type === "DEPOSIT" && role === "HOST"
                                ? "Earning"
                                : (transaction.transaction_type || '').replaceAll('_',' ').toLowerCase()}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className={transaction.amount > 0 ? "text-green-600" : "text-red-600"}>
                            {transaction.amount > 0 ? "+" : ""}Rs.{Math.abs(transaction.amount).toLocaleString()}
                          </span>
                        </TableCell>
                        <TableCell>{getStatusBadge(transaction.status)}</TableCell>
                        <TableCell className="font-mono text-sm">{transaction.reference_id || "—"}</TableCell>
                        <TableCell>{format(new Date(transaction.created_at), "MMM d, yyyy")}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
