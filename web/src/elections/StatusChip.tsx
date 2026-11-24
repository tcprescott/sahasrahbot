import type { ElectionSummary } from '../api/client'
import { Chip } from '../components'

export function StatusChip({ status }: Readonly<{ status: ElectionSummary['status'] }>) {
  if (status === 'open') return <Chip tone="live">Open</Chip>
  if (status === 'draft') return <Chip tone="pending">Draft</Chip>
  return <Chip tone="neutral">Closed</Chip>
}
