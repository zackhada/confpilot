import { cva, type VariantProps } from 'class-variance-authority'
import { Slot } from 'radix-ui'
import type { ComponentProps } from 'react'
import { cn } from '@/shared/cn'

// shadcn/ui button, restyled for ConfPilot. Every size keeps a 44 px minimum tap target.
const buttonVariants = cva(
  [
    'inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap select-none',
    'rounded-(--radius-control) font-semibold leading-none',
    'transition-[transform,opacity] duration-150 active:scale-[0.97]',
    'disabled:pointer-events-none disabled:opacity-45',
    "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-5",
  ],
  {
    variants: {
      variant: {
        primary: 'bg-fresh text-fresh-ink',
        quiet: 'border border-rule bg-hall-raised text-ink',
        ghost: 'text-ink-soft hover:text-ink',
        litSolid: 'bg-lit-ink text-lit',
        litQuiet: 'border border-lit-rule text-lit-ink',
      },
      size: {
        md: 'min-h-11 px-4 text-(length:--text-body)',
        lg: 'min-h-14 px-6 text-(length:--text-lead)',
        icon: 'size-11',
      },
    },
    defaultVariants: { variant: 'quiet', size: 'md' },
  },
)

type ButtonProps = ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & { asChild?: boolean }

function Button({ className, variant, size, asChild = false, type, ...props }: ButtonProps) {
  const Comp = asChild ? Slot.Root : 'button'
  return (
    <Comp
      data-slot="button"
      type={asChild ? undefined : (type ?? 'button')}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
}

export { Button }
