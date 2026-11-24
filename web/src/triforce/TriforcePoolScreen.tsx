import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, unwrap, type TriforceText } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Banner, Button, Chip, PageHeader, Panel, type Tone } from '../components'
import { ago, fullDate } from '../lib/time'
import { MAX_LINE, lineProblem } from './rules'
import { TriforcePreview } from './TriforceText'

export const STATUS_TONE: Record<TriforceText['status'], Tone> = { pending: 'pending', approved: 'ok', rejected: 'cancelled' }
export const STATUS_LABEL: Record<TriforceText['status'], string> = {
  pending: 'Waiting for review',
  approved: 'Approved',
  rejected: 'Not used',
}

/** /triforcetexts/:pool — write a triforce text for an event, and see what you've sent. */
export function TriforcePoolScreen() {
  return <RequireSignIn>{() => <Pool />}</RequireSignIn>
}

function Pool() {
  const { pool = '' } = useParams()
  const query = useQuery(`triforce/${pool}`, async () =>
    unwrap(await api.GET('/api/v1/triforce-texts/{pool}', { params: { path: { pool } } })),
  )
  const [lines, setLines] = useState(['', '', ''])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const [sent, setSent] = useState(false)
  const problems = lines.map(lineProblem)
  const blank = lines.every((l) => !l.trim())

  return (
    <Loaded query={query} label="Loading">
      {(data) => (
        <>
          <PageHeader
            title="Triforce text"
            lede={
              <>
                Write the message the Triforce shows at the end of a seed, for <span className="code">{data.pool}</span>.
              </>
            }
            actions={
              data.is_moderator && (
                <Button asChild variant="outline">
                  <Link to={`/triforcetexts/${encodeURIComponent(data.pool)}/moderation`}>Review submissions</Link>
                </Button>
              )
            }
          />
          {sent && <Banner tone="accent">Sent. The event's staff review every text before it's used.</Banner>}
          {error && <Banner tone="error">{error}</Banner>}
          <Panel title="Your text">
            <form
              className="panel__pad triforce-form"
              onSubmit={async (e) => {
                e.preventDefault()
                setBusy(true)
                setSent(false)
                try {
                  unwrap(
                    await api.POST('/api/v1/triforce-texts/{pool}/submissions', {
                      params: { path: { pool: data.pool } },
                      body: { lines },
                    }),
                  )
                  setLines(['', '', ''])
                  setError(undefined)
                  setSent(true)
                  query.reload()
                } catch (err) {
                  setError((err as Error).message)
                } finally {
                  setBusy(false)
                }
              }}
            >
              <div className="stack">
                {lines.map((line, i) => {
                  const id = `line-${i}`
                  const length = [...line].length
                  return (
                    <div key={id} className="field">
                      <div className="field__row">
                        <label className="field__label" htmlFor={id}>
                          Line {i + 1}
                        </label>
                        <span className={length > MAX_LINE ? 'char-count char-count--over' : 'char-count'} aria-hidden="true">
                          {length}/{MAX_LINE}
                        </span>
                      </div>
                      <input
                        id={id}
                        className="input mono"
                        value={line}
                        autoComplete="off"
                        spellCheck={false}
                        aria-invalid={problems[i] !== null}
                        aria-describedby={problems[i] ? `${id}-error` : undefined}
                        onChange={(e) => setLines(lines.map((l, j) => (j === i ? e.target.value : l)))}
                      />
                      {problems[i] && (
                        <span id={`${id}-error`} className="form-error">
                          {problems[i]}
                        </span>
                      )}
                    </div>
                  )
                })}
                <div className="t-actions">
                  <Button type="submit" busy={busy} busyLabel="Sending" disabled={blank || problems.some(Boolean)}>
                    Send for review
                  </Button>
                </div>
              </div>
              <div className="stack">
                <span className="field__label">Preview</span>
                <TriforcePreview lines={lines} />
              </div>
            </form>
          </Panel>
          <Panel title="Keep it fun">
            <div className="panel__pad prose">
              <p>Staff turn down texts about real-life religion or politics, hate speech, unapproved advertising,
                harassment, other community members without their say-so, or anything you couldn't show on a Twitch
                stream.</p>
              <p className="muted">
                Up to {MAX_LINE} characters a line: A to Z, 0 to 9, spaces, <span className="code">? ! , - … . ~ ～ ' ↑ ↓ → ←</span>{' '}
                and hiragana and katakana.
              </p>
            </div>
          </Panel>
          {data.mine.length > 0 && (
            <Panel title="What you've sent">
              <ul className="triforce-list">
                {data.mine.map((t) => (
                  <li key={t.id}>
                    <TriforcePreview lines={t.lines} />
                    <Chip tone={STATUS_TONE[t.status]}>{STATUS_LABEL[t.status]}</Chip>
                    <span className="muted" title={fullDate(t.submitted)}>
                      {ago(t.submitted)}
                    </span>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </>
      )}
    </Loaded>
  )
}
