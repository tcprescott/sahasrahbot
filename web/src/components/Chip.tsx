import type { ReactNode } from 'react'

export type Tone = 'ok' | 'pending' | 'live' | 'neutral' | 'cancelled' | 'info'

/** Status is a tint, not a fill: soft background, thin border, status-coloured text. */
export function Chip({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`chip chip--${tone}`}>{children}</span>
}

export function CountBadge({ count, label }: { count: number; label: string }) {
  if (count <= 0) return null
  return (
    <span className="count-badge" aria-label={label}>
      {count > 99 ? '99+' : count}
    </span>
  )
}
