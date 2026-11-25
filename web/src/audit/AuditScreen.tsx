import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { API_BASE, api, unwrap, type AuditEntry, type AuditOptions } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Banner, Button, Dialog, Icon, PageHeader, Spinner, type IconName } from '../components'
import { DataTable } from '../kit/DataTable'
import { browser } from '../lib/browser'
import { fullDate } from '../lib/time'
import './audit.css'

/** /audit — who changed what through SahasrahBot: your own actions, the servers you run, or everything (bot owners). */
export function AuditScreen() {
  return <RequireSignIn>{() => <AuditOptionsLoader />}</RequireSignIn>
}

function AuditOptionsLoader() {
  const options = useQuery('audit-options', async () => unwrap(await api.GET('/api/v1/audit/options')))
  return (
    <Loaded query={options} label="Loading the audit log">
      {(data) => <AuditLog options={data} />}
    </Loaded>
  )
}

type Filters = { scope: string; area: string; q: string; actor: string }

const VIA_ICONS: Record<AuditEntry['via'], IconName> = {
  website: 'language',
  api: 'key',
  mcp: 'smart_toy',
  discord: 'forum',
  racetime: 'flag',
  system: 'history',
}

function queryOf(filters: Filters, before?: number) {
  return {
    scope: filters.scope,
    area: filters.area || undefined,
    q: filters.q || undefined,
    actor: filters.actor || undefined,
    before,
  }
}

function AuditLog({ options }: Readonly<{ options: AuditOptions }>) {
  const [params, setParams] = useSearchParams()
  const scopeKeys = options.scopes.map((s) => s.key)
  const wanted = params.get('scope') ?? ''
  const filters: Filters = {
    scope: scopeKeys.includes(wanted) ? wanted : (options.scopes[1]?.key ?? 'mine'),
    area: params.get('area') ?? '',
    q: params.get('q') ?? '',
    actor: params.get('actor') ?? '',
  }
  const [search, setSearch] = useState(filters.q)
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [next, setNext] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>()
  const [open, setOpen] = useState<AuditEntry>()
  const key = JSON.stringify(filters)

  const load = async (before?: number) => {
    setLoading(true)
    try {
      const page = unwrap(await api.GET('/api/v1/audit', { params: { query: queryOf(filters, before) } }))
      setEntries((rows) => (before === undefined ? page.entries : [...rows, ...page.entries]))
      setNext(page.next_before ?? null)
      setError(undefined)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setEntries([])
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  const change = (patch: Partial<Filters>) => {
    const merged = { ...filters, ...patch }
    const nextParams = new URLSearchParams()
    for (const [k, v] of Object.entries(merged)) if (v) nextParams.set(k, v)
    setParams(nextParams, { replace: true })
  }

  const submitSearch = (event: FormEvent) => {
    event.preventDefault()
    change({ q: search.trim() })
  }

  const exportCsv = () => {
    const query = new URLSearchParams()
    for (const [k, v] of Object.entries(queryOf(filters))) if (v !== undefined) query.set(k, String(v))
    browser.assign(`${API_BASE}/api/v1/audit/export?${query.toString()}`)
  }

  const actorName = filters.actor ? entries.find((e) => e.actor_id === filters.actor)?.actor_name : undefined

  return (
    <>
      <PageHeader
        title="Audit log"
        lede="Every change made through SahasrahBot in the servers you run, and your own."
        actions={
          <Button variant="outline" icon="download" onClick={exportCsv}>
            Export CSV
          </Button>
        }
      />
      <div className="audit-filters">
        <label className="audit-select">
          <span>Showing</span>
          <select className="input" value={filters.scope} onChange={(e) => change({ scope: e.target.value })}>
            {options.scopes.map((s) => (
              <option key={s.key} value={s.key}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label className="audit-select">
          <span>Area</span>
          <select className="input" value={filters.area} onChange={(e) => change({ area: e.target.value })}>
            <option value="">All areas</option>
            {options.areas.map((a) => (
              <option key={a.key} value={a.key}>
                {a.label}
              </option>
            ))}
          </select>
        </label>
        <form className="search-field audit-search" role="search" onSubmit={submitSearch}>
          <Icon name="search" size={18} />
          <input
            className="search-field__input"
            aria-label="Search the audit log"
            placeholder="Search people, actions or names"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onBlur={() => search.trim() !== filters.q && change({ q: search.trim() })}
          />
        </form>
      </div>
      {filters.actor && (
        <Banner
          tone="info"
          action={
            <Button variant="outline" size="sm" onClick={() => change({ actor: '' })}>
              Show everyone
            </Button>
          }
        >
          Only showing what {actorName ?? 'one person'} did.
        </Banner>
      )}
      {error && (
        <Banner tone="error" action={<Button variant="outline" size="sm" onClick={() => void load()}>Try again</Button>}>
          {error}
        </Banner>
      )}
      {loading && entries.length === 0 ? (
        <Spinner label="Loading entries" />
      ) : (
        <DataTable
          label="Audit log"
          rows={entries}
          rowKey={(e) => e.id}
          onOpen={setOpen}
          openLabel={(e) => `${e.label}: ${e.target ?? ''}`}
          selectedKey={open?.id ?? null}
          empty={{
            icon: 'history',
            title: 'Nothing here yet',
            body: 'Changes show up here as people make them.',
          }}
          columns={[
            { key: 'when', header: 'When', render: (e) => <When iso={e.created_at} /> },
            {
              key: 'what',
              header: 'What happened',
              primary: true,
              render: (e) => (
                <span className="audit-what">
                  <b>{e.label}</b>
                  {e.target && <span className="audit-target">{e.target}</span>}
                </span>
              ),
            },
            { key: 'who', header: 'Who', render: (e) => <Who entry={e} /> },
            {
              key: 'server',
              header: 'Server',
              desktopOnly: true,
              render: (e) => e.guild_name ?? (e.guild_id ? <span className="muted mono">{e.guild_id}</span> : <span className="muted">No server</span>),
            },
            { key: 'via', header: 'Through', render: (e) => <Via entry={e} /> },
          ]}
        />
      )}
      {next !== null && (
        <div className="audit-more">
          <Button variant="outline" busy={loading} busyLabel="Loading" onClick={() => void load(next)}>
            Show older
          </Button>
        </div>
      )}
      <EntrySheet
        entry={open}
        onClose={() => setOpen(undefined)}
        onMoreBy={(e) => {
          setOpen(undefined)
          if (e.actor_id) change({ actor: e.actor_id })
        }}
      />
    </>
  )
}

/** Today's entries show the time; older ones the date too. Always the viewer's time zone. */
export function whenLabel(iso: string, now: Date = new Date()): string {
  const at = new Date(iso)
  const time = at.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  if (at.toDateString() === now.toDateString()) return time
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (at.toDateString() === yesterday.toDateString()) return `Yesterday, ${time}`
  const date = at.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: at.getFullYear() === now.getFullYear() ? undefined : 'numeric',
  })
  return `${date}, ${time}`
}

function When({ iso }: Readonly<{ iso: string }>) {
  return (
    <span className="audit-when" title={fullDate(iso)}>
      {whenLabel(iso)}
    </span>
  )
}

function Who({ entry }: Readonly<{ entry: AuditEntry }>) {
  if (entry.actor_name) return <>{entry.actor_name}</>
  if (entry.via === 'system') return <span className="muted">SahasrahBot</span>
  if (entry.actor_id) return <span className="muted mono">{entry.actor_id}</span>
  return <span className="muted">A deleted account</span>
}

function Via({ entry }: Readonly<{ entry: AuditEntry }>) {
  return (
    <span className="audit-via">
      <Icon name={VIA_ICONS[entry.via]} size={16} />
      {entry.via_label}
      {entry.via_detail && <span className="muted"> · {entry.via_detail}</span>}
    </span>
  )
}

function plain(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'nothing'
  if (Array.isArray(value)) return value.map(plain).join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  return String(value)
}

function words(key: string): string {
  const text = key.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** `details.changes` as before → after lines, and every other detail as a fact. */
export function describeDetails(details: Record<string, unknown>): { changes: [string, string, string][]; facts: [string, string][] } {
  const raw = details.changes
  const changes: [string, string, string][] =
    raw && typeof raw === 'object' && !Array.isArray(raw)
      ? Object.entries(raw as Record<string, unknown>).map(([field, pair]) => {
          const [before, after] = Array.isArray(pair) ? pair : [undefined, pair]
          return [words(field), plain(before), plain(after)]
        })
      : []
  const facts = Object.entries(details)
    .filter(([k]) => k !== 'changes')
    .map(([k, v]) => [words(k), plain(v)] as [string, string])
  return { changes, facts }
}

function EntrySheet({
  entry,
  onClose,
  onMoreBy,
}: Readonly<{ entry: AuditEntry | undefined; onClose: () => void; onMoreBy: (e: AuditEntry) => void }>) {
  const { changes, facts } = describeDetails((entry?.details ?? {}) as Record<string, unknown>)
  return (
    <Dialog
      open={entry !== undefined}
      onOpenChange={(o) => !o && onClose()}
      title={entry?.label ?? ''}
      size="side"
      footer={
        entry?.actor_id ? (
          <Button variant="outline" icon="search" onClick={() => onMoreBy(entry)}>
            More by {entry.actor_name ?? 'this person'}
          </Button>
        ) : undefined
      }
    >
      {entry && (
        <dl className="audit-dl">
          <dt>When</dt>
          <dd>{fullDate(entry.created_at)} (your time)</dd>
          <dt>Who</dt>
          <dd>
            <Who entry={entry} />
          </dd>
          <dt>Server</dt>
          <dd>{entry.guild_name ?? entry.guild_id ?? 'No server'}</dd>
          <dt>Through</dt>
          <dd>
            <Via entry={entry} />
          </dd>
          {entry.target && (
            <>
              <dt>What</dt>
              <dd>{entry.target}</dd>
            </>
          )}
          {changes.map(([field, before, after]) => (
            <ChangeRow key={field} field={field} before={before} after={after} />
          ))}
          {facts.map(([k, v]) => (
            <FactRow key={k} label={k} value={v} />
          ))}
          <dt>Action</dt>
          <dd className="mono">{entry.action}</dd>
        </dl>
      )}
    </Dialog>
  )
}

function ChangeRow({ field, before, after }: Readonly<{ field: string; before: string; after: string }>) {
  return (
    <>
      <dt>{field}</dt>
      <dd className="audit-change">
        <del>{before}</del> <span aria-hidden="true">→</span>
        <span className="visually-hidden">changed to</span> <ins>{after}</ins>
      </dd>
    </>
  )
}

function FactRow({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <>
      <dt>{label}</dt>
      <dd className="audit-fact">{value}</dd>
    </>
  )
}
