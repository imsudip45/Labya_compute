"use client"

import { useState } from "react"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { ProtectedRoute } from "@/components/auth/protected-route"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { useAuthStore } from "@/lib/auth-store"
import { useAppStore } from "@/lib/app-store"
import { Mail, Phone, MapPin, Calendar, Edit, Save, X, Server } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

export default function ProfilePage() {
  const { user, role } = useAuthStore()
  const { wallet } = useAppStore()
  const { toast } = useToast()
  const [isEditing, setIsEditing] = useState(false)

  const [formData, setFormData] = useState({
    first_name: user?.first_name || "",
    last_name: user?.last_name || "",
    email: user?.email || "",
    phone: user?.phone || "+977-9841234567",
    location: user?.location || "Kathmandu, Nepal",
    bio: user?.bio || "GPU enthusiast and cloud computing specialist.",
  })

  const handleSave = async () => {
    try {
      // TODO: Replace with real API call to update user profile
      console.log("Saving profile data:", formData)

      toast({
        title: "Profile updated",
        description: "Your profile has been updated successfully",
      })

      setIsEditing(false)
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update profile. Please try again.",
        variant: "destructive",
      })
    }
  }

  const handleCancel = () => {
    setFormData({
      first_name: user?.first_name || "",
      last_name: user?.last_name || "",
      email: user?.email || "",
      phone: user?.phone || "+977-9841234567",
      location: user?.location || "Kathmandu, Nepal",
      bio: user?.bio || "GPU enthusiast and cloud computing specialist.",
    })
    setIsEditing(false)
  }

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">Profile</h1>
              <p className="text-muted-foreground">Manage your account information and preferences</p>
            </div>
            {!isEditing ? (
              <Button onClick={() => setIsEditing(true)}>
                <Edit className="mr-2 h-4 w-4" />
                Edit Profile
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button onClick={handleSave}>
                  <Save className="mr-2 h-4 w-4" />
                  Save Changes
                </Button>
                <Button variant="outline" onClick={handleCancel}>
                  <X className="mr-2 h-4 w-4" />
                  Cancel
                </Button>
              </div>
            )}
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            {/* Profile Card */}
            <Card className="lg:col-span-1">
              <CardHeader className="text-center">
                <div className="flex justify-center mb-4">
                  <Avatar className="h-24 w-24">
                    <AvatarImage src="/placeholder.svg" alt={user?.first_name} />
                    <AvatarFallback className="text-2xl">
                      {user?.first_name?.[0]}
                      {user?.last_name?.[0]}
                    </AvatarFallback>
                  </Avatar>
                </div>
                <CardTitle className="text-xl">
                  {user?.first_name} {user?.last_name}
                </CardTitle>
                <div className="flex justify-center mt-2">
                  <Badge variant={role === "HOST" ? "default" : "secondary"}>{role}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center text-sm text-muted-foreground">
                  <Mail className="mr-2 h-4 w-4" />
                  {user?.email}
                </div>
                <div className="flex items-center text-sm text-muted-foreground">
                  <Phone className="mr-2 h-4 w-4" />
                  {user?.phone || "+977-9841234567"}
                </div>
                <div className="flex items-center text-sm text-muted-foreground">
                  <MapPin className="mr-2 h-4 w-4" />
                  {user?.location || "Kathmandu, Nepal"}
                </div>
                <div className="flex items-center text-sm text-muted-foreground">
                  <Calendar className="mr-2 h-4 w-4" />
                  Member since Jan 2024
                </div>
                {wallet && (
                  <div className="pt-4 border-t">
                    <div className="text-sm text-muted-foreground">Wallet Balance</div>
                    <div className="text-2xl font-bold text-green-600">Rs.{wallet.balance.toLocaleString()}</div>
                  </div>
                )}
              </CardContent>
            </Card>

            {role === "HOST" && (
              <Card className="mt-6 border-indigo-500/20 bg-indigo-950/5">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Server className="h-5 w-5 text-indigo-500" />
                    Desktop Host Agent
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    To host and lease out your GPU computing resources, download and run the standalone desktop client.
                  </p>
                  <a href="/downloads/LabhyaComputeAgentSetup.exe" download>
                    <Button className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium">
                      Download Agent Installer (.exe setup)
                    </Button>
                  </a>
                  <div className="flex gap-2 mt-2">
                    <a href="/downloads/LabhyaComputeAgent.exe" download className="flex-1">
                      <Button variant="outline" className="w-full text-[10px] py-1.5 h-auto text-muted-foreground hover:text-foreground">
                        Portable EXE
                      </Button>
                    </a>
                    <a href="/downloads/LabhyaComputeAgent.py" download className="flex-1">
                      <Button variant="outline" className="w-full text-[10px] py-1.5 h-auto text-muted-foreground hover:text-foreground">
                        Python Script (.py)
                      </Button>
                    </a>
                  </div>
                  <div className="text-[10px] text-muted-foreground pt-2 space-y-1">
                    <p className="font-semibold text-xs text-foreground">Quick Setup Instructions:</p>
                    <p>1. Ensure WSL2 & Docker Desktop are running.</p>
                    <p>2. Install the agent setup package on your Windows machine.</p>
                    <p>3. Authenticate with your Host credentials.</p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Profile Form */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Personal Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="first_name">First Name</Label>
                    <Input
                      id="first_name"
                      value={formData.first_name}
                      onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                      disabled={!isEditing}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name">Last Name</Label>
                    <Input
                      id="last_name"
                      value={formData.last_name}
                      onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                      disabled={!isEditing}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    disabled={!isEditing}
                  />
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone</Label>
                    <Input
                      id="phone"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      disabled={!isEditing}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="location">Location</Label>
                    <Input
                      id="location"
                      value={formData.location}
                      onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                      disabled={!isEditing}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="bio">Bio</Label>
                  <Textarea
                    id="bio"
                    value={formData.bio}
                    onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                    disabled={!isEditing}
                    rows={4}
                    placeholder="Tell us about yourself..."
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  )
}
