import { useState, type ReactNode } from 'react'
import { Link, NavLink, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api, unwrap, type RacerVerification, type VerifiedRacer } from '../../api/client'
import { Loaded } from '../../api/Loaded'
import { useQuery } from '../../api/useQuery'
import { ActionsMenu, Banner, Button, Chip, ConfirmDialog, Icon, type MenuItem, type Tone } from '../../components'
import { DataTable } from '../../kit/DataTable'
import { useServer } from '../ServerContext'
import { VerificationForm } from './VerificationForm'
import './verification.css'

/**
 * /servers/:guildId/verification/* — the server's verified-racer roles. The server
 * page (ServerScreen) draws the header and section tabs; this is the section body.
 */
export function VerificationSection() {
  return (
    <Routes>
      <Route index element={<VerificationList />} />
      <Route path="new" element={<NewVerification />} />
      <Route path=":verificationId" element={<VerificationPage tab="racers" />} />
      <Route path=":verificationId/settings" element={<VerificationPage tab="settings" />} />
    </Routes>
  )
}

/** Discord ids go in URLs as the strings they are: too big for a JS number. */
const asPathId = (id: string) => id as unknown as number

export const sectionPath = (guildId: string) => `/servers/${guildId}/verification`
export const verificationPath = (guildId: string, id: number) => `${sectionPath(guildId)}/${id}`

export function roleText(v: Pick<RacerVerification, 'role_name'>) {
  return v.role_name ?? '@deleted role'
}

export function countsText(v: Pick<RacerVerification, 'racetime_categories' | 'use_alttpr_ladder'>) {
  return [...v.racetime_categories, ...(v.use_alttpr_ladder ? ['ALTTPR Ladder'] : [])].join(', ')
}

export function recheckText(v: Pick<RacerVerification, 'reverify_period_days'>) {
  const days = v.reverify_period_days
  if (!days) return 'Off'
  return days === 1 ? 'Every day' : `Every ${days} days`
}

function problem(v: RacerVerification): string | undefined {
  if (!v.role_name) return 'The role was deleted. Pick another role in Settings.'
  if (!v.message_id) return "The Verify button isn't posted. Repost it so people can verify."
  if (!v.channel_name) return "SahasrahBot can't see the channel the button was in. Pick another in Settings."
  return undefined
}

function useVerifications(guildId: string) {
  return useQuery(`servers/${guildId}/racer-verifications`, async () =>
    unwrap(
      await api.GET('/api/v1/servers/{guild_id}/racer-verifications', { params: { path: { guild_id: asPathId(guildId) } } }),
    ),
  )
}

function VerificationList() {
  const { server } = useServer()
  const navigate = useNavigate()
  const notice = (useLocation().state as { notice?: string } | null)?.notice
  const query = useVerifications(server.id)
  const [pending, setPending] = useState<RacerVerification>()
  const [error, setError] = useState<string>()

  const repost = async (v: RacerVerification) => {
    try {
      unwrap(await api.POST('/api/v1/racer-verifications/{verification_id}/repost', { params: { path: { verification_id: v.id } } }))
      setError(undefined)
      query.reload()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <Loaded query={query} label="Loading racer verification">
      {({ verifications }) => {
        const menu = (v: RacerVerification): MenuItem[] => [
          { label: 'Settings', icon: 'edit', onSelect: () => navigate(`${verificationPath(server.id, v.id)}/settings`) },
          { label: 'Repost in Discord', icon: 'refresh', onSelect: () => repost(v) },
          { label: 'Delete', icon: 'delete', destructive: true, onSelect: () => setPending(v) },
        ]
        return (
          <div className="stack">
            <div className="rv-intro">
              <p>Give a role to people who've raced enough. They press a button in Discord and SahasrahBot counts their races.</p>
              <Button icon="add" asChild>
                <Link to={`${sectionPath(server.id)}/new`}>New verification</Link>
              </Button>
            </div>
            {notice && <Banner tone="accent">{notice}</Banner>}
            {error && <Banner tone="error">{error}</Banner>}
            <DataTable
              label="Racer verifications"
              rows={verifications}
              rowKey={(v) => v.id}
              empty={{ icon: 'verified', title: 'No racer verification yet', body: 'Press New verification to set one up.' }}
              columns={[
                {
                  key: 'role',
                  header: 'Role',
                  primary: true,
                  render: (v) => (
                    <span>
                      <Link to={verificationPath(server.id, v.id)} className="rv-role">
                        {roleText(v)}
                      </Link>
                      {problem(v) && (
                        <span className="rv-problem">
                          <Icon name="warning" size={16} /> {problem(v)}
                        </span>
                      )}
                    </span>
                  ),
                },
                {
                  key: 'needs',
                  header: 'Needs',
                  render: (v) => (
                    <span>
                      {v.requirement}
                      <br />
                      <span className="rv-sub">{countsText(v)}</span>
                    </span>
                  ),
                },
                { key: 'channel', header: 'Button in', desktopOnly: true, render: (v) => (v.channel_name ?? '–') },
                { key: 'verified', header: 'Verified', align: 'end', render: (v) => v.verified_count },
                {
                  key: 'recheck',
                  header: 'Recheck',
                  render: (v) => (
                    <span>
                      {recheckText(v)}
                      {v.revoke_ineligible && (
                        <>
                          <br />
                          <span className="rv-sub">removes the role</span>
                        </>
                      )}
                    </span>
                  ),
                },
              ]}
              rowMenu={menu}
              rowMenuLabel={(v) => `More for ${roleText(v)}`}
            />
            <DeleteDialog
              verification={pending}
              onClose={() => setPending(undefined)}
              onDeleted={() => {
                setPending(undefined)
                setError(undefined)
                query.reload()
              }}
              onError={setError}
            />
          </div>
        )
      }}
    </Loaded>
  )
}

function DeleteDialog({
  verification,
  onClose,
  onDeleted,
  onError,
}: Readonly<{
  verification: RacerVerification | undefined
  onClose: () => void
  onDeleted: () => void
  onError: (message: string) => void
}>) {
  return (
    <ConfirmDialog
      open={verification !== undefined}
      onOpenChange={(open) => !open && onClose()}
      title="Delete this racer verification?"
      action="Delete"
      onConfirm={async () => {
        if (!verification) return
        try {
          unwrap(await api.DELETE('/api/v1/racer-verifications/{verification_id}', { params: { path: { verification_id: verification.id } } }))
          onDeleted()
        } catch (e) {
          onError((e as Error).message)
        }
      }}
    >
      The Verify button message in Discord is deleted and SahasrahBot forgets its {verification?.verified_count} verified racers. Nobody
      loses the {verification ? roleText(verification) : ''} role.
    </ConfirmDialog>
  )
}

function BackLink() {
  const { server } = useServer()
  return (
    <Link to={sectionPath(server.id)} className="back-link">
      <Icon name="chevron_left" size={20} />
      All racer verification
    </Link>
  )
}

function NewVerification() {
  const { server } = useServer()
  const navigate = useNavigate()
  const query = useVerifications(server.id)
  return (
    <>
      <BackLink />
      <h2 className="rv-title">New racer verification</h2>
      <Loaded query={query} label="Loading">
        {({ racetime_categories, verifications }) => (
          <VerificationForm
            categories={racetime_categories}
            takenRoleIds={verifications.map((v) => v.role_id)}
            onSaved={(saved) =>
              navigate(verificationPath(server.id, saved.id), { state: { notice: `Posted the Verify button for ${roleText(saved)}.` } })
            }
          />
        )}
      </Loaded>
    </>
  )
}

function VerificationPage({ tab }: Readonly<{ tab: 'racers' | 'settings' }>) {
  const { server } = useServer()
  const id = Number(useParams().verificationId)
  const navigate = useNavigate()
  const notice = (useLocation().state as { notice?: string } | null)?.notice
  const query = useQuery(`racer-verifications/${id}`, async () => {
    const path = { params: { path: { verification_id: id } } }
    const [verification, list] = await Promise.all([
      api.GET('/api/v1/racer-verifications/{verification_id}', path).then(unwrap),
      api.GET('/api/v1/servers/{guild_id}/racer-verifications', { params: { path: { guild_id: asPathId(server.id) } } }).then(unwrap),
    ])
    return { verification, list }
  })
  const [deleting, setDeleting] = useState<RacerVerification>()
  const [message, setMessage] = useState<{ tone: 'accent' | 'error'; text: string }>()

  return (
    <>
      <BackLink />
      <Loaded query={query} label="Loading racer verification">
        {({ verification: v, list }) => {
          const base = verificationPath(server.id, v.id)
          const repost = async () => {
            try {
              unwrap(await api.POST('/api/v1/racer-verifications/{verification_id}/repost', { params: { path: { verification_id: v.id } } }))
              setMessage({ tone: 'accent', text: 'Posted the Verify button again and deleted the old message.' })
              query.reload()
            } catch (e) {
              setMessage({ tone: 'error', text: (e as Error).message })
            }
          }
          const jump = v.message_id && v.channel_id ? `https://discord.com/channels/${v.guild_id}/${v.channel_id}/${v.message_id}` : undefined
          return (
            <>
              <div className="rv-head">
                <div>
                  <h2 className="rv-title">{roleText(v)}</h2>
                  <p className="rv-sub">
                    {v.requirement} · {countsText(v)}
                    {jump && (
                      <>
                        {' · '}
                        <a href={jump} target="_blank" rel="noreferrer">
                          Jump to the message
                        </a>
                      </>
                    )}
                  </p>
                </div>
                <ActionsMenu
                  items={[
                    { label: 'Repost in Discord', icon: 'refresh', onSelect: repost },
                    { label: 'Delete verification', icon: 'delete', destructive: true, onSelect: () => setDeleting(v) },
                  ]}
                />
              </div>
              {notice && !message && <Banner tone="accent">{notice}</Banner>}
              {message && <Banner tone={message.tone}>{message.text}</Banner>}
              {problem(v) && <Banner tone="warning">{problem(v)}</Banner>}
              <nav className="rv-tabs" aria-label="Racer verification">
                <NavLink end to={base} className="rv-tab">
                  Verified racers ({v.verified_count})
                </NavLink>
                <NavLink to={`${base}/settings`} className="rv-tab">
                  Settings
                </NavLink>
              </nav>
              {tab === 'racers' ? (
                <Racers verification={v} onChanged={query.reload} />
              ) : (
                <VerificationForm
                  key={v.id}
                  verification={v}
                  categories={list.racetime_categories}
                  takenRoleIds={list.verifications.filter((o) => o.id !== v.id).map((o) => o.role_id)}
                  onSaved={() => {
                    setMessage({ tone: 'accent', text: 'Saved. The message in Discord is updated.' })
                    query.reload()
                  }}
                />
              )}
              <DeleteDialog
                verification={deleting}
                onClose={() => setDeleting(undefined)}
                onDeleted={() => navigate(sectionPath(server.id), { state: { notice: `Deleted racer verification for ${roleText(v)}.` } })}
                onError={(text) => setMessage({ tone: 'error', text })}
              />
            </>
          )
        }}
      </Loaded>
    </>
  )
}

type Filter = 'all' | VerifiedRacer['status']
const STATUS: Record<VerifiedRacer['status'], { label: string; tone: Tone }> = {
  verified: { label: 'Verified', tone: 'ok' },
  due: { label: 'Due for recheck', tone: 'pending' },
  not_qualified: { label: "Doesn't qualify now", tone: 'cancelled' },
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '–'
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

function Racers({ verification, onChanged }: Readonly<{ verification: RacerVerification; onChanged: () => void }>) {
  const query = useQuery(`racer-verifications/${verification.id}/racers`, async () =>
    unwrap(
      await api.GET('/api/v1/racer-verifications/{verification_id}/racers', { params: { path: { verification_id: verification.id } } }),
    ),
  )
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [removing, setRemoving] = useState<VerifiedRacer>()
  const [message, setMessage] = useState<{ tone: 'accent' | 'error'; text: ReactNode }>()

  const recheck = async (r: VerifiedRacer) => {
    try {
      const { racer } = unwrap(
        await api.POST('/api/v1/racer-verifications/{verification_id}/racers/{racer_id}/recheck', {
          params: { path: { verification_id: verification.id, racer_id: r.id } },
        }),
      )
      setMessage({
        tone: 'accent',
        text: racer
          ? `Rechecked ${nameOf(r)}: ${racer.race_count ?? 0} races counted. ${STATUS[racer.status].label}.`
          : `Rechecked ${nameOf(r)}. They no longer qualify or have left the server, so they were removed.`,
      })
      query.reload()
      if (!racer) onChanged()
    } catch (e) {
      setMessage({ tone: 'error', text: (e as Error).message })
    }
  }

  return (
    <Loaded query={query} label="Loading verified racers">
      {({ racers }) => {
        const count = (f: Filter) => (f === 'all' ? racers.length : racers.filter((r) => r.status === f).length)
        const needle = search.trim().toLowerCase()
        const rows = racers.filter(
          (r) =>
            (filter === 'all' || r.status === filter) &&
            (!needle || [r.name, r.racetime_id].some((x) => x?.toLowerCase().includes(needle))),
        )
        const filters: { key: Filter; label: string }[] = [
          { key: 'all', label: 'All' },
          ...(verification.reverify_period_days ? [{ key: 'due' as Filter, label: 'Due for recheck' }] : []),
          { key: 'not_qualified', label: "Doesn't qualify now" },
        ]
        return (
          <div className="stack">
            {message && <Banner tone={message.tone}>{message.text}</Banner>}
            <div className="rv-toolbar">
              <input
                className="input rv-search"
                type="search"
                placeholder="Search by name"
                aria-label="Search by name"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <fieldset className="filter-chips" aria-label="Show">
                {filters.map((f) => (
                  <button key={f.key} type="button" className="filter-chip" aria-pressed={filter === f.key} onClick={() => setFilter(f.key)}>
                    {f.label} <span className="filter-chips__n">{count(f.key)}</span>
                  </button>
                ))}
              </fieldset>
            </div>
            <DataTable
              label="Verified racers"
              rows={rows}
              rowKey={(r) => r.id}
              empty={{
                icon: 'verified',
                title: racers.length === 0 ? 'Nobody has verified yet' : 'Nobody matches',
                body: racers.length === 0 ? 'People appear here once they press the Verify button in Discord.' : undefined,
              }}
              columns={[
                {
                  key: 'name',
                  header: 'Racer',
                  primary: true,
                  render: (r) => (
                    <span>
                      <b>{nameOf(r)}</b>
                      {r.racetime_id && (
                        <>
                          <br />
                          <a className="rv-sub" href={r.racetime_url ?? undefined} target="_blank" rel="noreferrer">
                            racetime.gg profile
                          </a>
                        </>
                      )}
                    </span>
                  ),
                },
                { key: 'count', header: 'Races counted', align: 'end', render: (r) => r.race_count ?? '–' },
                { key: 'last', header: 'Last checked', render: (r) => formatDate(r.last_checked) },
                ...(verification.reverify_period_days
                  ? [{ key: 'next', header: 'Next check', desktopOnly: true, render: (r: VerifiedRacer) => formatDate(r.next_check) }]
                  : []),
                { key: 'status', header: 'Status', render: (r) => <Chip tone={STATUS[r.status].tone}>{STATUS[r.status].label}</Chip> },
              ]}
              rowMenu={(r) => [
                { label: 'Recheck now', icon: 'refresh', onSelect: () => recheck(r) },
                { label: 'Remove verification', icon: 'delete', destructive: true, onSelect: () => setRemoving(r) },
              ]}
              rowMenuLabel={(r) => `More for ${nameOf(r)}`}
            />
            <ConfirmDialog
              open={removing !== undefined}
              onOpenChange={(open) => !open && setRemoving(undefined)}
              title={`Remove ${removing ? nameOf(removing) : ''}?`}
              action="Remove"
              onConfirm={async () => {
                if (!removing) return
                try {
                  unwrap(
                    await api.DELETE('/api/v1/racer-verifications/{verification_id}/racers/{racer_id}', {
                      params: { path: { verification_id: verification.id, racer_id: removing.id } },
                    }),
                  )
                  setMessage({ tone: 'accent', text: `Removed ${nameOf(removing)} and took the role away.` })
                  query.reload()
                  onChanged()
                } catch (e) {
                  setMessage({ tone: 'error', text: (e as Error).message })
                }
              }}
            >
              SahasrahBot takes the {roleText(verification)} role from them and forgets their verification. They can press the Verify
              button again to get it back if they qualify.
            </ConfirmDialog>
          </div>
        )
      }}
    </Loaded>
  )
}

function nameOf(r: VerifiedRacer) {
  return r.name ?? r.discord_user_id ?? `Racer ${r.id}`
}
