import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, unwrap, type ElectionResults } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { Chip, IconButton, PageHeader, Panel } from '../components'
import { fullDate } from '../lib/time'
import { methodText, votes } from './labels'
import './elections.css'

type Round = ElectionResults['tally']['rounds'][number]
type Status = Round['candidates'][number]['status']

/** /elections/:electionId/results — public once voting closes; the Discord post links here. */
export function ResultsScreen() {
  const { electionId = '' } = useParams()
  const id = Number(electionId)
  const query = useQuery(`results/${id}`, async () =>
    unwrap(await api.GET('/api/v1/elections/{election_id}/results', { params: { path: { election_id: id } } })),
  )
  return (
    <Loaded query={query} label="Loading the results" notFound="This election doesn't exist.">
      {(results) => <Results results={results} />}
    </Loaded>
  )
}

const BAR_CLASS: Record<Status, string> = { elected: 'round-bar__fill--won', eliminated: 'round-bar__fill--out', hopeful: '' }
const STATUS_LABEL: Record<Status, string> = { elected: 'elected', eliminated: 'out', hopeful: 'still in' }
const NAME_CLASS: Record<Status, string | undefined> = { elected: 'is-won', eliminated: 'is-out', hopeful: undefined }

/** Each candidate's status in a round, and whether it changed in that round. */
function statusIn(rounds: Round[], index: number, id: number): { status: Status; now: boolean } {
  const find = (r: Round | undefined) => r?.candidates.find((c) => c.id === id)?.status ?? 'hopeful'
  const status = find(rounds[index])
  return { status, now: index === 0 ? status !== 'hopeful' : find(rounds[index - 1]) !== status }
}

/** "Ranked (STV), 3 seats · 42 ballots · Closed … · Server". */
function ledeFor(results: ElectionResults): string {
  const ballots = results.tally.ballots
  return [
    methodText(results.method, results.seats),
    `${ballots} ${ballots === 1 ? 'ballot' : 'ballots'}`,
    results.closed_at && `Closed ${fullDate(results.closed_at)}`,
    results.guild_name,
  ]
    .filter(Boolean)
    .join(' · ')
}

function Results({ results }: Readonly<{ results: ElectionResults }>) {
  const { tally, candidates } = results
  const names = new Map(candidates.map((c) => [c.id, c.name]))
  const rounds = tally.rounds
  const lede = ledeFor(results)

  return (
    <>
      <PageHeader title={results.title} lede={lede} />
      <div className="stack">
        <Panel title={tally.winners.length === 1 ? 'Winner' : 'Winners'}>
          <div className="panel__pad stack">
            {tally.winners.length === 0 ? (
              <p className="muted">No ballots were cast.</p>
            ) : (
              <div className="winners">
                {tally.winners.map((id, i) => (
                  <Chip key={id} tone="ok">
                    {i + 1}. {names.get(id)}
                  </Chip>
                ))}
              </div>
            )}
            {tally.tie_broken && <p className="muted-sub">There was a tie, settled by a random draw that's the same every time this election is counted.</p>}
          </div>
        </Panel>
        {rounds.length > 0 && <Bars results={results} />}
        {rounds.length > 1 && <RoundTable results={results} />}
      </div>
    </>
  )
}

function caption(results: ElectionResults, index: number): string {
  const { tally } = results
  const names = new Map(results.candidates.map((c) => [c.id, c.name]))
  if (tally.method !== 'stv') {
    return tally.method === 'approval' ? 'Each bar is how many voters ticked that candidate.' : 'Each bar is how many voters picked that candidate.'
  }
  const rounds = tally.rounds
  const round = rounds[index]!
  const changed = (s: Status) =>
    round.candidates.filter((c) => c.status === s && statusIn(rounds, index, c.id).now).map((c) => names.get(c.id) ?? '')
  const elected = changed('elected')
  const out = changed('eliminated')
  const parts = [`Dashed line: the quota to win (${votes(tally.quota ?? 0)}).`]
  if (elected.length) parts.push(`${elected.join(' and ')} ${elected.length === 1 ? 'reaches' : 'reach'} the quota and ${elected.length === 1 ? 'is' : 'are'} elected.`)
  if (out.length) parts.push(`${out.join(' and ')} ${out.length === 1 ? 'has' : 'have'} the fewest votes and ${out.length === 1 ? 'is' : 'are'} out; those votes move to their next choices.`)
  if (round.exhausted > 0) parts.push(`${votes(round.exhausted)} ${round.exhausted === 1 ? 'vote has' : 'votes have'} no next choice left.`)
  return parts.join(' ')
}

/** One round at a time as bars, with the quota as a dashed line. */
function Bars({ results }: Readonly<{ results: ElectionResults }>) {
  const { tally, candidates } = results
  const rounds = tally.rounds
  const [index, setIndex] = useState(rounds.length - 1)
  const round = rounds[index]!
  const top = Math.max(tally.quota ?? 0, ...rounds.flatMap((r) => r.candidates.map((c) => c.votes)), 1)
  const byId = new Map(round.candidates.map((c) => [c.id, c]))
  const quota = tally.method === 'stv' && tally.quota ? tally.quota : null
  return (
    <Panel title="How the count went">
      {rounds.length > 1 && (
        <div className="round-stepper">
          <IconButton icon="chevron_left" label="Previous round" disabled={index === 0} onClick={() => setIndex(index - 1)} />
          <b aria-live="polite">
            Round {index + 1} of {rounds.length}
          </b>
          <IconButton icon="chevron_right" label="Next round" disabled={index === rounds.length - 1} onClick={() => setIndex(index + 1)} />
        </div>
      )}
      <ul className="round-bars">
        {candidates.map((c) => {
          const row = byId.get(c.id)
          const status = row?.status ?? 'eliminated'
          const value = row?.votes ?? 0
          const out = status === 'eliminated'
          const fill = `round-bar__fill ${BAR_CLASS[status]}`
          const label = STATUS_LABEL[status]
          return (
            <li className="round-bar" key={c.id} aria-label={`${c.name}: ${votes(value)} votes, ${label}`}>
              <span className={out ? 'round-bar__name is-out' : 'round-bar__name'}>{c.name}</span>
              <span className="round-bar__track" aria-hidden="true">
                <span className={fill} style={{ display: 'block', width: `${(value / top) * 100}%` }} />
                {quota && <span className="round-bar__quota" style={{ left: `${(quota / top) * 100}%` }} />}
              </span>
              <span className="round-bar__value" aria-hidden="true">
                {out && value === 0 ? 'out' : votes(value)}
              </span>
            </li>
          )
        })}
      </ul>
      <p className="panel__pad muted-sub">{caption(results, index)}</p>
    </Panel>
  )
}

/** Every round at once, for the record. */
function RoundTable({ results }: Readonly<{ results: ElectionResults }>) {
  const rounds = results.tally.rounds
  const cell = (index: number, id: number) => {
    const row = rounds[index]?.candidates.find((c) => c.id === id)
    const { status, now } = statusIn(rounds, index, id)
    if (status === 'eliminated' && !now) return '–'
    const value = votes(row?.votes ?? 0)
    if (status === 'elected' && now) return `${value} ✓`
    if (status === 'eliminated') return `${value} out`
    return value
  }
  const final = (id: number) => statusIn(rounds, rounds.length - 1, id).status
  return (
    <Panel title="Every round">
      <div className="rounds-scroll">
        <table className="rounds-table">
          <thead>
            <tr>
              <th scope="col">Candidate</th>
              {rounds.map((_, i) => (
                <th scope="col" key={i}>
                  Round {i + 1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.candidates.map((c) => (
              <tr key={c.id}>
                <th scope="row" className={NAME_CLASS[final(c.id)]}>
                  {c.name}
                </th>
                {rounds.map((_, i) => (
                  <td key={i}>{cell(i, c.id)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {results.tally.quota != null && <p className="panel__pad muted-sub">Quota to win: {votes(results.tally.quota)} votes. ✓ marks the round a candidate was elected.</p>}
    </Panel>
  )
}
