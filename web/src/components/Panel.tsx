import type { ReactNode } from 'react'

interface PanelProps {
  title?: ReactNode
  actions?: ReactNode
  children: ReactNode
}

/** A white card on the grey canvas, with an optional small-caps header. */
export function Panel({ title, actions, children }: PanelProps) {
  return (
    <section className="panel">
      {(title || actions) && (
        <header className="panel__head">
          {title && <h2 className="panel__title">{title}</h2>}
          {actions && <div className="panel__actions">{actions}</div>}
        </header>
      )}
      <div className="panel__body">{children}</div>
    </section>
  )
}

export function PanelRow({ children }: { children: ReactNode }) {
  return <div className="panel__row">{children}</div>
}
