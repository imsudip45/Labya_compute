// TODO: Replace with actual authentication system
// This file contains dummy credentials for testing the Labhya Compute platform

export const DUMMY_CREDENTIALS = {
  // Host account credentials
  HOST: {
    email: "host@example.com",
    password: "password123",
    userData: {
      id: "host-1",
      username: "host",
      email: "host@example.com",
      first_name: "John",
      last_name: "Host",
      role: "HOST" as const,
    },
  },

  // Renter account credentials
  RENTER: {
    email: "renter@example.com",
    password: "password123",
    userData: {
      id: "renter-1",
      username: "renter",
      email: "renter@example.com",
      first_name: "Jane",
      last_name: "Renter",
      role: "RENTER" as const,
    },
  },

  // Additional test accounts
  ADDITIONAL_HOSTS: [
    {
      email: "host2@example.com",
      password: "password123",
      userData: {
        id: "host-2",
        username: "host2",
        email: "host2@example.com",
        first_name: "Mike",
        last_name: "Provider",
        role: "HOST" as const,
      },
    },
  ],

  ADDITIONAL_RENTERS: [
    {
      email: "renter2@example.com",
      password: "password123",
      userData: {
        id: "renter-2",
        username: "renter2",
        email: "renter2@example.com",
        first_name: "Sarah",
        last_name: "Developer",
        role: "RENTER" as const,
      },
    },
  ],
}

// Helper function to validate dummy credentials
export const validateDummyCredentials = (email: string, password: string) => {
  // Check main accounts
  if (email === DUMMY_CREDENTIALS.HOST.email && password === DUMMY_CREDENTIALS.HOST.password) {
    return DUMMY_CREDENTIALS.HOST.userData
  }

  if (email === DUMMY_CREDENTIALS.RENTER.email && password === DUMMY_CREDENTIALS.RENTER.password) {
    return DUMMY_CREDENTIALS.RENTER.userData
  }

  // Check additional accounts
  const allAccounts = [...DUMMY_CREDENTIALS.ADDITIONAL_HOSTS, ...DUMMY_CREDENTIALS.ADDITIONAL_RENTERS]

  const account = allAccounts.find((acc) => acc.email === email && acc.password === password)
  return account?.userData || null
}
