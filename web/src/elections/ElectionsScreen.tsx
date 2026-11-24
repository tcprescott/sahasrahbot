import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, unwrap, type ElectionSummary } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Banner, Button, ConfirmDialog, PageHeader, type MenuItem } from '../components'
import { DataTable } from '../kit/DataTable'
import { closesText, methodText } from './labels'
import { editPath, resultsPath, votePath } from './paths'
import { StatusChip } from './StatusChip'
import './elections.css'

type Filter = 'open' | 'draft' | 'closed' | 'all'
const FILTERS: { key: Filter; label: string }[] = [
  { key: 'open', label: 'Open' },
  { key: 'draft', label: 'Drafts' },
  { key: 'closed', label: 'Closed' },
  { key: 'all', label: 'All' },
]

/** /elections — the elections in the servers you administer. */
export function ElectionsScreen() {
  return <RequireSignIn>{() => <Elections />}</RequireSignIn>
}

type Pending = { kind: 'close' | 'delete'; election: ElectionSummary }

function Elections() {
  const navigate = useNavigate()
  const notice = (useLocation().state as { notice?: string } | null)?.notice
  const query = useQuery('elections', async () => {
    const [list, servers] = await Promise.all([
      api.GET('/api/v1/elections').then(unwrap),
      api.GET('/api/v1/elections/servers').then(unwrap),
    ])
    return { elections: list.elections, servers: servers.servers }
  })
  const [filter, setFilter] = useState<Filter>()
  const [pending, setPending] = useState<Pending>()
  const [error, setError] = useState<string>()

  const act = async ({ kind, election }: Pending) => {
    const path = { params: { path: { election_id: election.id } } }
    try {
      if (kind === 'close') unwrap(await api.POST('/api/v1/elections/{election_id}/close', path))
      else unwrap(await api.DELETE('/api/v1/elections/{election_id}', path))
      setError(undefined)
      query.reload()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <Loaded query={query} label="Loading elections">
      {({ elections, servers }) => {
        const count = (f: Filter) => (f === 'all' ? elections.length : elections.filter((e) => e.status === f).length)
        // Start on Open, unless nothing is open.
        const shown = filter ?? (count('open') > 0 || elections.length === 0 ? 'open' : 'all')
        const rows = shown === 'all' ? elections : elections.filter((e) => e.status === shown)
        const menu = (e: ElectionSummary): MenuItem[] => {
          const items: MenuItem[] = []
          if (e.status !== 'closed') items.push({ label: 'Edit', icon: 'edit', onSelect: () => navigate(editPath(e.id)) })
          if (e.status === 'open') {
            items.push({ label: 'Open the ballot', icon: 'how_to_vote', onSelect: () => navigate(votePath(e.id)) })
            items.push({ label: 'Close and count now', icon: 'check_circle', onSelect: () => setPending({ kind: 'close', election: e }) })
          }
          if (e.status === 'closed') items.push({ label: 'View results', icon: 'bar_chart', onSelect: () => navigate(resultsPath(e.id)) })
          items.push({ label: 'Delete', icon: 'delete', destructive: true, onSelect: () => setPending({ kind: 'delete', election: e }) })
          return items
        }
        return (
          <>
            <PageHeader
              title="Elections"
              lede="Elections in the servers you administer."
              actions={
                servers.length > 0 && (
                  <Button icon="add" asChild>
                    <Link to="/elections/new">New election</Link>
                  </Button>
                )
              }
            />
            {notice && <Banner tone="accent">{notice}</Banner>}
            {error && <Banner tone="error">{error}</Banner>}
            {servers.length === 0 && elections.length === 0 ? (
              <Banner tone="info">
                Elections are run by server Administrators. You don't administer any server SahasrahBot is in.
              </Banner>
            ) : (
              <div className="stack">
                <fieldset className="filter-chips" aria-label="Show">
                  {FILTERS.map((f) => (
                    <button key={f.key} type="button" className="filter-chip" aria-pressed={shown === f.key} onClick={() => setFilter(f.key)}>
                      {f.label} <span className="filter-chips__n">{count(f.key)}</span>
                    </button>
                  ))}
                </fieldset>
                <DataTable
                  label="Elections"
                  rows={rows}
                  rowKey={(e) => e.id}
                  empty={{
                    icon: 'how_to_vote',
                    title: elections.length === 0 ? 'No elections yet' : 'Nothing here',
                    body: elections.length === 0 ? 'Press New election to make one.' : 'Pick another filter to see the rest.',
                  }}
                  columns={[
                    {
                      key: 'title',
                      header: 'Election',
                      primary: true,
                      render: (e) => <Link to={e.status === 'closed' ? resultsPath(e.id) : editPath(e.id)}>{e.title}</Link>,
                    },
                    { key: 'server', header: 'Server', render: (e) => e.guild_name ?? '–' },
                    { key: 'method', header: 'Method', render: (e) => methodText(e.method, e.seats) },
                    { key: 'ballots', header: 'Ballots', align: 'end', render: (e) => e.ballots },
                    { key: 'closes', header: 'Closes', render: (e) => closesText(e) },
                    { key: 'status', header: 'Status', render: (e) => <StatusChip status={e.status} /> },
                  ]}
                  rowMenu={menu}
                  rowMenuLabel={(e) => `More for ${e.title}`}
                />
              </div>
            )}
            <ConfirmDialog
              open={pending?.kind === 'close'}
              onOpenChange={(open) => !open && setPending(undefined)}
              title="Close and count now?"
              action="Close and count"
              onConfirm={async () => pending && act(pending)}
            >
              Voting on “{pending?.election.title}” stops now, the ballots are counted and the results go up in Discord. This can't be undone.
            </ConfirmDialog>
            <ConfirmDialog
              open={pending?.kind === 'delete'}
              onOpenChange={(open) => !open && setPending(undefined)}
              title="Delete this election?"
              action="Delete"
              onConfirm={async () => pending && act(pending)}
            >
              “{pending?.election.title}”, its ballots and its Discord post are deleted. This can't be undone.
            </ConfirmDialog>
          </>
        )
      }}
    </Loaded>
  )
}
