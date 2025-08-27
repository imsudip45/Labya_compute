import { LoginForm } from "@/components/auth/login-form"

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-primary">Labhya Compute</h1>
          <p className="text-muted-foreground mt-2">Rent and share GPU computing power</p>
        </div>
        <LoginForm />
      </div>
    </div>
  )
}
