import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-blackout px-4 text-whiteout">
      <div className="max-w-sm text-center">
        <p className="font-mono text-body-sm text-ash">404</p>
        <h1 className="mt-2 text-heading font-medium">Page not found</h1>
        <p className="mt-2 text-body-sm text-ash">This page doesn't exist. Check the address, or go back to the start.</p>
        <div className="mt-8 flex justify-center gap-3">
          <Button asChild><Link href="/">Home</Link></Button>
          <Button variant="outline" asChild><Link href="/dashboard">Overview</Link></Button>
        </div>
      </div>
    </main>
  )
}
