import { AuthForm } from "@/components/app/auth-form"

export const metadata = { title: "Create a renter account · Labhya Compute" }

export default function RegisterRenterPage() {
  return <AuthForm mode="RENTER" />
}
