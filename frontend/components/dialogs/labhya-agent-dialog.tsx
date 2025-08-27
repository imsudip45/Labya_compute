"use client"

import type React from "react"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Download, Monitor, Shield, Zap } from "lucide-react"

interface LabhyaAgentDialogProps {
  children: React.ReactNode
}

export function LabhyaAgentDialog({ children }: LabhyaAgentDialogProps) {
  const [isDownloading, setIsDownloading] = useState(false)

  const handleDownload = () => {
    setIsDownloading(true)
    // TODO: Replace with actual download URL for Labhya Agent installer
    // const downloadUrl = "https://releases.labhya.com/agent/windows/labhya-agent-setup.exe"

    // Simulate download
    setTimeout(() => {
      // Create a mock download link
      const link = document.createElement("a")
      link.href = "#" // TODO: Replace with actual download URL
      link.download = "labhya-agent-setup.exe"
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      setIsDownloading(false)
    }, 1000)
  }

  return (
    <Dialog>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Monitor className="h-5 w-5" />
            Start Hosting Your GPU
          </DialogTitle>
          <DialogDescription>
            Download the Labhya Agent to begin sharing your GPU computing power and earning NPR.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Labhya Agent for Windows</CardTitle>
              <CardDescription>The official desktop application to host your GPU resources securely</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="space-y-2">
                  <Shield className="h-8 w-8 mx-auto text-green-500" />
                  <p className="text-sm font-medium">Secure</p>
                  <p className="text-xs text-muted-foreground">End-to-end encryption</p>
                </div>
                <div className="space-y-2">
                  <Zap className="h-8 w-8 mx-auto text-blue-500" />
                  <p className="text-sm font-medium">Fast Setup</p>
                  <p className="text-xs text-muted-foreground">5-minute installation</p>
                </div>
                <div className="space-y-2">
                  <Monitor className="h-8 w-8 mx-auto text-purple-500" />
                  <p className="text-sm font-medium">Auto-detect</p>
                  <p className="text-xs text-muted-foreground">Finds your GPUs</p>
                </div>
              </div>

              <div className="bg-muted p-4 rounded-lg">
                <h4 className="font-medium mb-2">System Requirements:</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Windows 10/11 (64-bit)</li>
                  <li>• NVIDIA GPU with 4GB+ VRAM</li>
                  <li>• Stable internet connection</li>
                  <li>• Administrator privileges</li>
                </ul>
              </div>

              <Button onClick={handleDownload} className="w-full" size="lg" disabled={isDownloading}>
                <Download className="mr-2 h-4 w-4" />
                {isDownloading ? "Preparing Download..." : "Download Labhya Agent"}
              </Button>

              <p className="text-xs text-center text-muted-foreground">
                By downloading, you agree to our Terms of Service and Privacy Policy
              </p>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  )
}
