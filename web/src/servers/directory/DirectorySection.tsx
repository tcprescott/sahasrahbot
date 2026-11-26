import { useEffect, useId, useState, type ReactNode } from 'react'
import { api, unwrap, type GetBody } from '../../api/client'
import { Loaded } from '../../api/Loaded'
import { useQuery } from '../../api/useQuery'
import {
  ActionsMenu,
  Banner,
  Button,
  ConfirmDialog,
  EmptyState,
  FormDialog,
  Icon,
  IconButton,
  Panel,
  RowMenu,
} from '../../components'
import { ago } from '../../lib/time'
import { useServer } from '../ServerContext'
import './directory.css'

export type ServerDirectory = GetBody<'/api/v1/servers/{guild_id}/directory'>
export type DirectoryCategory = ServerDirectory['categories'][number]
export type DirectoryServer = DirectoryCategory['servers'][number]
type Invite = GetBody<'/api/v1/servers/{guild_id}/directory/invite'>
export interface Channel {
  id: string
  name: string
}

type Editing =
  | { kind: 'category'; category?: DirectoryCategory }
  | { kind: 'server'; category: DirectoryCategory; server?: DirectoryServer }
  | { kind: 'delete-category'; category: DirectoryCategory }
  | { kind: 'delete-server'; server: DirectoryServer }
  | { kind: 'post' }

/** The section's route under `servers/:guildId`: the server comes from ServerScreen. */
export function DirectoryRoute() {
  const { server } = useServer()
  return <DirectorySection guildId={server.id} channels={server.text_channels} />
}

/**
 * The "Server directory" section of a server's page: the partner servers
 * SahasrahBot posts to the server's channels, in categories. Every change is
 * saved at once; "Post to Discord" replaces what Discord shows.
 */
export function DirectorySection({ guildId, channels }: Readonly<{ guildId: string; channels: Channel[] }>) {
  const query = useQuery(`directory:${guildId}`, () =>
    api.GET('/api/v1/servers/{guild_id}/directory', { params: { path: guildPath(guildId) } }).then(unwrap),
  )
  return (
    <Loaded query={query} label="Loading the server directory">
      {(initial) => <Directory guildId={guildId} initial={initial} channels={channels} />}
    </Loaded>
  )
}

/** Discord ids don't fit in a JS number, so the id goes into the URL as the string it is. */
function guildPath(guildId: string) {
  return { guild_id: guildId as unknown as number }
}

function channelName(channels: Channel[], id: string): string {
  const name = channels.find((c) => c.id === id)?.name
  if (!name) return 'a channel SahasrahBot can’t see'
  return name.startsWith('#') ? name : `#${name}`
}

function initials(text: string): string {
  const letters = text
    .split(/\s+/)
    .map((w) => w.replace(/[^\p{L}\p{N}]/gu, '')[0])
    .filter(Boolean)
  return (letters.join('').slice(0, 2) || '?').toUpperCase()
}

function moved<T>(list: T[], index: number, by: -1 | 1): T[] {
  const next = [...list]
  const [item] = next.splice(index, 1)
  next.splice(index + by, 0, item as T)
  return next
}

function Directory({ guildId, initial, channels }: Readonly<{ guildId: string; initial: ServerDirectory; channels: Channel[] }>) {
  const [dir, setDir] = useState(initial)
  const [editing, setEditing] = useState<Editing>()
  const [error, setError] = useState<string>()
  const [notice, setNotice] = useState<string>()
  const path = guildPath(guildId)

  useEffect(() => setDir(initial), [initial])

  /** Run a change; the API answers with the whole directory. False when it failed. */
  const change = async (call: () => Promise<ServerDirectory>): Promise<boolean> => {
    try {
      setDir(await call())
      setError(undefined)
      setNotice(undefined)
      return true
    } catch (e) {
      setError((e as Error).message)
      return false
    }
  }

  const moveCategory = (index: number, by: -1 | 1) =>
    change(async () =>
      unwrap(
        await api.PUT('/api/v1/servers/{guild_id}/directory/order', {
          params: { path },
          body: { ids: moved(dir.categories, index, by).map((c) => c.id) },
        }),
      ),
    )

  const moveServer = (category: DirectoryCategory, index: number, by: -1 | 1) =>
    change(async () =>
      unwrap(
        await api.PUT('/api/v1/servers/{guild_id}/directory/categories/{category_id}/order', {
          params: { path: { ...path, category_id: category.id } },
          body: { ids: moved(category.servers, index, by).map((s) => s.id) },
        }),
      ),
    )

  const post = async (): Promise<boolean> => {
    try {
      const posted = unwrap(await api.POST('/api/v1/servers/{guild_id}/directory/post', { params: { path } }))
      setDir(unwrap(await api.GET('/api/v1/servers/{guild_id}/directory', { params: { path } })))
      setError(undefined)
      setNotice(`Posted ${posted.messages} ${posted.messages === 1 ? 'message' : 'messages'} to Discord.`)
      return true
    } catch (e) {
      setError((e as Error).message)
      return false
    }
  }

  const empty = dir.categories.length === 0
  return (
    <div className="stack">
      <div className="dir-bar">
        <p className="muted dir-bar__lede">Partner servers SahasrahBot posts to your channels, grouped in categories.</p>
        <div className="dir-bar__actions">
          <ActionsMenu items={[{ label: 'New category', icon: 'add', onSelect: () => setEditing({ kind: 'category' }) }]} />
          <Button icon="refresh" disabled={empty} onClick={() => setEditing({ kind: 'post' })}>
            Post to Discord
          </Button>
        </div>
      </div>
      {error && <Banner tone="error">{error}</Banner>}
      {notice && <Banner tone="accent">{notice}</Banner>}
      {dir.unposted_changes && (
        <Banner tone="warning" action={<Button variant="outline" size="sm" onClick={() => setEditing({ kind: 'post' })}>Post to Discord</Button>}>
          {dir.last_posted_at
            ? `You've made changes since the list was last posted (${ago(dir.last_posted_at)}). Discord still shows the old list.`
            : 'Discord won’t show these changes until you post the list.'}
        </Banner>
      )}
      {empty ? (
        <EmptyState icon="forum" title="No categories yet">
          <p>Make a category, such as “Randomizer communities”, then add servers to it with their invite links.</p>
          <Button icon="add" onClick={() => setEditing({ kind: 'category' })}>New category</Button>
        </EmptyState>
      ) : (
        <div className="dir-split">
          <div className="stack">
            {dir.categories.map((category, index) => (
              <CategoryPanel
                key={category.id}
                category={category}
                channels={channels}
                first={index === 0}
                last={index === dir.categories.length - 1}
                onMove={(by) => moveCategory(index, by)}
                onMoveServer={(i, by) => moveServer(category, i, by)}
                onEdit={(e) => setEditing(e)}
              />
            ))}
          </div>
          <Preview dir={dir} channels={channels} />
        </div>
      )}

      {editing?.kind === 'category' && (
        <CategoryDialog
          category={editing.category}
          channels={channels}
          onClose={() => setEditing(undefined)}
          onSave={(body) =>
            change(async () =>
              editing.category
                ? unwrap(
                    await api.PUT('/api/v1/servers/{guild_id}/directory/categories/{category_id}', {
                      params: { path: { ...path, category_id: editing.category.id } },
                      body,
                    }),
                  )
                : unwrap(await api.POST('/api/v1/servers/{guild_id}/directory/categories', { params: { path }, body })),
            )
          }
        />
      )}
      {editing?.kind === 'server' && (
        <ServerDialog
          guildId={guildId}
          category={editing.category}
          server={editing.server}
          categories={dir.categories}
          onClose={() => setEditing(undefined)}
          onSave={(body) =>
            change(async () =>
              editing.server
                ? unwrap(
                    await api.PUT('/api/v1/servers/{guild_id}/directory/servers/{server_id}', {
                      params: { path: { ...path, server_id: editing.server.id } },
                      body,
                    }),
                  )
                : unwrap(
                    await api.POST('/api/v1/servers/{guild_id}/directory/categories/{category_id}/servers', {
                      params: { path: { ...path, category_id: editing.category.id } },
                      body: { invite: body.invite, description: body.description },
                    }),
                  ),
            )
          }
        />
      )}
      <ConfirmDialog
        open={editing?.kind === 'delete-category'}
        onOpenChange={(open) => !open && setEditing(undefined)}
        title="Delete this category?"
        action="Delete category"
        onConfirm={async () => {
          if (editing?.kind !== 'delete-category') return
          const id = editing.category.id
          await change(async () =>
            unwrap(await api.DELETE('/api/v1/servers/{guild_id}/directory/categories/{category_id}', { params: { path: { ...path, category_id: id } } })),
          )
        }}
      >
        {editing?.kind === 'delete-category' &&
          `“${editing.category.title}” and the ${editing.category.servers.length} ${editing.category.servers.length === 1 ? 'server' : 'servers'} in it are deleted. Discord keeps showing them until you post the list again.`}
      </ConfirmDialog>
      <ConfirmDialog
        open={editing?.kind === 'delete-server'}
        onOpenChange={(open) => !open && setEditing(undefined)}
        title="Remove this server?"
        action="Remove server"
        onConfirm={async () => {
          if (editing?.kind !== 'delete-server') return
          const id = editing.server.id
          await change(async () =>
            unwrap(await api.DELETE('/api/v1/servers/{guild_id}/directory/servers/{server_id}', { params: { path: { ...path, server_id: id } } })),
          )
        }}
      >
        {editing?.kind === 'delete-server' && `“${editing.server.description}” comes off the list. Discord keeps showing it until you post the list again.`}
      </ConfirmDialog>
      {editing?.kind === 'post' && <PostDialog dir={dir} channels={channels} onClose={() => setEditing(undefined)} onPost={post} />}
    </div>
  )
}

function CategoryPanel({
  category,
  channels,
  first,
  last,
  onMove,
  onMoveServer,
  onEdit,
}: Readonly<{
  category: DirectoryCategory
  channels: Channel[]
  first: boolean
  last: boolean
  onMove: (by: -1 | 1) => void
  onMoveServer: (index: number, by: -1 | 1) => void
  onEdit: (editing: Editing) => void
}>) {
  const servers = category.servers
  return (
    <Panel
      title={category.title}
      actions={
        <>
          <span className="dir-move dir-move--category">
            <IconButton icon="arrow_upward" label={`Move ${category.title} up`} disabled={first} onClick={() => onMove(-1)} />
            <IconButton icon="arrow_downward" label={`Move ${category.title} down`} disabled={last} onClick={() => onMove(1)} />
          </span>
          <Button variant="outline" size="sm" icon="add" onClick={() => onEdit({ kind: 'server', category })}>
            Add server
          </Button>
          <RowMenu
            label={`More for ${category.title}`}
            items={[
              { label: 'Edit category', icon: 'edit', onSelect: () => onEdit({ kind: 'category', category }) },
              ...(first ? [] : [{ label: 'Move up', icon: 'arrow_upward' as const, onSelect: () => onMove(-1) }]),
              ...(last ? [] : [{ label: 'Move down', icon: 'arrow_downward' as const, onSelect: () => onMove(1) }]),
              { label: 'Delete category', icon: 'delete', destructive: true, onSelect: () => onEdit({ kind: 'delete-category', category }) },
            ]}
          />
        </>
      }
    >
      <p className="panel__pad dir-where muted">
        Posted in {channelName(channels, category.channel_id)}
        {category.description ? ` · ${category.description}` : ''}
      </p>
      {servers.length === 0 ? (
        <p className="panel__pad muted">No servers yet. Press Add server to add one with its invite link.</p>
      ) : (
        <ol className="dir-rows" aria-label={`Servers in ${category.title}`}>
          {servers.map((server, i) => (
            <li key={server.id}>
              <span className="dir-av" aria-hidden>
                {initials(server.description)}
              </span>
              <span className="dir-text">
                <b>{server.description}</b>
                <a className="dir-sub" href={`https://discord.gg/${server.invite_code}`} target="_blank" rel="noreferrer">
                  discord.gg/{server.invite_code}
                </a>
              </span>
              <span className="dir-move">
                <IconButton icon="arrow_upward" label={`Move ${server.description} up`} disabled={i === 0} onClick={() => onMoveServer(i, -1)} />
                <IconButton
                  icon="arrow_downward"
                  label={`Move ${server.description} down`}
                  disabled={i === servers.length - 1}
                  onClick={() => onMoveServer(i, 1)}
                />
              </span>
              <RowMenu
                label={`More for ${server.description}`}
                items={[
                  { label: 'Edit', icon: 'edit', onSelect: () => onEdit({ kind: 'server', category, server }) },
                  { label: 'Remove', icon: 'delete', destructive: true, onSelect: () => onEdit({ kind: 'delete-server', server }) },
                ]}
              />
            </li>
          ))}
        </ol>
      )}
    </Panel>
  )
}

/** The messages SahasrahBot posts, as `refresh` builds them: one per category, split every N servers. */
export function messagesFor(dir: ServerDirectory, channelId: string): { title: string; servers: DirectoryServer[] }[] {
  const n = dir.servers_per_message
  return dir.categories
    .filter((c) => c.channel_id === channelId)
    .flatMap((c) => {
      const parts = Math.ceil(c.servers.length / n)
      return Array.from({ length: parts }, (_, i) => ({
        title: parts === 1 ? c.title : `${c.title} - Part ${i + 1}`,
        servers: c.servers.slice(i * n, (i + 1) * n),
      }))
    })
}

function channelIds(dir: ServerDirectory): string[] {
  return [...new Set(dir.categories.map((c) => c.channel_id))]
}

function Preview({ dir, channels }: Readonly<{ dir: ServerDirectory; channels: Channel[] }>) {
  const ids = channelIds(dir)
  const [picked, setPicked] = useState<string>()
  const shown = picked && ids.includes(picked) ? picked : (ids[0] ?? '')
  const messages = messagesFor(dir, shown)
  return (
    <section className="dir-preview" aria-label="Preview in Discord">
      <h2 className="dir-h">Preview of {channelName(channels, shown)}</h2>
      {ids.length > 1 && (
        <fieldset className="filter-chips dir-chips" aria-label="Channel">
          {ids.map((id) => (
            <button key={id} type="button" className="filter-chip" aria-pressed={id === shown} onClick={() => setPicked(id)}>
              {channelName(channels, id)}
            </button>
          ))}
        </fieldset>
      )}
      <div className="dc">
        {messages.length === 0 && <p className="dc__line">Nothing is posted here: its categories have no servers yet.</p>}
        {messages.map((m) => (
          <div className="dc__msg" key={m.title}>
            <span className="dc__av" aria-hidden />
            <div className="dc__body">
              <span className="dc__name">SahasrahBot</span>
              <span className="dc__app">APP</span>
              <div className="dc__line dc__head">{m.title}</div>
              {m.servers.map((s) => (
                <div className="dc__line" key={s.id}>
                  {s.description}: <span className="dc__link">https://discord.gg/{s.invite_code}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function Field({ label, hint, children }: Readonly<{ label: string; hint?: ReactNode; children: (id: string) => ReactNode }>) {
  const id = useId()
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      {children(id)}
      {hint && <span className="field__hint">{hint}</span>}
    </div>
  )
}

type CategoryBody = { title: string; description: string | null; channel_id: string }

function CategoryDialog({
  category,
  channels,
  onClose,
  onSave,
}: Readonly<{ category?: DirectoryCategory; channels: Channel[]; onClose: () => void; onSave: (body: CategoryBody) => Promise<boolean> }>) {
  const [title, setTitle] = useState(category?.title ?? '')
  const [channel, setChannel] = useState(category?.channel_id ?? '')
  const [note, setNote] = useState(category?.description ?? '')
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<string>()
  const known = channels.some((c) => c.id === channel)
  return (
    <FormDialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={category ? 'Edit category' : 'New category'}
      primaryLabel={category ? 'Save' : 'Add category'}
      busy={busy}
      onPrimary={async () => {
        if (!title.trim()) return setProblem('Give the category a title.')
        if (!channel) return setProblem('Pick the channel it’s posted in.')
        setBusy(true)
        const ok = await onSave({ title: title.trim(), description: note.trim() || null, channel_id: channel })
        setBusy(false)
        if (ok) onClose()
      }}
    >
      <div className="stack">
        {problem && <Banner tone="error">{problem}</Banner>}
        <Field label="Title" hint="Posted in bold above the category’s servers.">
          {(id) => <input id={id} className="input" value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />}
        </Field>
        <Field label="Channel" hint="Categories in the same channel are posted there in order.">
          {(id) => (
            <select id={id} className="input" value={channel} onChange={(e) => setChannel(e.target.value)}>
              <option value="">Pick a channel</option>
              {!known && channel && <option value={channel}>{channelName(channels, channel)}</option>}
              {channels.map((c) => (
                <option key={c.id} value={c.id}>
                  {channelName(channels, c.id)}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Field label="Note (optional)" hint="Only shown here, to help other admins.">
          {(id) => <input id={id} className="input" value={note} maxLength={200} onChange={(e) => setNote(e.target.value)} />}
        </Field>
      </div>
    </FormDialog>
  )
}

type ServerBody = { invite: string; description: string; category_id: number }

function ServerDialog({
  guildId,
  category,
  server,
  categories,
  onClose,
  onSave,
}: Readonly<{
  guildId: string
  category: DirectoryCategory
  server?: DirectoryServer
  categories: DirectoryCategory[]
  onClose: () => void
  onSave: (body: ServerBody) => Promise<boolean>
}>) {
  const [invite, setInvite] = useState(server ? `https://discord.gg/${server.invite_code}` : '')
  const [description, setDescription] = useState(server?.description ?? '')
  const [categoryId, setCategoryId] = useState(category.id)
  const [checked, setChecked] = useState<{ text: string; invite?: Invite; error?: string }>()
  const [checking, setChecking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<string>()

  const check = async () => {
    const text = invite.trim()
    if (!text || checked?.text === text) return
    setChecking(true)
    const result = await api.GET('/api/v1/servers/{guild_id}/directory/invite', {
      params: { path: guildPath(guildId), query: { invite: text } },
    })
    setChecking(false)
    try {
      const found = unwrap(result)
      setChecked({ text, invite: found })
      if (!description.trim()) setDescription(found.server_name)
    } catch (e) {
      setChecked({ text, error: (e as Error).message })
    }
  }

  const shownCode = checked?.invite?.code ?? (invite.trim() || 'abc123').replace(/^.*\//, '')
  return (
    <FormDialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={server ? 'Edit server' : `Add a server to ${category.title}`}
      primaryLabel={server ? 'Save' : 'Add server'}
      busy={busy}
      busyLabel="Checking the invite"
      onPrimary={async () => {
        if (!invite.trim()) return setProblem('Paste the server’s invite link.')
        if (!description.trim()) return setProblem('Give the text shown in Discord.')
        setBusy(true)
        const ok = await onSave({ invite: invite.trim(), description: description.trim(), category_id: categoryId })
        setBusy(false)
        if (ok) onClose()
        else setProblem(undefined)
      }}
    >
      <div className="stack">
        {problem && <Banner tone="error">{problem}</Banner>}
        <Field label="Invite link" hint="Use an invite that never expires, or the list will break.">
          {(id) => (
            <input
              id={id}
              className="input"
              value={invite}
              placeholder="https://discord.gg/abc123"
              onChange={(e) => setInvite(e.target.value)}
              onBlur={check}
            />
          )}
        </Field>
        {checking && <p className="muted">Checking the invite with Discord…</p>}
        {!checking && checked?.invite && checked.text === invite.trim() && (
          <output className="dir-found">
            <span className="dir-av" aria-hidden>
              {initials(checked.invite.server_name)}
            </span>
            <span className="dir-text">
              <b>{checked.invite.server_name}</b>
              <span className="dir-sub">
                Invite works
                {checked.invite.expires_at ? ` · expires ${new Date(checked.invite.expires_at).toLocaleDateString()}` : ' · never expires'}
                {checked.invite.member_count != null && ` · ${checked.invite.member_count.toLocaleString()} members`}
              </span>
            </span>
            <Icon name="check_circle" />
          </output>
        )}
        {!checking && checked?.error && checked.text === invite.trim() && <Banner tone="error">{checked.error}</Banner>}
        <Field label="Text shown in Discord" hint={`Posted as “${description.trim() || 'Text'}: https://discord.gg/${shownCode}”.`}>
          {(id) => <input id={id} className="input" value={description} maxLength={200} onChange={(e) => setDescription(e.target.value)} />}
        </Field>
        {server && categories.length > 1 && (
          <Field label="Category" hint="Moving it puts it last in the other category.">
            {(id) => (
              <select id={id} className="input" value={categoryId} onChange={(e) => setCategoryId(Number(e.target.value))}>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            )}
          </Field>
        )}
      </div>
    </FormDialog>
  )
}

function PostDialog({
  dir,
  channels,
  onClose,
  onPost,
}: Readonly<{ dir: ServerDirectory; channels: Channel[]; onClose: () => void; onPost: () => Promise<boolean> }>) {
  const [busy, setBusy] = useState(false)
  const ids = channelIds(dir)
  return (
    <FormDialog
      open
      onOpenChange={(open) => !open && onClose()}
      title="Post the server list to Discord?"
      primaryLabel={`Post ${dir.categories.length} ${dir.categories.length === 1 ? 'category' : 'categories'}`}
      busy={busy}
      busyLabel="Posting"
      onPrimary={async () => {
        setBusy(true)
        const ok = await onPost()
        setBusy(false)
        if (ok) onClose()
      }}
    >
      <div className="stack">
        <p>SahasrahBot deletes its own messages in these channels, then posts the list again:</p>
        <ul className="dir-list">
          {ids.map((id) => (
            <li key={id}>
              <b>{channelName(channels, id)}</b>:{' '}
              {dir.categories
                .filter((c) => c.channel_id === id)
                .map((c) => `${c.title} (${c.servers.length})`)
                .join(', ')}
            </li>
          ))}
        </ul>
        <p className="muted">Other people’s messages in those channels are left alone.</p>
      </div>
    </FormDialog>
  )
}
