import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { api, unwrap } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Banner, Button, PageHeader, Panel } from '../components'

/** /submit/:event?episode_id= — the race settings form a tournament DMs its players. */
export function SubmissionScreen() {
  return <RequireSignIn>{() => <Submission />}</RequireSignIn>
}

function Submission() {
  const { event = '' } = useParams()
  const [params] = useSearchParams()
  const query = useQuery(`submit/${event}`, async () =>
    unwrap(await api.GET('/api/v1/tournaments/{event}/submission-form', { params: { path: { event } } })),
  )
  const [episode, setEpisode] = useState(params.get('episode_id') ?? '')
  const [settings, setSettings] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const [done, setDone] = useState<string>()

  return (
    <Loaded query={query} label="Loading the form" notFound="This event doesn't take race settings here.">
      {(form) => {
        const complete = /^\d+$/.test(episode) && form.fields.every((f) => settings[f.key])
        return (
          <>
            <PageHeader title="Race settings" lede={`Pick the settings for your ${form.event} race.`} />
            {done && <Banner tone="accent">Thanks, settings for {done} are in. Check your Discord DMs for the details.</Banner>}
            {error && <Banner tone="error">{error}</Banner>}
            <Panel>
              <form
                className="panel__pad stack"
                onSubmit={async (e) => {
                  e.preventDefault()
                  setBusy(true)
                  try {
                    const result = unwrap(
                      await api.POST('/api/v1/tournaments/{event}/submissions', {
                        params: { path: { event: form.event } },
                        body: { episode_id: Number(episode), settings },
                      }),
                    )
                    setError(undefined)
                    setDone(result.versus)
                  } catch (err) {
                    setError((err as Error).message)
                  } finally {
                    setBusy(false)
                  }
                }}
              >
                <div className="field-grid">
                  <div className="field">
                    <label className="field__label" htmlFor="episode">
                      SpeedGaming episode
                    </label>
                    <input
                      id="episode"
                      className="input mono"
                      inputMode="numeric"
                      value={episode}
                      onChange={(e) => setEpisode(e.target.value.trim())}
                    />
                  </div>
                  {form.fields.map((f) => (
                    <div key={f.key} className="field">
                      <label className="field__label" htmlFor={`setting-${f.key}`}>
                        {f.label}
                      </label>
                      <select
                        id={`setting-${f.key}`}
                        className="input"
                        value={settings[f.key] ?? ''}
                        onChange={(e) => setSettings({ ...settings, [f.key]: e.target.value })}
                      >
                        <option value="" disabled>
                          Choose…
                        </option>
                        {f.options.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  ))}
                </div>
                <div className="t-actions t-actions--end">
                  <Button type="submit" busy={busy} busyLabel="Submitting" disabled={!complete}>
                    Submit settings
                  </Button>
                </div>
              </form>
            </Panel>
          </>
        )
      }}
    </Loaded>
  )
}
