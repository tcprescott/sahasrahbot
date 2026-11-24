import { Slot } from '@radix-ui/react-slot'
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Icon } from './Icon'
import type { IconName } from './icons'

export type ButtonVariant = 'primary' | 'outline' | 'ghost' | 'danger'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: 'md' | 'sm'
  icon?: IconName
  /** While true the button shows a spinner and these words, and ignores presses. */
  busy?: boolean
  busyLabel?: string
  /** Render the child (a router Link, an anchor) with button styling. */
  asChild?: boolean
  children?: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', icon, busy = false, busyLabel, asChild = false, className, children, disabled, ...rest },
  ref,
) {
  const classes = ['btn', `btn--${variant}`, `btn--${size}`, busy && 'is-busy', className].filter(Boolean).join(' ')
  if (asChild) {
    return (
      <Slot ref={ref} className={classes} {...rest}>
        {children}
      </Slot>
    )
  }
  return (
    <button
      ref={ref}
      type="button"
      className={classes}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy ? <Icon name="progress_activity" size={18} className="spin" /> : icon && <Icon name={icon} size={18} />}
      <span>{busy && busyLabel ? busyLabel : children}</span>
    </button>
  )
})
