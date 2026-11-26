import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, api, loginUrl, unwrap } from '../api/client'
import { useQuery } from '../api/useQuery'
import { useSession } from '../auth/SessionProvider'
import { Banner, Button, Icon, PageHeader, Panel, Spinner } from '../components'
import { fullDate } from '../lib/time'
import { RollOptions } from './RollOptions'
import { DEFAULT_CHOICES, ROLLABLE, hashFrom, rollSeed, type Rollable, type RollChoices, type Seed } from './rolling'
import { CopyButton, SeedCard } from './SeedCard'
import './seeds.css'

/** /seeds and /seeds/:hash — roll from any preset, as /alttpr preset, /sm and /smz3 do, or look a seed up. */
export function SeedsScreen() {
  const { user } = useSession()
  const signedOut = user === null
  const waiting = !user // signed out, or still finding out
  return (
    <>
      <PageHeader
        title="Seeds"
        lede="Roll a seed from any preset, as /alttpr preset, /sm and /smz3 do in Discord, or look one up."
      />
      {signedOut && (
        <Banner
          action={
            <Button asChild variant="outline">
              <a href={loginUrl()}>Sign in</a>
            </Button>
          }
        >
          Sign in with Discord to roll or look up seeds.
        </Banner>
      )}
      <RollPanel disabled={waiting} />
      <LookupPanel disabled={waiting} />
    </>
  )
}

function RollPanel({ disabled }: Readonly<{ disabled: boolean }>) {
  const [randomizer, setRandomizer] = useState<Rollable>('alttpr')
  const [preset, setPreset] = useState('')
  const [choices, setChoices] = useState<RollChoices>(DEFAULT_CHOICES)
  const [seed, setSeed] = useState<Seed | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const builtIn = useQuery(`seeds/presets/${randomizer}`, async () =>
    unwrap(await api.GET('/api/v1/seeds/presets/{randomizer}', { params: { path: { randomizer } } })),
  )

  const roll = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(undefined)
    setSeed(null)
    try {
      setSeed(await rollSeed(randomizer, preset.trim(), choices))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <Panel title="Roll a seed">
        <form onSubmit={(e) => void roll(e)}>
          <div className="seed-form">
            <div className="filter-chips" role="group" aria-label="Randomizer">
              {ROLLABLE.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  className="filter-chip"
                  aria-pressed={randomizer === r.id}
                  onClick={() => setRandomizer(r.id)}
                >
                  {r.label}
                </button>
              ))}
            </div>
            <div className="field">
              <label className="field__label" htmlFor="seed-preset">
                Preset
              </label>
              <input
                id="seed-preset"
                className="input"
                list="seed-presets"
                value={preset}
                onChange={(e) => setPreset(e.target.value)}
                autoComplete="off"
                required
              />
              <span className="field__hint">
                A built-in preset, or someone's as <span className="code">namespace/name</span>.{' '}
                <Link to="/presets">Browse presets</Link>
              </span>
              <datalist id="seed-presets">
                {(builtIn.data?.presets ?? []).map((name) => (
                  <option key={name} value={name} />
                ))}
              </datalist>
            </div>
          </div>
          <RollOptions randomizer={randomizer} value={choices} onChange={setChoices} />
          <div className="seed-roll t-actions">
            <Button type="submit" icon="refresh" busy={busy} busyLabel="Rolling" disabled={disabled || !preset.trim()}>
              Roll
            </Button>
          </div>
        </form>
        {busy && <p className="seed-hint">Rolling takes a few seconds.</p>}
      </Panel>
      {error && <Banner tone="error">{error}</Banner>}
      {seed && (
        <Panel title="Your seed">
          <SeedCard seed={seed} />
        </Panel>
      )}
    </>
  )
}

function LookupPanel({ disabled }: Readonly<{ disabled: boolean }>) {
  const { hash = '' } = useParams()
  const navigate = useNavigate()
  const [text, setText] = useState(hash)
  const found = useQuery(hash && !disabled ? `seeds/${hash}` : null, async () =>
    unwrap(await api.GET('/api/v1/seeds/{hash_id}', { params: { path: { hash_id: hash } } })),
  )

  const look = (e: FormEvent) => {
    e.preventDefault()
    const next = hashFrom(text)
    if (next) navigate(`/seeds/${encodeURIComponent(next)}`)
  }

  return (
    <>
      <Panel title="Look up a seed">
        <form className="seed-search" onSubmit={look}>
          <input
            className="input"
            aria-label="Seed hash or link"
            placeholder="Hash or seed link"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <Button type="submit" icon="search" disabled={disabled || !text.trim()}>
            Look up
          </Button>
        </form>
      </Panel>
      {hash && !disabled && found.loading && !found.data && <Spinner label="Looking up the seed" />}
      {found.error && (
        <Banner tone={found.error instanceof ApiError && found.error.status === 404 ? 'info' : 'error'}>{found.error.message}</Banner>
      )}
      {found.data && found.data.hash === hash && (
        <Panel title={<span className="code">{found.data.hash}</span>}>
          <div className="seed-result">
            <dl className="t-kv">
              <dt>Randomizer</dt>
              <dd>{found.data.randomizer ?? 'Not recorded'}</dd>
              {found.data.kind && (
                <>
                  <dt>Rolled as</dt>
                  <dd>{found.data.kind}</dd>
                </>
              )}
              <dt>Preset</dt>
              <dd>{found.data.preset ?? 'Not recorded'}</dd>
              {found.data.rolled_at && (
                <>
                  <dt>Rolled</dt>
                  <dd>{fullDate(found.data.rolled_at)}</dd>
                </>
              )}
            </dl>
            {found.data.url && (
              <div className="t-actions">
                <Button asChild>
                  <a href={found.data.url} target="_blank" rel="noreferrer">
                    <Icon name="open_in_new" size={18} />
                    Open seed
                  </a>
                </Button>
                <CopyButton value={found.data.url} />
              </div>
            )}
          </div>
        </Panel>
      )}
    </>
  )
}
