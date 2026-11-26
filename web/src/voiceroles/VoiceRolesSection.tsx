import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, unwrap, type VoiceRole, type VoiceRoles } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { Banner, Button, ConfirmDialog, FormDialog, Icon } from '../components'
import { DataTable } from '../kit/DataTable'
import './voiceroles.css'

/** /servers/:guildId/voice-roles — the server page's Voice roles tab. */
export function VoiceRolesSection() {
  const guildId = useParams().guildId ?? ''
  const query = useQuery(`voice-roles:${guildId}`, async () =>
    unwrap(await api.GET('/api/v1/servers/{guild_id}/voice-roles', { params: { path: { guild_id: guildId } } })),
  )
  const [adding, setAdding] = useState(false)
  const [removing, setRemoving] = useState<VoiceRole>()
  const [error, setError] = useState<string>()
  const [notice, setNotice] = useState<string>()

  const remove = async (row: VoiceRole) => {
    try {
      unwrap(
        await api.DELETE('/api/v1/servers/{guild_id}/voice-roles/{voice_role_id}', {
          params: { path: { guild_id: guildId, voice_role_id: row.id } },
        }),
      )
      setError(undefined)
      setNotice(undefined)
      query.reload()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <Loaded query={query} label="Loading voice roles">
      {(data) => (
        <div className="stack">
          <div className="vr-head">
            <p className="vr-head__lede">People get these roles while they're in the voice channel, and lose them when they leave.</p>
            <Button icon="add" onClick={() => setAdding(true)}>
              Add voice role
            </Button>
          </div>
          {notice && <Banner tone="accent">{notice}</Banner>}
          {error && <Banner tone="error">{error}</Banner>}
          <DataTable
            label="Voice roles"
            rows={data.voice_roles}
            rowKey={(v) => v.id}
            empty={{
              icon: 'volume_up',
              title: 'No voice roles yet',
              body: 'Press Add voice role to give people a role while they’re in a voice channel.',
            }}
            columns={[
              {
                key: 'channel',
                header: 'Voice channel',
                primary: true,
                render: (v) => (
                  <span>
                    <span className="vr-channel">
                      <Icon name="volume_up" size={18} />
                      {v.voice_channel_name ?? 'Deleted channel'}
                    </span>
                    {v.problem && (
                      <span className="vr-problem">
                        <Icon name="warning" size={16} /> {v.problem}
                      </span>
                    )}
                  </span>
                ),
              },
              { key: 'role', header: 'Role given', render: (v) => <span className="vr-role">{v.role_name ?? 'Deleted role'}</span> },
            ]}
            rowMenu={(v) => [{ label: 'Remove', icon: 'delete', destructive: true, onSelect: () => setRemoving(v) }]}
            rowMenuLabel={(v) => `More for ${v.voice_channel_name ?? 'deleted channel'} and ${v.role_name ?? 'deleted role'}`}
          />
          <AddDialog
            open={adding}
            guildId={guildId}
            data={data}
            onClose={() => setAdding(false)}
            onAdded={(row) => {
              setAdding(false)
              setNotice(`${row.voice_channel_name} now gives ${row.role_name}. People already in the channel get it the next time they join.`)
              query.reload()
            }}
          />
          <ConfirmDialog
            open={removing !== undefined}
            onOpenChange={(o) => !o && setRemoving(undefined)}
            title="Remove this voice role?"
            action="Remove"
            onConfirm={async () => {
              if (removing) await remove(removing)
            }}
          >
            {removing && (
              <>
                {removing.voice_channel_name ?? 'The deleted channel'} will stop giving {removing.role_name ?? 'the deleted role'}. Anyone in the channel
                now keeps the role until they leave.
              </>
            )}
          </ConfirmDialog>
        </div>
      )}
    </Loaded>
  )
}

function AddDialog({
  open,
  guildId,
  data,
  onClose,
  onAdded,
}: Readonly<{ open: boolean; guildId: string; data: VoiceRoles; onClose: () => void; onAdded: (row: VoiceRole) => void }>) {
  const [channel, setChannel] = useState('')
  const [role, setRole] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const roles = data.roles.filter((r) => r.assignable)
  const hidden = data.roles.length - roles.length

  const close = () => {
    setChannel('')
    setRole('')
    setError(undefined)
    onClose()
  }

  const add = async () => {
    if (!channel || !role) {
      setError('Pick a voice channel and a role.')
      return
    }
    setBusy(true)
    try {
      const row = unwrap(
        await api.POST('/api/v1/servers/{guild_id}/voice-roles', {
          params: { path: { guild_id: guildId } },
          body: { voice_channel_id: channel, role_id: role },
        }),
      )
      setChannel('')
      setRole('')
      setError(undefined)
      onAdded(row)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <FormDialog
      open={open}
      onOpenChange={(o) => !o && close()}
      title="Add voice role"
      size="sm"
      primaryLabel="Add voice role"
      onPrimary={() => void add()}
      busy={busy}
      busyLabel="Adding the voice role"
    >
      <div className="stack">
        {error && <Banner tone="error">{error}</Banner>}
        {data.voice_channels.length === 0 ? (
          <Banner tone="info">This server has no voice channels SahasrahBot can see.</Banner>
        ) : (
          <div className="field">
            <label className="field__label" htmlFor="vr-channel">
              Voice channel
            </label>
            <select id="vr-channel" className="input" value={channel} onChange={(e) => setChannel(e.target.value)}>
              <option value="">Pick a voice channel</option>
              {data.voice_channels.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="field">
          <label className="field__label" htmlFor="vr-role">
            Role to give
          </label>
          <select id="vr-role" className="input" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="">Pick a role</option>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
          {hidden > 0 && (
            <span className="field__hint">
              Only roles below SahasrahBot’s role are listed, because the bot can’t give the others. To use one of them, move SahasrahBot’s role above
              it in Discord’s server settings.
            </span>
          )}
        </div>
        <span className="muted">People already in the channel get the role the next time they join.</span>
      </div>
    </FormDialog>
  )
}
