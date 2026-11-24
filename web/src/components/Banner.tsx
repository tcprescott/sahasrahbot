import type { ReactNode } from 'react'
import { Icon } from './Icon'
import type { IconName } from './icons'

type BannerTone = 'info' | 'warning' | 'error' | 'accent'

const ICON: Record<BannerTone, IconName> = { info: 'info', warning: 'warning', error: 'error', accent: 'info' }

export function Banner({ tone = 'info', children, action }: { tone?: BannerTone; children: ReactNode; action?: ReactNode }) {
  return (
    <div className={`banner banner--${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      <Icon name={ICON[tone]} />
      <div className="banner__text">{children}</div>
      {action && <div className="banner__action">{action}</div>}
    </div>
  )
}
