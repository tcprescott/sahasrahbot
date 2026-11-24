import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: ReactNode
  lede?: ReactNode
  /** One main button, plus an Actions menu if the page needs more. */
  actions?: ReactNode
}

export function PageHeader({ title, lede, actions }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header__text">
        <h1>{title}</h1>
        {lede && <p className="page-header__lede">{lede}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </header>
  )
}
