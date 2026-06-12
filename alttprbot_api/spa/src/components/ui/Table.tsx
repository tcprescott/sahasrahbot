import type { ReactNode } from 'react';

interface TableProps {
  /** column header labels */
  head: ReactNode[];
  children: ReactNode;
  className?: string;
}

/** Horizontally-scrollable data table matching the design system (`table.data`). */
export function Table({ head, children, className }: TableProps) {
  return (
    <div className="table-wrap">
      <table className={['data', className ?? ''].filter(Boolean).join(' ')}>
        <thead>
          <tr>
            {head.map((label, i) => (
              <th key={i}>{label}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
