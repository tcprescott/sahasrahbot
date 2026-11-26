import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { api, unwrap, type RoleMenu, type RoleMenuServerOptions, type RoleMenuStyle } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import {
  ActionsMenu,
  Banner,
  Button,
  ConfirmDialog,
  FormDialog,
  Icon,
  IconButton,
  PageHeader,
  Panel,
  RowMenu,
  type MenuItem,
} from '../components'
import { browser } from '../lib/browser'
import { move } from '../ranked/ranking'
import { DiscordPreview, Emoji } from './DiscordPreview'
import { STYLES, styleMax } from './labels'
import { editPath, listPath, messageUrl } from './paths'
import './rolemenus.css'


interface OptionDraft {
  key: number
  id?: number
  roleId: string
  label: string
  emoji: string
  description: string
}

interface Draft {
  guildId: string
  channelId: string
  title: string
  description: string
  style: RoleMenuStyle
  singleChoice: boolean
  options: OptionDraft[]
}

let nextKey = 1

function fromMenu(menu: RoleMenu | undefined, guildId: string, channel: string | null): Draft {
  if (!menu) {
    return {
      guildId,
      channelId: channel ?? '',
      title: '',
      description: '',
      style: 'buttons',
      singleChoice: false,
      options: [],
    }
  }
  return {
    guildId: menu.guild_id,
    channelId: menu.channel_id,
    title: menu.title,
    description: menu.description ?? '',
    style: menu.style,
    singleChoice: menu.single_choice,
    options: menu.options.map((o) => ({
      key: nextKey++,
      id: o.id,
      roleId: o.role_id,
      label: o.label,
      emoji: o.emoji ?? '',
      description: o.description ?? '',
    })),
  }
}

function toBody(d: Draft) {
  return {
    guild_id: d.guildId,
    channel_id: d.channelId,
    title: d.title.trim(),
    description: d.description.trim() || null,
    style: d.style,
    single_choice: d.singleChoice,
    options: d.options.map((o) => ({
      id: o.id ?? null,
      role_id: o.roleId,
      label: o.label.trim(),
      emoji: o.emoji.trim() || null,
      description: o.description.trim() || null,
    })),
  }
}

/**
 * /servers/:guildId/role-menus/new and /servers/:guildId/role-menus/:menuId, in the
 * server page's Role menus section. One form; saving posts or redraws the menu in Discord.
 */
export function RoleMenuEditor({ guildId, menuId }: Readonly<{ guildId: string; menuId?: number }>) {
  // Wrapped, because Loaded treats an undefined result as still loading (and a new menu has none).
  const query = useQuery(`role-menus/form/${guildId}/${menuId ?? 'new'}`, async () => ({
    menu: menuId === undefined ? undefined : unwrap(await api.GET('/api/v1/role-menus/{menu_id}', { params: { path: { menu_id: menuId } } })),
  }))
  return (
    <Loaded query={query} label="Loading the role menu">
      {({ menu }) => (
        // A new key per menu, so the form starts over when it changes.
        <Form key={menu?.id ?? 'new'} guildId={guildId} menu={menu} onSaved={query.reload} />
      )}
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
      {hint && <span className="field__hint">{hint}</span>}
    </div>
  )
}

function useServerOptions(guildId: string) {
  return useQuery(guildId ? `role-menus/servers/${guildId}` : null, async () =>
    // The id goes in the URL as the string it is: Discord ids are too big for a JS number.
    unwrap(await api.GET('/api/v1/role-menus/servers/{guild_id}', { params: { path: { guild_id: guildId as unknown as number } } })),
  )
}

function Form({ guildId, menu, onSaved }: Readonly<{ guildId: string; menu: RoleMenu | undefined; onSaved: () => void }>) {
  const navigate = useNavigate()
  const notice = (useLocation().state as { notice?: string } | null)?.notice
  const [params] = useSearchParams()
  const [linkedChannel] = useState(() => !menu && !!params.get('channel'))
  const [draft, setDraft] = useState(() => fromMenu(menu, guildId, params.get('channel')))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const [saved, setSaved] = useState(notice)
  const [editing, setEditing] = useState<OptionDraft | 'new'>()
  const [confirm, setConfirm] = useState<'repost' | 'delete'>()
  const options = useServerOptions(draft.guildId)
  const errorRef = useRef<HTMLDivElement>(null)

  const legacy = menu !== undefined && !menu.posted_by_bot
  const set = (patch: Partial<Draft>) => {
    setDraft((d) => ({ ...d, ...patch }))
    setSaved(undefined)
  }
  const channels = options.data?.channels ?? []
  const roles = options.data?.roles ?? []
  const roleName = (roleId: string) =>
    roles.find((r) => r.id === roleId)?.name ?? menu?.options.find((o) => o.role_id === roleId)?.role_name ?? 'A deleted role'
  const max = styleMax(draft.style)

  useEffect(() => {
    const first = channels[0]
    if (!first || menu) return
    const usable = (cid: string) => !!cid && (!linkedChannel || channels.some((c) => c.id === cid))
    if (!usable(draft.channelId)) setDraft((d) => (usable(d.channelId) ? d : { ...d, channelId: first.id }))
  }, [channels, draft.channelId, linkedChannel, menu])

  useEffect(() => {
    if (error) errorRef.current?.scrollIntoView({ block: 'nearest' })
  }, [error])

  const save = async () => {
    setBusy(true)
    setError(undefined)
    try {
      const body = toBody(draft)
      if (menu) {
        unwrap(await api.PUT('/api/v1/role-menus/{menu_id}', { params: { path: { menu_id: menu.id } }, body }))
        setSaved('Saved. The menu in Discord is updated.')
        onSaved()
      } else {
        const made = unwrap(await api.POST('/api/v1/role-menus', { body }))
        navigate(editPath(guildId, made.id), { replace: true, state: { notice: `“${made.title}” is posted in Discord.` } })
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const act = async (kind: 'repost' | 'delete') => {
    if (!menu) return
    const path = { params: { path: { menu_id: menu.id } } }
    try {
      if (kind === 'repost') {
        unwrap(await api.POST('/api/v1/role-menus/{menu_id}/repost', path))
        setSaved('Reposted. SahasrahBot posted the menu as a new message.')
        onSaved()
      } else {
        unwrap(await api.DELETE('/api/v1/role-menus/{menu_id}', path))
        navigate(listPath(guildId), { state: { notice: `“${menu.title}” is deleted.` } })
      }
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const url = menu ? messageUrl(menu) : undefined
  const actions: MenuItem[] = menu
    ? [
        ...(url ? [{ label: 'Jump to the message', icon: 'open_in_new' as const, onSelect: () => browser.open(url) }] : []),
        { label: 'Repost in Discord', icon: 'refresh', onSelect: () => setConfirm('repost') },
        { label: 'Delete menu', icon: 'delete', destructive: true, onSelect: () => setConfirm('delete') },
      ]
    : []

  const list = draft.options
  const moveRow = (key: number, by: -1 | 1) => {
    const order = move(
      list.map((o) => o.key),
      key,
      by,
    )
    set({ options: order.map((k) => list.find((o) => o.key === k)!) })
  }

  return (
    <>
      <Link to={listPath(guildId)} className="back-link">
        <Icon name="chevron_left" size={20} />
        Role menus
      </Link>
      <PageHeader
        title={menu ? menu.title : 'New role menu'}
        lede={
          menu ? (
            <>
              {menu.channel_name ?? 'A channel SahasrahBot can’t see'}
              {url && (
                <>
                  {' · '}
                  <a href={url} target="_blank" rel="noreferrer">
                    Jump to the message
                  </a>
                </>
              )}
            </>
          ) : (
            'Nothing is posted until you press Create and post.'
          )
        }
        actions={actions.length > 0 && <ActionsMenu items={actions} />}
      />
      <div className="stack">
        {saved && <Banner tone="accent">{saved}</Banner>}
        {error && (
          <div ref={errorRef}>
            <Banner tone="error">{error}</Banner>
          </div>
        )}
        {legacy && (
          <Banner
            tone="info"
            action={
              <Button variant="outline" size="sm" onClick={() => setConfirm('repost')}>
                Repost as SahasrahBot
              </Button>
            }
          >
            This menu is on a message SahasrahBot didn't post, so it can only use reactions. Repost it to use buttons or a dropdown.
          </Banner>
        )}
        {menu && menu.problems.length > 0 && (
          <Banner tone="warning">
            {menu.problems.length === 1 ? (
              menu.problems[0]
            ) : (
              <ul className="rm-problems">
                {menu.problems.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            )}
          </Banner>
        )}
        <div className="rm-split">
          <div className="stack">
            <Panel title="Basics">
              <div className="panel__pad stack">
                <div className="field-grid">
                  <Field
                    id="rm-channel"
                    label="Channel"
                    hint={legacy ? 'Repost it to move it.' : menu ? 'Moving it posts a new message there.' : undefined}
                  >
                    <select
                      id="rm-channel"
                      className="input"
                      value={draft.channelId}
                      disabled={legacy || options.loading}
                      onChange={(e) => set({ channelId: e.target.value })}
                    >
                      {!draft.channelId && <option value="">{options.loading ? 'Loading channels…' : 'Pick a channel'}</option>}
                      {draft.channelId && !channels.some((c) => c.id === draft.channelId) && (
                        <option value={draft.channelId}>{options.loading ? 'Loading channels…' : (menu?.channel_name ?? 'A channel SahasrahBot can’t post in')}</option>
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
                <Field id="rm-title" label="Title">
                  <input id="rm-title" className="input" value={draft.title} maxLength={256} onChange={(e) => set({ title: e.target.value })} />
                </Field>
                <Field id="rm-description" label="Description" hint="Optional. Shown under the title in Discord.">
                  <textarea
                    id="rm-description"
                    className="input"
                    rows={2}
                    maxLength={4000}
                    value={draft.description}
                    onChange={(e) => set({ description: e.target.value })}
                  />
                </Field>
                <fieldset className="field choice-fieldset">
                  <legend className="field__label">How people pick</legend>
                  <div className="choice-tiles">
                    {STYLES.map((s) => (
                      <label key={s.key} className="choice-tile">
                        <input
                          type="radio"
                          name="style"
                          value={s.key}
                          checked={draft.style === s.key}
                          disabled={legacy && s.key !== 'reactions'}
                          onChange={() => set({ style: s.key })}
                        />
                        <div>
                          <b>{s.name}</b>
                          <span className="choice-tile__desc">{s.description}</span>
                        </div>
                      </label>
                    ))}
                  </div>
                </fieldset>
                <label className="t-check">
                  <input type="checkbox" checked={draft.singleChoice} onChange={(e) => set({ singleChoice: e.target.checked })} /> People can
                  hold only one role from this menu
                </label>
              </div>
            </Panel>

            <Panel
              title={`Roles (${list.length} of ${max})`}
              actions={
                <Button variant="outline" size="sm" icon="add" disabled={list.length >= max || !draft.guildId} onClick={() => setEditing('new')}>
                  Add role
                </Button>
              }
            >
              {list.length === 0 ? (
                <p className="panel__pad rm-muted">No roles yet. Press Add role to add the first.</p>
              ) : (
                <ol className="rm-opts">
                  {list.map((o, i) => {
                    const name = o.label.trim() || `role ${i + 1}`
                    return (
                      <li key={o.key}>
                        <span className="rm-opt__emoji">{o.emoji ? <Emoji text={o.emoji} size={24} /> : <Icon name="label" />}</span>
                        <span className="rm-opt__text">
                          <b>{o.label || 'Unnamed role'}</b>
                          <span className="rm-muted">
                            gives <span className="rm-role">{roleName(o.roleId)}</span>
                            {o.description && ` · ${o.description}`}
                          </span>
                          {draft.style === 'reactions' && !o.emoji && <span className="rm-problem">Needs an emoji for reactions</span>}
                        </span>
                        <IconButton icon="arrow_upward" label={`Move ${name} up`} disabled={i === 0} onClick={() => moveRow(o.key, -1)} />
                        <IconButton icon="arrow_downward" label={`Move ${name} down`} disabled={i === list.length - 1} onClick={() => moveRow(o.key, 1)} />
                        <RowMenu
                          label={`More for ${name}`}
                          items={[
                            { label: 'Edit', icon: 'edit', onSelect: () => setEditing(o) },
                            { label: 'Remove', icon: 'delete', destructive: true, onSelect: () => set({ options: list.filter((x) => x.key !== o.key) }) },
                          ]}
                        />
                      </li>
                    )
                  })}
                </ol>
              )}
            </Panel>

            <div className="t-actions t-actions--end">
              <Button variant="ghost" asChild>
                <Link to={listPath(guildId)}>Cancel</Link>
              </Button>
              <Button icon="check_circle" busy={busy} busyLabel={menu ? 'Saving' : 'Posting'} onClick={save}>
                {menu ? 'Save and update Discord' : 'Create and post'}
              </Button>
            </div>
          </div>
          <div className="rm-preview">
            <h2 className="rm-preview__title">Preview in Discord</h2>
            <DiscordPreview
              menu={{
                title: draft.title,
                description: draft.description,
                style: draft.style,
                singleChoice: draft.singleChoice,
                options: list.map((o) => ({ key: o.key, label: o.label, emoji: o.emoji, description: o.description })),
              }}
            />
          </div>
        </div>
      </div>

      <OptionDialog
        option={editing}
        server={options.data}
        taken={list.filter((o) => editing === 'new' || o.key !== editing?.key).map((o) => o.roleId)}
        needsEmoji={draft.style === 'reactions'}
        onClose={() => setEditing(undefined)}
        onDone={(o) => {
          set({ options: editing === 'new' ? [...list, o] : list.map((x) => (x.key === o.key ? o : x)) })
          setEditing(undefined)
        }}
      />
      <ConfirmDialog
        open={confirm === 'repost'}
        onOpenChange={(open) => !open && setConfirm(undefined)}
        title="Repost this menu?"
        action="Repost"
        onConfirm={async () => act('repost')}
      >
        {legacy
          ? 'SahasrahBot posts the menu as its own message in the same channel and takes its reactions off the old one. The old message stays until its author deletes it.'
          : 'SahasrahBot posts the menu as a new message in its channel and deletes the old one.'}{' '}
        People keep the roles they have.
      </ConfirmDialog>
      <ConfirmDialog
        open={confirm === 'delete'}
        onOpenChange={(open) => !open && setConfirm(undefined)}
        title="Delete this menu?"
        action="Delete"
        onConfirm={async () => act('delete')}
      >
        The menu and its Discord message are deleted. People keep the roles they have. This can't be undone.
      </ConfirmDialog>
    </>
  )
}

/** Adding or editing one role: which role, its label, emoji and description. */
function OptionDialog({
  option,
  server,
  taken,
  needsEmoji,
  onClose,
  onDone,
}: Readonly<{
  option: OptionDraft | 'new' | undefined
  server: RoleMenuServerOptions | undefined
  taken: string[]
  needsEmoji: boolean
  onClose: () => void
  onDone: (option: OptionDraft) => void
}>) {
  const [form, setForm] = useState<OptionDraft>()
  const [problem, setProblem] = useState<string>()
  useEffect(() => {
    setProblem(undefined)
    if (option === 'new') setForm({ key: nextKey++, roleId: '', label: '', emoji: '', description: '' })
    else setForm(option)
  }, [option])
  if (!form) return null
  const roles = server?.roles ?? []
  const emojis = server?.emojis ?? []
  const patch = (p: Partial<OptionDraft>) => setForm({ ...form, ...p })
  const pickRole = (roleId: string) => {
    const role = roles.find((r) => r.id === roleId)
    // Start the label from the role's name, unless one was typed.
    const label = form.label.trim() ? form.label : (role?.name.replace(/^@/, '') ?? '')
    patch({ roleId, label: label.slice(0, 80) })
  }
  const done = () => {
    if (!form.roleId) return setProblem('Pick a role.')
    if (!form.label.trim()) return setProblem('Give it a label.')
    if (needsEmoji && !form.emoji.trim()) return setProblem('Reaction menus need an emoji for every role.')
    onDone(form)
  }
  return (
    <FormDialog
      open={option !== undefined}
      onOpenChange={(open) => !open && onClose()}
      title={option === 'new' ? 'Add a role' : 'Edit role'}
      primaryLabel={option === 'new' ? 'Add' : 'Done'}
      onPrimary={done}
    >
      <div className="stack">
        {problem && <Banner tone="error">{problem}</Banner>}
        <Field id="rm-opt-role" label="Role" hint="Roles above SahasrahBot's highest role can't be given, so they're greyed out.">
          <select id="rm-opt-role" className="input" value={form.roleId} onChange={(e) => pickRole(e.target.value)}>
            <option value="">Pick a role</option>
            {form.roleId && !roles.some((r) => r.id === form.roleId) && <option value={form.roleId}>A deleted role</option>}
            {roles.map((r) => (
              <option key={r.id} value={r.id} disabled={!r.assignable || (taken.includes(r.id) && r.id !== form.roleId)}>
                {r.name}
                {r.assignable ? '' : ' (SahasrahBot can’t give this)'}
                {taken.includes(r.id) && r.id !== form.roleId ? ' (already on this menu)' : ''}
              </option>
            ))}
          </select>
        </Field>
        <Field id="rm-opt-label" label="Label" hint="What people see on the button or in the list.">
          <input id="rm-opt-label" className="input" maxLength={80} value={form.label} onChange={(e) => patch({ label: e.target.value })} />
        </Field>
        <Field
          id="rm-opt-emoji"
          label={needsEmoji ? 'Emoji' : 'Emoji (optional)'}
          hint="Type or paste an emoji. For a custom one, pick it below or paste it as <:name:id>."
        >
          <div className="field__row">
            <input id="rm-opt-emoji" className="input grow" maxLength={100} value={form.emoji} onChange={(e) => patch({ emoji: e.target.value })} />
            <span className="rm-emoji-preview" aria-hidden="true">
              <Emoji text={form.emoji.trim()} size={24} />
            </span>
          </div>
        </Field>
        {emojis.length > 0 && (
          <div className="rm-emoji-picker" role="group" aria-label="This server's emoji">
            {emojis.slice(0, 60).map((e) => (
              <button key={e.id} type="button" className="rm-emoji-pick" aria-label={e.name} onClick={() => patch({ emoji: e.name })}>
                <Emoji text={e.name} size={22} />
              </button>
            ))}
          </div>
        )}
        <Field id="rm-opt-description" label="Description (optional)" hint="Shown in the dropdown and the reactions list. Up to 100 characters.">
          <input
            id="rm-opt-description"
            className="input"
            maxLength={100}
            value={form.description}
            onChange={(e) => patch({ description: e.target.value })}
          />
        </Field>
      </div>
    </FormDialog>
  )
}
