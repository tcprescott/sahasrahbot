import type { ElectionMethod, ElectionSummary } from '../api/client'
import { fullDate } from '../lib/time'

export const METHOD_LABEL: Record<ElectionMethod, string> = {
  stv: 'Ranked (STV)',
  approval: 'Approval',
  plurality: 'Plurality',
}

export const METHODS: { key: ElectionMethod; name: string; description: string }[] = [
  { key: 'stv', name: 'Ranked (instant runoff / STV)', description: 'Voters rank candidates. Best for committees and contested seats.' },
  { key: 'approval', name: 'Approval', description: 'Voters tick everyone they would accept. Most ticks wins.' },
  { key: 'plurality', name: 'Plurality', description: 'Voters pick one. Most votes wins. Good for quick polls.' },
]

/** "Ranked (STV), 3 seats", "Approval". */
export function methodText(method: ElectionMethod, seats: number): string {
  return method === 'stv' && seats > 1 ? `${METHOD_LABEL[method]}, ${seats} seats` : METHOD_LABEL[method]
}

/** When it closes (or closed), for a list row. */
export function closesText(e: Pick<ElectionSummary, 'status' | 'closes_at' | 'closed_at'>): string {
  if (e.status === 'closed') return e.closed_at ? `Closed ${fullDate(e.closed_at)}` : 'Closed'
  return e.closes_at ? fullDate(e.closes_at) : 'No closing time'
}

/** What a voter is asked to do. */
export function instructions(method: ElectionMethod, seats: number): string {
  if (method === 'approval') return "Tick every option you'd be happy with. The most ticks wins."
  if (method === 'plurality') return 'Pick one. The most votes wins.'
  const winners = seats > 1 ? `${seats} will win.` : 'One will win.'
  return `Tap candidates in the order you prefer them, favourite first. Tap a ranked one again to take it out. ${winners}`
}

/** "1st", "2nd", "3rd", "11th". */
export function ordinal(n: number): string {
  const teen = n % 100 >= 11 && n % 100 <= 13
  const suffix = teen ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th'
  return `${n}${suffix}`
}

/** A vote count as people read it: whole numbers plain, transfers to one decimal place. */
export function votes(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

/** An ISO time as the value of a datetime-local input, in the viewer's time zone. */
export function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** A datetime-local value back to an ISO time with a zone; empty means none. */
export function fromLocalInput(value: string): string | null {
  return value ? new Date(value).toISOString() : null
}

/** The viewer's time zone, for the closing time's hint. */
export function timeZoneName(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone
}
