import { AuthForm } from "@/components/app/auth-form"

export const metadata = { title: "Create a host account · Labhya Compute" }

export default function RegisterHostPage() {
  return <AuthForm mode="HOST" />
}
