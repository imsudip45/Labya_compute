import type { GPU, Session, Host, Renter, User } from "./types"

// TODO: Replace with actual API calls to http://localhost:8000/api

export const mockHostUser: User = {
  id: "host-1",
  username: "johnhost",
  email: "john@host.com",
  first_name: "John",
  last_name: "Host",
}

export const mockHost: Host = {
  id: "host-1",
  user: mockHostUser,
  wallet_balance: 245075, // Updated to NPR equivalent (2450.75 USD * 100)
}

export const mockRenterUser: User = {
  id: "renter-1",
  username: "janeuser",
  email: "jane@renter.com",
  first_name: "Jane",
  last_name: "Renter",
}

export const mockRenter: Renter = {
  id: "renter-1",
  user: mockRenterUser,
  wallet_balance: 15025, // Updated to NPR equivalent (150.25 USD * 100)
}

export const mockGPUs: GPU[] = [
  {
    id: "gpu-1",
    gpu_name: "RTX 4090 Gaming Rig",
    gpu_model: "NVIDIA RTX 4090",
    gpu_memory: 24,
    gpu_price: 250, // Updated to NPR equivalent (2.5 USD * 100)
    gpu_location: "New York, USA",
    gpu_availability: true,
    host: mockHost,
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-20T14:30:00Z",
  },
  {
    id: "gpu-2",
    gpu_name: "RTX 3080 Workstation",
    gpu_model: "NVIDIA RTX 3080",
    gpu_memory: 10,
    gpu_price: 180, // Updated to NPR equivalent (1.8 USD * 100)
    gpu_location: "California, USA",
    gpu_availability: true,
    host: mockHost,
    created_at: "2024-01-10T09:00:00Z",
    updated_at: "2024-01-18T16:45:00Z",
  },
  {
    id: "gpu-3",
    gpu_name: "A100 ML Server",
    gpu_model: "NVIDIA A100",
    gpu_memory: 40,
    gpu_price: 400, // Updated to NPR equivalent (4.0 USD * 100)
    gpu_location: "Texas, USA",
    gpu_availability: false,
    host: mockHost,
    created_at: "2024-01-05T11:30:00Z",
    updated_at: "2024-01-22T08:15:00Z",
  },
]

export const mockSessions: Session[] = [
  {
    id: "session-1",
    gpu: mockGPUs[0],
    renter: mockRenter,
    host: mockHost,
    start_time: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
    status: "ACTIVE",
    ssh_host: "gpu-server-1.platform.com",
    ssh_port: 22,
    ssh_username: "user_session_1",
    gpu_utilization: 85,
    memory_utilization: 78,
    temperature: 72,
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "session-2",
    gpu: mockGPUs[1],
    renter: mockRenter,
    host: mockHost,
    start_time: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // 1 day ago
    end_time: new Date(Date.now() - 20 * 60 * 60 * 1000).toISOString(), // 20 hours ago (4 hour session)
    status: "COMPLETED",
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 20 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: "session-3",
    gpu: mockGPUs[2],
    renter: mockRenter,
    host: mockHost,
    start_time: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(), // 2 days ago
    end_time: new Date(Date.now() - 48 * 60 * 60 * 1000 + 15 * 60 * 1000).toISOString(), // 15 minutes later
    status: "CANCELLED",
    created_at: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 48 * 60 * 60 * 1000 + 15 * 60 * 1000).toISOString(),
  },
]

// Mock API functions - TODO: Replace with actual API calls
export const fetchHostStats = async () => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        totalGPUs: mockGPUs.length,
        activeGPUs: mockGPUs.filter((gpu) => gpu.gpu_availability).length,
        activeSessions: mockSessions.filter((session) => session.status === "ACTIVE").length,
        todayEarnings: 12550, // Updated to NPR equivalent (125.5 USD * 100)
        walletBalance: mockHost.wallet_balance,
      })
    }, 500)
  })
}

export const fetchHostGPUs = async () => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockGPUs)
    }, 300)
  })
}

export const fetchRecentSessions = async () => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockSessions.slice(0, 5))
    }, 400)
  })
}

export const fetchRenterStats = async () => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        activeSessions: mockSessions.filter((session) => session.status === "ACTIVE").length,
        totalSessions: mockSessions.length,
        totalSpent: 48725, // Updated to NPR equivalent (487.25 USD * 100)
        walletBalance: mockRenter.wallet_balance,
      })
    }, 500)
  })
}

export const fetchAvailableGPUs = async () => {
  return new Promise((resolve) => {
    setTimeout(() => {
      // Return available GPUs from different hosts
      const availableGPUs = [
        ...mockGPUs.filter((gpu) => gpu.gpu_availability),
        // Add some additional GPUs from other hosts for variety
        {
          id: "gpu-4",
          gpu_name: "RTX 4080 Super",
          gpu_model: "NVIDIA RTX 4080 Super",
          gpu_memory: 16,
          gpu_price: 220, // Updated to NPR equivalent (2.2 USD * 100)
          gpu_location: "Seattle, USA",
          gpu_availability: true,
          host: {
            id: "host-2",
            user: {
              id: "host-2",
              username: "sarahhost",
              email: "sarah@host.com",
              first_name: "Sarah",
              last_name: "Wilson",
            },
            wallet_balance: 120000, // Updated to NPR equivalent (1200 USD * 100)
          },
          created_at: "2024-01-12T08:00:00Z",
          updated_at: "2024-01-20T12:00:00Z",
        },
        {
          id: "gpu-5",
          gpu_name: "RTX 3070 Ti",
          gpu_model: "NVIDIA RTX 3070 Ti",
          gpu_memory: 8,
          gpu_price: 150, // Updated to NPR equivalent (1.5 USD * 100)
          gpu_location: "Austin, USA",
          gpu_availability: true,
          host: {
            id: "host-3",
            user: {
              id: "host-3",
              username: "mikehost",
              email: "mike@host.com",
              first_name: "Mike",
              last_name: "Johnson",
            },
            wallet_balance: 89050, // Updated to NPR equivalent (890.5 USD * 100)
          },
          created_at: "2024-01-08T15:30:00Z",
          updated_at: "2024-01-19T10:20:00Z",
        },
        {
          id: "gpu-6",
          gpu_name: "H100 ML Powerhouse",
          gpu_model: "NVIDIA H100",
          gpu_memory: 80,
          gpu_price: 850, // Updated to NPR equivalent (8.5 USD * 100)
          gpu_location: "California, USA",
          gpu_availability: true,
          host: {
            id: "host-4",
            user: {
              id: "host-4",
              username: "alexhost",
              email: "alex@host.com",
              first_name: "Alex",
              last_name: "Chen",
            },
            wallet_balance: 320000, // Updated to NPR equivalent (3200 USD * 100)
          },
          created_at: "2024-01-01T12:00:00Z",
          updated_at: "2024-01-21T09:30:00Z",
        },
        {
          id: "gpu-7",
          gpu_name: "RTX 3080 Gaming",
          gpu_model: "NVIDIA RTX 3080",
          gpu_memory: 10,
          gpu_price: 170, // Updated to NPR equivalent (1.7 USD * 100)
          gpu_location: "Florida, USA",
          gpu_availability: true,
          host: {
            id: "host-5",
            user: {
              id: "host-5",
              username: "emilyhost",
              email: "emily@host.com",
              first_name: "Emily",
              last_name: "Davis",
            },
            wallet_balance: 75025, // Updated to NPR equivalent (750.25 USD * 100)
          },
          created_at: "2024-01-18T14:15:00Z",
          updated_at: "2024-01-22T11:45:00Z",
        },
      ]
      resolve(availableGPUs)
    }, 400)
  })
}

export const fetchRenterSessions = async () => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(mockSessions)
    }, 300)
  })
}
