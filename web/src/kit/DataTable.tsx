import type { ReactNode } from 'react'
import { EmptyState, RowMenu, type IconName, type MenuItem } from '../components'
import { usePhone } from '../lib/usePhone'
import './table.css'

export interface Column<T> {
  key: string
  header: string
  cell: (row: T) => ReactNode
  /** The column that names the row: the card's title on a phone. Exactly one. */
  primary?: boolean
  align?: 'start' | 'end'
  /** Left off the phone card (still in the desktop table). */
  desktopOnly?: boolean
}

interface DataTableProps<T> {
  /** Names the table for screen readers, e.g. "Events". */
  label: string
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string | number
  /** The row's one ⋮ menu. Destructive items go last; the menu sorts them. A row with no items gets no ⋮. */
  rowMenu?: (row: T) => MenuItem[]
  /** Names the ⋮ for a screen reader, e.g. "More for SGL26". */
  rowMenuLabel?: (row: T) => string
  /** The row's one button, beside the ⋮. */
  rowAction?: (row: T) => ReactNode
  empty?: { icon: IconName; title: string; body?: ReactNode }
  /** Opening a row (a side sheet, say). The primary cell becomes a button that does it. */
  onOpen?: (row: T) => void
  /** Names the open button for a screen reader, e.g. "Open SGL26". Defaults to the primary cell's text. */
  openLabel?: (row: T) => string
  /** The row whose sheet is open, highlighted. */
  selectedKey?: string | number | null
}

/**
 * A table on desktop and one card per row on a phone, from one set of columns,
 * so a wide list never scrolls sideways or hides its row actions off-screen.
 */
export function DataTable<T>({
  label,
  columns,
  rows,
  rowKey,
  rowMenu,
  rowMenuLabel,
  rowAction,
  empty,
  onOpen,
  openLabel,
  selectedKey,
}: DataTableProps<T>) {
  const phone = usePhone()
  if (rows.length === 0 && empty) {
    return (
      <EmptyState icon={empty.icon} title={empty.title}>
        {empty.body}
      </EmptyState>
    )
  }
  const primary = columns.find((c) => c.primary) ?? columns[0]
  if (!primary) return null
  const title = (row: T) =>
    onOpen ? (
      <button type="button" className="data-table__open" aria-label={openLabel?.(row)} onClick={() => onOpen(row)}>
        {primary.cell(row)}
      </button>
    ) : (
      primary.cell(row)
    )
  const selected = (row: T) => selectedKey != null && rowKey(row) === selectedKey
  const actions = (row: T) => {
    if (!rowAction && !rowMenu) return null
    const items = rowMenu?.(row) ?? []
    return (
      <span className="data-table__actions">
        {rowAction?.(row)}
        {items.length > 0 && <RowMenu label={rowMenuLabel?.(row) ?? 'More'} items={items} />}
      </span>
    )
  }

  if (phone) {
    const rest = columns.filter((c) => c !== primary && !c.desktopOnly)
    return (
      <ul className="data-cards" aria-label={label}>
        {rows.map((row) => (
          <li key={rowKey(row)} className={selected(row) ? 'data-card data-card--selected' : 'data-card'}>
            <div className="data-card__head">
              <span className="data-card__title">{title(row)}</span>
              {actions(row)}
            </div>
            {rest.length > 0 && (
              <dl className="data-card__fields">
                {rest.map((c) => (
                  <div key={c.key} className="data-card__field">
                    <dt>{c.header}</dt>
                    <dd>{c.cell(row)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </li>
        ))}
      </ul>
    )
  }

  return (
    <div className="data-table__wrap" role="region" aria-label={label} tabIndex={0}>
      <table className="data-table" aria-label={label}>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col" className={c.align === 'end' ? 'data-table__end' : undefined}>
                {c.header}
              </th>
            ))}
            {(rowAction || rowMenu) && (
              <th scope="col" className="data-table__end">
                <span className="visually-hidden">Actions</span>
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className={selected(row) ? 'data-table__row--selected' : undefined}>
              {columns.map((c) =>
                c === primary ? (
                  <th key={c.key} scope="row" className="data-table__primary">
                    {title(row)}
                  </th>
                ) : (
                  <td key={c.key} className={c.align === 'end' ? 'data-table__end' : undefined}>
                    {c.cell(row)}
                  </td>
                ),
              )}
              {(rowAction || rowMenu) && <td className="data-table__end">{actions(row)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
