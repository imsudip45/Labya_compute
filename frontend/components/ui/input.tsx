import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "placeholder:text-pewter selection:bg-neon-muted flex h-10 w-full min-w-0 rounded-sm border border-graphite-light bg-graphite px-3 text-body-sm text-whiteout transition-colors outline-none disabled:cursor-not-allowed disabled:opacity-50",
        "focus-visible:border-neon-glow aria-invalid:border-system-warning",
        className
      )}
      {...props}
    />
  )
}

export { Input }
