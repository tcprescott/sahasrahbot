import type { ReactNode } from 'react'
import { Icon } from './Icon'
import type { IconName } from './icons'

export function EmptyState({ icon, title, children }: { icon: IconName; title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <Icon name={icon} size={36} />
      <p className="empty__title">{title}</p>
      {children && <div className="empty__body">{children}</div>}
    </div>
  )
}

export function Spinner({ label }: { label: string }) {
  return (
    <div className="spinner" role="status">
      <Icon name="progress_activity" size={28} className="spin" />
      <span>{label}</span>
    </div>
  )
}
