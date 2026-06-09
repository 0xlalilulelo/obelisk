import { cva, type VariantProps } from 'class-variance-authority';
import { forwardRef, type ButtonHTMLAttributes } from 'react';

import { cn } from '@/lib/utils';

const button = cva(
  'inline-flex items-center justify-center gap-2 rounded text-body-base font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary-accent disabled:opacity-50 disabled:pointer-events-none',
  {
    variants: {
      variant: {
        // Primary: solid Obelisk Blue (design system).
        primary: 'bg-primary text-foreground hover:bg-primary/90',
        // Secondary: ghost — 1px border, subtle fill on hover.
        secondary:
          'border border-border-subtle bg-transparent text-foreground hover:bg-surface',
        ghost: 'bg-transparent text-foreground-muted hover:text-foreground hover:bg-surface',
        danger: 'border border-error/40 text-error hover:bg-error/10',
      },
      size: {
        sm: 'h-8 px-3 text-body-sm',
        md: 'h-9 px-4',
        lg: 'h-11 px-6',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(button({ variant, size }), className)} {...props} />
  ),
);
Button.displayName = 'Button';
