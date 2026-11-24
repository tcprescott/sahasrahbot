import type { ReactNode } from 'react'
import { Icon } from './Icon'
import type { IconName } from './icons'

type BannerTone = 'info' | 'warning' | 'error' | 'accent'

const ICON: Record<BannerTone, IconName> = { info: 'info', warning: 'warning', error: 'error', accent: 'info' }

export function Banner({ tone = 'info', children, action }: Readonly<{ tone?: BannerTone; children: ReactNode; action?: ReactNode }>) {
  const className = `banner banner--${tone}`
  const body = (
    <>
      <Icon name={ICON[tone]} />
      <span className="banner__text">{children}</span>
      {action && <span className="banner__action">{action}</span>}
    </>
  )
  // Errors interrupt (role="alert"); everything else is a polite status message.
  if (tone === 'error') {
    return (
      <div className={className} role="alert">
        {body}
      </div>
    )
  }
  return <output className={className}>{body}</output>
}
