import type React from "react"
import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { GeistMono } from "geist/font/mono"
import "./globals.css"
import { Toaster } from "@/components/ui/toaster"

const inter = Inter({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-inter" })

export const metadata: Metadata = {
  title: "Labhya Compute",
  description: "Rent a GPU by the hour from hosts on the Labhya network, or earn by hosting your own.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${inter.variable} ${GeistMono.variable} antialiased`} suppressHydrationWarning>
      <body>
        {children}
        <Toaster />
      </body>
    </html>
  )
}
