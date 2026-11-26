import { useEffect, useState } from 'react'
import { api, unwrap, type Inquiry, type InquiryCheck } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { Banner, Button, ConfirmDialog, FormDialog, Icon, Panel, RowMenu, type MenuItem } from '../components'
import { browser } from '../lib/browser'
import { useServer } from './ServerContext'

const gid = (id: string) => ({ guild_id: id as unknown as number })

/** The Inquiry buttons panel of a server's Settings: list, post (/inquiry from the web) and remove. */
export function InquiriesPanel() {
  const { server } = useServer()
  const query = useQuery(`servers/${server.id}/inquiries`, async () =>
    unwrap(await api.GET('/api/v1/servers/{guild_id}/inquiries', { params: { path: gid(server.id) } })).inquiries,
  )
  const [posting, setPosting] = useState(false)
  const [removing, setRemoving] = useState<Inquiry>()
  const [notice, setNotice] = useState<{ tone: 'accent' | 'error'; text: string }>()

  const remove = async (inquiry: Inquiry) => {
    try {
      unwrap(
        await api.DELETE('/api/v1/servers/{guild_id}/inquiries/{message_id}', {
          params: { path: { ...gid(server.id), message_id: inquiry.message_id as unknown as number } },
        }),
      )
      setNotice({ tone: 'accent', text: 'Inquiry button removed. Threads it opened are still there.' })
      query.reload()
    } catch (e) {
      setNotice({ tone: 'error', text: (e as Error).message })
    }
  }

  const menu = (i: Inquiry): MenuItem[] => {
    const items: MenuItem[] = []
    if (i.jump_url) {
      const url = i.jump_url
      items.push({ label: 'Jump to the message', icon: 'open_in_new', onSelect: () => browser.openTab(url) })
    }
    items.push({ label: 'Remove', icon: 'delete', destructive: true, onSelect: () => setRemoving(i) })
    return items
  }

  return (
    <Panel
      title="Inquiry buttons"
      actions={
        <Button variant="outline" icon="add" onClick={() => setPosting(true)}>
          Post an inquiry button
        </Button>
      }
    >
      {notice && (
        <div className="server-settings__pad">
          <Banner tone={notice.tone}>{notice.text}</Banner>
        </div>
      )}
      <Loaded query={query} label="Loading inquiry buttons">
        {(inquiries) =>
          inquiries.length === 0 ? (
            <p className="server-settings__pad server-muted">
              No inquiry buttons yet. Members press one to open a private thread with a role, for questions they'd
              rather not ask in public. Buttons posted before November 2026 still work but aren't listed here.
            </p>
          ) : (
            <ul className="inquiry-rows" aria-label="Inquiry buttons">
              {inquiries.map((i) => {
                const channel = i.channel_name ?? 'A channel SahasrahBot can’t see'
                return (
                  <li key={i.message_id} className="inquiry-row">
                    <Icon name="forum" />
                    <span className="inquiry-row__text">
                      <b>{channel}</b>
                      <span className="server-muted">
                        Opens a private thread with {i.role_name ?? 'a deleted role'}
                        {i.created && ` · Posted ${new Date(i.created).toLocaleDateString()}`}
                      </span>
                    </span>
                    <RowMenu label={`More for the button in ${channel}`} items={menu(i)} />
                  </li>
                )
              })}
            </ul>
          )
        }
      </Loaded>
      {posting && (
        <PostInquiryDialog
          onClose={() => setPosting(false)}
          onPosted={(i) => {
            setPosting(false)
            setNotice({ tone: 'accent', text: `Inquiry button posted in ${i.channel_name ?? 'the channel'}.` })
            query.reload()
          }}
        />
      )}
      <ConfirmDialog
        open={removing !== undefined}
        onOpenChange={(open) => !open && setRemoving(undefined)}
        title="Remove this inquiry button?"
        action="Remove"
        onConfirm={async () => {
          if (removing) await remove(removing)
        }}
      >
        SahasrahBot deletes the message in {removing?.channel_name ?? 'its channel'}. Threads it already opened stay.
      </ConfirmDialog>
    </Panel>
  )
}

function PostInquiryDialog({ onClose, onPosted }: Readonly<{ onClose: () => void; onPosted: (i: Inquiry) => void }>) {
  const { server } = useServer()
  const [channelId, setChannelId] = useState(server.text_channels[0]?.id ?? '')
  const [roleId, setRoleId] = useState(server.roles[0]?.id ?? '')
  const [checks, setChecks] = useState<InquiryCheck[]>()
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)
  const channelName = server.text_channels.find((c) => c.id === channelId)?.name ?? 'the channel'

  useEffect(() => {
    setChecks(undefined)
    if (!channelId || !roleId) return
    let live = true
    api
      .POST('/api/v1/servers/{guild_id}/inquiries/check', {
        params: { path: gid(server.id) },
        body: { channel_id: channelId, role_id: roleId },
      })
      .then((result) => {
        if (!live) return
        setChecks(unwrap(result).checks)
        setError(undefined)
      })
      .catch((e: unknown) => live && setError((e as Error).message))
    return () => {
      live = false
    }
  }, [server.id, channelId, roleId])

  const ready = checks !== undefined && checks.every((c) => c.ok)
  const post = async () => {
    setBusy(true)
    try {
      onPosted(
        unwrap(
          await api.POST('/api/v1/servers/{guild_id}/inquiries', {
            params: { path: gid(server.id) },
            body: { channel_id: channelId, role_id: roleId },
          }),
        ),
      )
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <FormDialog
      open
      onOpenChange={(open) => !open && onClose()}
      title="Post an inquiry button"
      description="Members press it to open a private thread with a role, for questions they'd rather not ask in public."
      primaryLabel={`Post in ${channelName}`}
      onPrimary={post}
      primaryDisabled={!ready}
      busy={busy}
      busyLabel="Posting"
    >
      <div className="inquiry-form">
        <div className="field">
          <label className="field__label" htmlFor="inquiry-channel">
            Channel
          </label>
          <select id="inquiry-channel" className="input" value={channelId} onChange={(e) => setChannelId(e.target.value)}>
            {server.text_channels.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <span className="field__hint">Where the button is posted. Members should be able to see it but not send messages there.</span>
        </div>
        <div className="field">
          <label className="field__label" htmlFor="inquiry-role">
            Who answers
          </label>
          <select id="inquiry-role" className="input" value={roleId} onChange={(e) => setRoleId(e.target.value)}>
            {server.roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
          <span className="field__hint">Pressing the button opens a private thread with the member and this role.</span>
        </div>
        {checks && (
          <ul className="inquiry-checks" aria-label="Channel checks">
            {checks.map((c) => (
              <li key={c.text} className={c.ok ? 'inquiry-check' : 'inquiry-check inquiry-check--bad'}>
                <Icon name={c.ok ? 'check_circle' : 'error'} size={18} />
                <span>{c.text}</span>
              </li>
            ))}
          </ul>
        )}
        {error && <Banner tone="error">{error}</Banner>}
      </div>
    </FormDialog>
  )
}
