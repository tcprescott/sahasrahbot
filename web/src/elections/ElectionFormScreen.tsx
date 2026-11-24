import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api, unwrap, type ElectionDetail, type ElectionMethod, type ServerOption } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import {
  ActionsMenu,
  Banner,
  Button,
  ConfirmDialog,
  EmptyState,
  FormDialog,
  Icon,
  IconButton,
  PageHeader,
  Panel,
  type MenuItem,
} from '../components'
import { move } from '../ranked/ranking'
import { fromLocalInput, METHODS, timeZoneName, toLocalInput } from './labels'
import { editPath, resultsPath, votePath } from './paths'
import { StatusChip } from './StatusChip'
import './elections.css'

/** /elections/new and /elections/:electionId/edit — one page, saved as a draft until posted. */
export function ElectionFormScreen() {
  return <RequireSignIn>{() => <ElectionForm />}</RequireSignIn>
}

type Body = {
  guild_id: string
  channel_id: string
  title: string
  description: string | null
  candidates: string[]
  method: ElectionMethod
  seats: number
  voter_role_id: string | null
  closes_at: string | null
  show_vote_count: boolean
}

interface Draft {
  guildId: string
  channelId: string
  title: string
  description: string
  candidates: { key: number; name: string }[]
  method: ElectionMethod
  /** Empty while the person is retyping it. */
  seats: number | ''
  roleId: string
  closes: string
  showCount: boolean
}

let nextKey = 1
const row = (name = '') => ({ key: nextKey++, name })

function fromDetail(e: ElectionDetail | undefined, servers: ServerOption[]): Draft {
  if (!e) {
    return {
      guildId: servers[0]?.id ?? '',
      channelId: '',
      title: '',
      description: '',
      candidates: [row(), row()],
      method: 'stv',
      seats: 1,
      roleId: '',
      closes: '',
      showCount: true,
    }
  }
  return {
    guildId: e.guild_id ?? '',
    channelId: e.channel_id ?? '',
    title: e.title,
    description: e.description ?? '',
    candidates: e.candidates.map((c) => row(c.name)),
    method: e.method,
    seats: e.seats,
    roleId: e.voter_role_id ?? '',
    closes: toLocalInput(e.closes_at),
    showCount: e.show_vote_count,
  }
}

function toBody(d: Draft): Body {
  return {
    guild_id: d.guildId,
    channel_id: d.channelId,
    title: d.title.trim(),
    description: d.description.trim() || null,
    candidates: d.candidates.map((c) => c.name.trim()).filter(Boolean),
    method: d.method,
    seats: d.method === 'stv' ? Number(d.seats) || 1 : 1,
    voter_role_id: d.roleId || null,
    closes_at: fromLocalInput(d.closes),
    show_vote_count: d.showCount,
  }
}

function ElectionForm() {
  const { electionId } = useParams()
  const id = electionId ? Number(electionId) : undefined
  const query = useQuery(`elections/form/${id ?? 'new'}`, async () => {
    const [servers, election] = await Promise.all([
      api.GET('/api/v1/elections/servers').then(unwrap),
      id === undefined
        ? Promise.resolve(undefined)
        : api.GET('/api/v1/elections/{election_id}', { params: { path: { election_id: id } } }).then(unwrap),
    ])
    return { servers: servers.servers, election }
  })
  return (
    <Loaded query={query} label="Loading the election">
      {({ servers, election }) => {
        if (!election && servers.length === 0) {
          return (
            <EmptyState icon="how_to_vote" title="You can't run elections">
              Elections are run by server Administrators. You don't administer any server SahasrahBot is in.
            </EmptyState>
          )
        }
        if (election?.status === 'closed') {
          return (
            <EmptyState icon="how_to_vote" title="This election has closed">
              It can't be edited any more. <Link to={resultsPath(election.id)}>See the results</Link>.
            </EmptyState>
          )
        }
        // A new key per election, so the form starts over when it changes.
        return <Form key={election?.id ?? 'new'} servers={servers} election={election} onSaved={query.reload} />
      }}
    </Loaded>
  )
}

function Field({ id, label, hint, children }: Readonly<{ id: string; label: string; hint?: ReactNode; children: ReactNode }>) {
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      {children}
      {hint && (
        <span className="field__hint" id={`${id}-hint`}>
          {hint}
        </span>
      )}
    </div>
  )
}

function useServerOptions(guildId: string) {
  return useQuery(guildId ? `elections/servers/${guildId}` : null, async () =>
    // The id goes in the URL as the string it is: Discord ids are too big for a JS number.
    unwrap(await api.GET('/api/v1/elections/servers/{guild_id}', { params: { path: { guild_id: guildId as unknown as number } } })),
  )
}

function Form({
  servers,
  election,
  onSaved,
}: Readonly<{ servers: ServerOption[]; election: ElectionDetail | undefined; onSaved: () => void }>) {
  const navigate = useNavigate()
  const notice = (useLocation().state as { notice?: string; error?: string } | null) ?? {}
  const [draft, setDraft] = useState(() => fromDetail(election, servers))
  const [busy, setBusy] = useState<'save' | 'post'>()
  const [error, setError] = useState(notice.error)
  const [saved, setSaved] = useState(notice.notice)
  const [pasting, setPasting] = useState(false)
  const [confirm, setConfirm] = useState<'close' | 'delete'>()
  const options = useServerOptions(draft.guildId)
  const errorRef = useRef<HTMLDivElement>(null)

  const posted = election !== undefined && election.status !== 'draft'
  const locked = election?.locked ?? false
  const set = (patch: Partial<Draft>) => {
    setDraft((d) => ({ ...d, ...patch }))
    setSaved(undefined)
  }
  // The server choice offers the election's own server even if the viewer lost Administrator there.
  const serverChoices =
    election?.guild_id && !servers.some((s) => s.id === election.guild_id)
      ? [{ id: election.guild_id, name: election.guild_name ?? 'This server' }, ...servers]
      : servers
  const channels = options.data?.channels ?? []
  const roles = options.data?.roles ?? []

  // Pick the first channel once the server's channels arrive, if none is chosen.
  useEffect(() => {
    if (!draft.channelId && channels[0]) setDraft((d) => (d.channelId ? d : { ...d, channelId: channels[0]!.id }))
  }, [channels, draft.channelId])

  useEffect(() => {
    if (error) errorRef.current?.scrollIntoView({ block: 'nearest' })
  }, [error])

  const save = async (andPost: boolean) => {
    setBusy(andPost ? 'post' : 'save')
    setError(undefined)
    let savedId = election?.id
    try {
      const body = toBody(draft)
      const result = election
        ? unwrap(await api.PUT('/api/v1/elections/{election_id}', { params: { path: { election_id: election.id } }, body }))
        : unwrap(await api.POST('/api/v1/elections', { body }))
      savedId = result.id
      if (andPost) {
        unwrap(await api.POST('/api/v1/elections/{election_id}/publish', { params: { path: { election_id: result.id } } }))
        navigate('/elections', { state: { notice: `“${result.title}” is posted in Discord.` } })
        return
      }
      if (!election) {
        navigate(editPath(result.id), { replace: true, state: { notice: 'Draft saved. Nothing is posted yet.' } })
        return
      }
      setSaved(posted ? 'Saved. The Discord post is updated.' : 'Draft saved. Nothing is posted yet.')
      onSaved()
    } catch (e) {
      const message = (e as Error).message
      // Saved as a draft but the post failed: carry on editing that draft.
      if (!election && savedId !== undefined) {
        navigate(editPath(savedId), { replace: true, state: { error: `Saved as a draft, but not posted: ${message}` } })
        return
      }
      setError(message)
    } finally {
      setBusy(undefined)
    }
  }

  const act = async (kind: 'close' | 'delete') => {
    if (!election) return
    const path = { params: { path: { election_id: election.id } } }
    try {
      if (kind === 'close') {
        unwrap(await api.POST('/api/v1/elections/{election_id}/close', path))
        navigate(resultsPath(election.id))
      } else {
        unwrap(await api.DELETE('/api/v1/elections/{election_id}', path))
        navigate('/elections', { state: { notice: `“${election.title}” is deleted.` } })
      }
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const menu = actionsFor(election, {
    vote: () => election && navigate(votePath(election.id)),
    close: () => setConfirm('close'),
    remove: () => setConfirm('delete'),
  })

  const names = draft.candidates
  const setName = (key: number, name: string) => set({ candidates: names.map((c) => (c.key === key ? { ...c, name } : c)) })
  const moveRow = (key: number, by: -1 | 1) => {
    const order = move(
      names.map((c) => c.key),
      key,
      by,
    )
    set({ candidates: order.map((k) => names.find((c) => c.key === k)!) })
  }
  const filled = names.filter((c) => c.name.trim()).length

  return (
    <>
      <Link to="/elections" className="back-link">
        <Icon name="chevron_left" size={20} />
        Elections
      </Link>
      <PageHeader
        title={election ? election.title : 'New election'}
        lede={
          election ? (
            <>
              <StatusChip status={election.status} /> {election.ballots} {election.ballots === 1 ? 'ballot' : 'ballots'}
              {election.guild_name ? ` · ${election.guild_name}` : ''}
            </>
          ) : (
            'Nothing is posted until you press Create and post.'
          )
        }
        actions={menu.length > 0 && <ActionsMenu items={menu} />}
      />
      <div className="stack">
        {saved && <Banner tone="accent">{saved}</Banner>}
        {error && (
          <div ref={errorRef}>
            <Banner tone="error">{error}</Banner>
          </div>
        )}
        <Panel title="Basics">
          <div className="panel__pad stack">
            <div className="field-grid">
              <Field id="election-server" label="Server" hint={posted ? "A posted election stays in its server." : undefined}>
                <select
                  id="election-server"
                  className="input"
                  value={draft.guildId}
                  disabled={posted}
                  onChange={(e) => set({ guildId: e.target.value, channelId: '', roleId: '' })}
                >
                  {serverChoices.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field
                id="election-channel"
                label="Post it in"
                hint={posted ? 'A posted election stays in its channel.' : 'SahasrahBot posts the election here, with a Vote button.'}
              >
                <select
                  id="election-channel"
                  className="input"
                  value={draft.channelId}
                  disabled={posted || options.loading}
                  onChange={(e) => set({ channelId: e.target.value })}
                >
                  {!draft.channelId && <option value="">{options.loading ? 'Loading channels…' : 'Pick a channel'}</option>}
                  {draft.channelId && !channels.some((c) => c.id === draft.channelId) && (
                    <option value={draft.channelId}>{options.loading ? 'Loading channels…' : 'A channel SahasrahBot can’t see'}</option>
                  )}
                  {channels.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            {options.error && <Banner tone="error">{options.error.message}</Banner>}
            <Field id="election-title" label="Title">
              <input id="election-title" className="input" value={draft.title} maxLength={200} onChange={(e) => set({ title: e.target.value })} />
            </Field>
            <Field id="election-description" label="Description" hint="Optional. Shown on the ballot and in the Discord post.">
              <textarea
                id="election-description"
                className="input"
                value={draft.description}
                maxLength={2000}
                rows={3}
                onChange={(e) => set({ description: e.target.value })}
              />
            </Field>
          </div>
        </Panel>

        <Panel title="Candidates">
          <div className="panel__pad stack">
            {locked ? (
              <>
                <Banner tone="info">People have voted, so the candidates can't change.</Banner>
                <ol className="candidate-editor">
                  {names.map((c, i) => (
                    <li key={c.key}>
                      <span className="candidate-editor__n">{i + 1}</span>
                      <span>{c.name}</span>
                    </li>
                  ))}
                </ol>
              </>
            ) : (
              <>
                <ol className="candidate-editor">
                  {names.map((c, i) => {
                    const label = c.name.trim() || `candidate ${i + 1}`
                    return (
                      <li key={c.key}>
                        <span className="candidate-editor__n">{i + 1}</span>
                        <input
                          className="input"
                          value={c.name}
                          maxLength={200}
                          aria-label={`Candidate ${i + 1}`}
                          onChange={(e) => setName(c.key, e.target.value)}
                        />
                        <IconButton icon="arrow_upward" label={`Move ${label} up`} disabled={i === 0} onClick={() => moveRow(c.key, -1)} />
                        <IconButton
                          icon="arrow_downward"
                          label={`Move ${label} down`}
                          disabled={i === names.length - 1}
                          onClick={() => moveRow(c.key, 1)}
                        />
                        <IconButton
                          icon="close"
                          label={`Remove ${label}`}
                          onClick={() => set({ candidates: names.filter((x) => x.key !== c.key) })}
                        />
                      </li>
                    )
                  })}
                </ol>
                <div className="t-actions">
                  <Button variant="outline" size="sm" icon="add" onClick={() => set({ candidates: [...names, row()] })}>
                    Add candidate
                  </Button>
                  <Button variant="ghost" size="sm" icon="upload" onClick={() => setPasting(true)}>
                    Paste a list
                  </Button>
                </div>
                <span className="field__hint">Candidates appear on ballots in this order. Paste a list adds one name per line.</span>
              </>
            )}
          </div>
        </Panel>

        <Panel title="Voting">
          <div className="panel__pad stack">
            <fieldset className="field choice-fieldset" disabled={locked}>
              <legend className="field__label">Voting method</legend>
              <div className="choice-tiles">
                {METHODS.map((m) => (
                  <label key={m.key} className="choice-tile">
                    <input
                      type="radio"
                      name="method"
                      value={m.key}
                      checked={draft.method === m.key}
                      disabled={locked}
                      onChange={() => set({ method: m.key })} />
                    <div>
                      <b>{m.name}</b>
                      <span className="choice-tile__desc">{m.description}</span>
                    </div>
                  </label>
                ))}
              </div>
              {locked && <span className="field__hint">People have voted, so the method and winners can't change.</span>}
            </fieldset>
            <div className="field-grid">
              {draft.method === 'stv' && (
                <Field id="election-seats" label="Winners" hint="How many candidates win.">
                  <input
                    id="election-seats"
                    className="input"
                    type="number"
                    min={1}
                    max={Math.max(1, filled - 1)}
                    value={draft.seats}
                    disabled={locked}
                    onChange={(e) => set({ seats: e.target.value === '' ? '' : Math.max(1, Math.floor(Number(e.target.value)) || 1) })}
                  />
                </Field>
              )}
              <Field id="election-role" label="Who can vote" hint="Leave as everyone to let any server member vote.">
                <select id="election-role" className="input" value={draft.roleId} onChange={(e) => set({ roleId: e.target.value })}>
                  <option value="">Everyone in the server</option>
                  {draft.roleId && !roles.some((r) => r.id === draft.roleId) && (
                    <option value={draft.roleId}>{options.loading ? 'Loading roles…' : 'A role SahasrahBot can’t see'}</option>
                  )}
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <div className="field-grid">
              <Field
                id="election-closes"
                label="Closes"
                hint={`Optional. Your time zone (${timeZoneName()}). You can always end it early.`}
              >
                <div className="field__row">
                  <input
                    id="election-closes"
                    className="input grow"
                    type="datetime-local"
                    value={draft.closes}
                    onChange={(e) => set({ closes: e.target.value })}
                  />
                  {draft.closes && <IconButton icon="close" label="No closing time" onClick={() => set({ closes: '' })} />}
                </div>
              </Field>
              <label className="t-check">
                <input type="checkbox" checked={draft.showCount} onChange={(e) => set({ showCount: e.target.checked })} /> Show the number of
                ballots in the Discord post
              </label>
            </div>
          </div>
        </Panel>

        <div className="t-actions t-actions--end">
          <Button variant="ghost" asChild>
            <Link to="/elections">Cancel</Link>
          </Button>
          {posted ? (
            <Button icon="check_circle" busy={busy === 'save'} busyLabel="Saving" onClick={() => save(false)}>
              Save changes
            </Button>
          ) : (
            <>
              <Button variant="outline" busy={busy === 'save'} busyLabel="Saving" disabled={busy === 'post'} onClick={() => save(false)}>
                Save draft
              </Button>
              <Button icon="how_to_vote" busy={busy === 'post'} busyLabel="Posting" disabled={busy === 'save'} onClick={() => save(true)}>
                Create and post
              </Button>
            </>
          )}
        </div>
      </div>

      <PasteList
        open={pasting}
        onOpenChange={setPasting}
        onAdd={(list) => {
          const kept = names.filter((c) => c.name.trim())
          set({ candidates: [...kept, ...list.map((n) => row(n))] })
          setPasting(false)
        }}
      />
      <ConfirmDialog
        open={confirm === 'close'}
        onOpenChange={(open) => !open && setConfirm(undefined)}
        title="Close and count now?"
        action="Close and count"
        onConfirm={async () => act('close')}
      >
        Voting stops now, the ballots are counted and the results go up in Discord. This can't be undone.
      </ConfirmDialog>
      <ConfirmDialog
        open={confirm === 'delete'}
        onOpenChange={(open) => !open && setConfirm(undefined)}
        title="Delete this election?"
        action="Delete"
        onConfirm={async () => act('delete')}
      >
        The election, its ballots and its Discord post are deleted. This can't be undone.
      </ConfirmDialog>
    </>
  )
}

/** The page's Actions menu: none for a new election. */
function actionsFor(
  election: ElectionDetail | undefined,
  on: { vote: () => void; close: () => void; remove: () => void },
): MenuItem[] {
  if (!election) return []
  const open: MenuItem[] =
    election.status === 'open'
      ? [
          { label: 'Open the ballot', icon: 'how_to_vote', onSelect: on.vote },
          { label: 'Close and count now', icon: 'check_circle', onSelect: on.close },
        ]
      : []
  return [...open, { label: 'Delete', icon: 'delete', destructive: true, onSelect: on.remove }]
}

function PasteList({
  open,
  onOpenChange,
  onAdd,
}: Readonly<{ open: boolean; onOpenChange: (open: boolean) => void; onAdd: (names: string[]) => void }>) {
  const [text, setText] = useState('')
  const list = text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  return (
    <FormDialog
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next)
        if (!next) setText('')
      }}
      title="Paste a list"
      primaryLabel={list.length ? `Add ${list.length}` : 'Add'}
      onPrimary={() => {
        if (list.length) onAdd(list)
        setText('')
      }}
    >
      <div className="field">
        <label className="field__label" htmlFor="paste-list">
          One candidate per line
        </label>
        <textarea id="paste-list" className="input" rows={8} value={text} onChange={(e) => setText(e.target.value)} />
      </div>
    </FormDialog>
  )
}
