import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: ReactNode
  lede?: ReactNode
  /** One main button, plus an Actions menu if the page needs more. */
  actions?: ReactNode
  /** 2 for a page inside another page's header, like a server section's sub-page. */
  level?: 1 | 2
}

export function PageHeader({ title, lede, actions, level = 1 }: Readonly<PageHeaderProps>) {
  const Heading = level === 2 ? 'h2' : 'h1'
  return (
    <header className="page-header">
      <div className="page-header__text">
        <Heading>{title}</Heading>
        {lede && <p className="page-header__lede">{lede}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </header>
  )
}
