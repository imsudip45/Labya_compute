import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

// Pill buttons per CLAUDE.md. "default" is the white primary, "outline" the secondary.
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-body-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-40 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-neon-glow focus-visible:ring-offset-2 focus-visible:ring-offset-blackout",
  {
    variants: {
      variant: {
        default: "bg-whiteout text-graphite-deep hover:bg-cloud",
        destructive: "border border-graphite-light text-system-warning hover:border-system-warning",
        outline: "border border-graphite-light text-whiteout hover:border-ash",
        secondary: "bg-graphite text-whiteout hover:bg-graphite-light",
        ghost: "text-cloud hover:bg-graphite hover:text-whiteout",
        link: "text-whiteout underline decoration-graphite-light underline-offset-4 hover:decoration-whiteout",
      },
      size: {
        default: "h-10 px-5",
        sm: "h-8 px-3.5",
        lg: "h-11 px-7",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
