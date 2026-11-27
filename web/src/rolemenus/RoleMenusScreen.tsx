import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, unwrap, type RoleMenu } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { Banner, Button, Chip, ConfirmDialog, Icon, type MenuItem } from '../components'
import { DataTable } from '../kit/DataTable'
import { browser } from '../lib/browser'
import { Emoji } from './DiscordPreview'
import { styleName } from './labels'
import { editPath, messageUrl, newPath } from './paths'
import './rolemenus.css'


type Pending = { kind: 'repost' | 'delete'; menu: RoleMenu }

export function StyleChip({ menu }: Readonly<{ menu: Pick<RoleMenu, 'style'> }>) {
  return <Chip tone={menu.style === 'reactions' ? 'neutral' : 'info'}>{styleName(menu.style)}</Chip>
}

/** The roles as their emoji, or their labels for a menu without emoji. */
function RoleSummary({ menu }: Readonly<{ menu: RoleMenu }>) {
  const withEmoji = menu.options.filter((o) => o.emoji)
  if (withEmoji.length === 0) return <span className="rm-labels">{menu.options.map((o) => o.label).join(', ')}</span>
  return (
    <span className="rm-emojis" aria-label={menu.options.map((o) => o.label).join(', ')}>
      {withEmoji.map((o) => (
        <Emoji key={o.id} text={o.emoji} />
      ))}
    </span>
  )
}

/** /servers/:guildId/role-menus — the server's role menus, as a section of its server page. */
export function RoleMenusSection({ guildId }: Readonly<{ guildId: string }>) {
  const navigate = useNavigate()
  const notice = (useLocation().state as { notice?: string } | null)?.notice
  const query = useQuery(`role-menus/${guildId}`, async () => {
    const list = unwrap(await api.GET('/api/v1/role-menus', { params: { query: { guild_id: guildId } } }))
    return { menus: list.menus }
  })
  const [pending, setPending] = useState<Pending>()
  const [done, setDone] = useState<string>()
  const [error, setError] = useState<string>()

  const act = async ({ kind, menu }: Pending) => {
    const path = { params: { path: { menu_id: menu.id } } }
    try {
      if (kind === 'repost') unwrap(await api.POST('/api/v1/role-menus/{menu_id}/repost', path))
      else unwrap(await api.DELETE('/api/v1/role-menus/{menu_id}', path))
      setError(undefined)
      setDone(kind === 'repost' ? `“${menu.title}” is reposted.` : `“${menu.title}” is deleted.`)
      query.reload()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <Loaded query={query} label="Loading role menus">
      {({ menus }) => {
        const rowMenu = (m: RoleMenu): MenuItem[] => {
          const url = messageUrl(m)
          return [
            { label: 'Edit', icon: 'edit', onSelect: () => navigate(editPath(guildId, m.id)) },
            ...(url ? [{ label: 'Jump to the message', icon: 'open_in_new' as const, onSelect: () => browser.openTab(url) }] : []),
            { label: 'Repost in Discord', icon: 'refresh', onSelect: () => setPending({ kind: 'repost', menu: m }) },
            { label: 'Delete', icon: 'delete', destructive: true, onSelect: () => setPending({ kind: 'delete', menu: m }) },
          ]
        }
        return (
          <>
            <div className="rm-section-head">
              <p className="rm-muted">Messages people use to give themselves roles.</p>
              <Button icon="add" asChild>
                <Link to={newPath(guildId)}>New role menu</Link>
              </Button>
            </div>
            <div className="stack">
              {(done ?? notice) && <Banner tone="accent">{done ?? notice}</Banner>}
              {error && <Banner tone="error">{error}</Banner>}
              <DataTable
                  label="Role menus"
                  rows={menus}
                  rowKey={(m) => m.id}
                  empty={{ icon: 'label', title: 'No role menus yet', body: 'Press New role menu to make one.' }}
                  columns={[
                    {
                      key: 'title',
                      header: 'Menu',
                      primary: true,
                      render: (m) => (
                        <span>
                          <Link to={editPath(guildId, m.id)}>{m.title}</Link>
                          {m.problems.length > 0 && (
                            <span className="rm-problem">
                              <Icon name="warning" size={16} /> {m.problems[0]}
                              {m.problems.length > 1 && ` (+${m.problems.length - 1} more)`}
                            </span>
                          )}
                        </span>
                      ),
                    },
                    { key: 'channel', header: 'Channel', render: (m) => m.channel_name ?? 'A channel SahasrahBot can’t see' },
                    { key: 'roles', header: 'Roles', render: (m) => <RoleSummary menu={m} /> },
                    { key: 'style', header: 'Style', render: (m) => <StyleChip menu={m} /> },
                  ]}
                  rowMenu={rowMenu}
                  rowMenuLabel={(m) => `More for ${m.title}`}
                />
            </div>
            <ConfirmDialog
              open={pending?.kind === 'repost'}
              onOpenChange={(open) => !open && setPending(undefined)}
              title="Repost this menu?"
              action="Repost"
              onConfirm={async () => pending && act(pending)}
            >
              SahasrahBot posts “{pending?.menu.title}” as a new message in its channel and deletes its old one. People keep
              the roles they have.
            </ConfirmDialog>
            <ConfirmDialog
              open={pending?.kind === 'delete'}
              onOpenChange={(open) => !open && setPending(undefined)}
              title="Delete this menu?"
              action="Delete"
              onConfirm={async () => pending && act(pending)}
            >
              “{pending?.menu.title}” and its Discord message are deleted. People keep the roles they have. This can't be
              undone.
            </ConfirmDialog>
          </>
        )
      }}
    </Loaded>
  )
}
