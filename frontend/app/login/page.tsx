import { AuthForm } from "@/components/app/auth-form"

export const metadata = { title: "Log in · Labhya Compute" }

export default function LoginPage() {
  return <AuthForm mode="login" />
}
