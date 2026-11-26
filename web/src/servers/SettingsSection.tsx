import { useState } from 'react'
import { api, unwrap, type ServerSettings } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { Banner, Button, Icon, Panel } from '../components'
import { useServer } from './ServerContext'

/** /servers/:guildId/settings — the daily challenge channels and the /holyimage default game. */
export function SettingsSection() {
  const { server } = useServer()
  const query = useQuery(`servers/${server.id}/settings`, async () =>
    unwrap(
      await api.GET('/api/v1/servers/{guild_id}/settings', {
        params: { path: { guild_id: server.id as unknown as number } },
      }),
    ),
  )
  return (
    <Loaded query={query} label="Loading the settings">
      {(settings) => <SettingsForm key={server.id} saved={settings} />}
    </Loaded>
  )
}

type Draft = { daily: string[]; game: string }

const draftOf = (s: ServerSettings): Draft => ({
  daily: s.daily_channels.map((c) => c.name),
  game: s.holy_image_game ?? '',
})

const same = (a: Draft, b: Draft) => a.game === b.game && a.daily.join(',') === b.daily.join(',')

function SettingsForm({ saved: initial }: Readonly<{ saved: ServerSettings }>) {
  const { server } = useServer()
  const [saved, setSaved] = useState(initial)
  const [draft, setDraftState] = useState(() => draftOf(initial))
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<{ tone: 'accent' | 'error'; text: string }>()
  // An edit clears the last save's message.
  const setDraft = (next: Draft) => {
    setDraftState(next)
    setNotice(undefined)
  }

  const usable = new Map(saved.daily_channels.map((c) => [c.name, c.usable]))
  const postable = server.text_channels.map((c) => c.name.replace(/^#/, ''))
  const isUsable = (name: string) => usable.get(name) ?? postable.includes(name)
  const addable = postable.filter((name) => !draft.daily.includes(name))
  const problems = draft.daily.filter((name) => !isUsable(name))
  const dirty = !same(draft, draftOf(saved))
  const games = saved.holy_image_games.includes(draft.game) || !draft.game ? saved.holy_image_games : [draft.game, ...saved.holy_image_games]

  const save = async () => {
    setBusy(true)
    try {
      const next = unwrap(
        await api.PUT('/api/v1/servers/{guild_id}/settings', {
          params: { path: { guild_id: server.id as unknown as number } },
          body: { daily_channels: draft.daily, holy_image_game: draft.game || null },
        }),
      )
      setSaved(next)
      setDraftState(draftOf(next))
      setNotice({ tone: 'accent', text: 'Settings saved.' })
    } catch (e) {
      setNotice({ tone: 'error', text: (e as Error).message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="server-settings">
      <Panel title="Daily challenge">
        <div className="server-settings__pad">
          <div className="field">
            <label className="field__label" htmlFor="daily-add">
              Announce the ALTTPR daily challenge in
            </label>
            {draft.daily.length > 0 && (
              <ul className="channel-chips" aria-label="Daily challenge channels">
                {draft.daily.map((name) => {
                  const ok = isUsable(name)
                  return (
                    <li key={name} className={ok ? 'channel-chip' : 'channel-chip channel-chip--problem'}>
                      {!ok && <Icon name="warning" size={16} />}#{name}
                      <button
                        type="button"
                        aria-label={`Remove #${name}`}
                        onClick={() => setDraft({ ...draft, daily: draft.daily.filter((n) => n !== name) })}
                      >
                        <Icon name="close" size={16} />
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
            <select
              id="daily-add"
              className="input"
              value=""
              disabled={addable.length === 0}
              aria-describedby="daily-hint"
              onChange={(e) => e.target.value && setDraft({ ...draft, daily: [...draft.daily, e.target.value] })}
            >
              <option value="">{addable.length ? 'Add a channel…' : 'No other channels SahasrahBot can post in'}</option>
              {addable.map((name) => (
                <option key={name} value={name}>
                  #{name}
                </option>
              ))}
            </select>
            <span className="field__hint" id="daily-hint">
              Each new daily seed is posted here with a thread to discuss it. With no channels, it isn't posted in this
              server.
            </span>
          </div>
          {problems.map((name) => (
            <p key={name} className="server-settings__problem">
              <Icon name="warning" size={16} />
              <span>#{name} no longer exists or SahasrahBot can't post there, so nothing is posted in it.</span>
            </p>
          ))}
        </div>
      </Panel>

      <Panel title="Holy images">
        <div className="server-settings__pad">
          <div className="field">
            <label className="field__label" htmlFor="holy-game">
              Default game for /holyimage
            </label>
            <select
              id="holy-game"
              className="input"
              value={draft.game}
              aria-describedby="holy-hint"
              onChange={(e) => setDraft({ ...draft, game: e.target.value })}
            >
              <option value="">{saved.holy_image_fallback} (the default)</option>
              {games
                .filter((g) => g !== saved.holy_image_fallback)
                .map((g) => (
                  <option key={g} value={g}>
                    {g}
                  </option>
                ))}
            </select>
            <span className="field__hint" id="holy-hint">
              Used when someone runs /holyimage in this server without picking a game.
            </span>
          </div>
        </div>
      </Panel>

      {notice && <Banner tone={notice.tone}>{notice.text}</Banner>}
      <div className="server-settings__save">
        {dirty && <span>Unsaved changes</span>}
        {dirty && (
          <Button variant="outline" onClick={() => setDraft(draftOf(saved))} disabled={busy}>
            Discard
          </Button>
        )}
        <Button onClick={save} disabled={!dirty} busy={busy} busyLabel="Saving">
          Save settings
        </Button>
      </div>
    </div>
  )
}
