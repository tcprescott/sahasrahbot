import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError, unwrap, type Election } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Banner, Button, Chip, EmptyState, Icon, IconButton, PageHeader, Panel } from '../components'
import { instructions, ordinal } from '../elections/labels'
import { resultsPath } from '../elections/paths'
import { fullDate } from '../lib/time'
import { add, move, remove } from './ranking'
import '../elections/elections.css'
import './ballot.css'

/** /ranked_choice/:electionId — the Vote link SahasrahBot posts with every election. */
export function BallotScreen() {
  return <RequireSignIn>{() => <Ballot />}</RequireSignIn>
}

function Ballot() {
  const { electionId = '' } = useParams()
  const id = Number(electionId)
  const query = useQuery(`ballot/${id}`, async () =>
    unwrap(await api.GET('/api/v1/elections/{election_id}/ballot', { params: { path: { election_id: id } } })),
  )
  const [changing, setChanging] = useState(false)
  const closed = query.error instanceof ApiError && query.error.status === 404 && /closed/.test(query.error.message)
  if (closed) {
    return (
      <EmptyState icon="how_to_vote" title="Voting has closed">
        This election is over. <Link to={resultsPath(id)}>See the results</Link>.
      </EmptyState>
    )
  }
  return (
    <Loaded query={query} label="Loading your ballot" notFound="This election doesn't exist.">
      {(election) =>
        election.ballot && !changing ? (
          <Submitted election={election} onChange={() => setChanging(true)} />
        ) : (
          <Vote
            election={election}
            onCancel={election.ballot ? () => setChanging(false) : undefined}
            onVoted={() => {
              setChanging(false)
              query.reload()
            }}
          />
        )
      }
    </Loaded>
  )
}

function Header({ election, voting = true }: Readonly<{ election: Election; voting?: boolean }>) {
  const until = election.closes_at
    ? `Closes ${fullDate(election.closes_at)} · You can change your ballot until then.`
    : 'You can change your ballot until an admin ends the vote.'
  return (
    <>
      <PageHeader title={election.title} lede={election.description || instructions(election.method, election.seats)} />
      <p className="muted-sub election-sub">{[election.guild_name, until].filter(Boolean).join(' · ')}</p>
      {voting && election.description && <p className="muted">{instructions(election.method, election.seats)}</p>}
    </>
  )
}

function Submitted({ election, onChange }: Readonly<{ election: Election; onChange: () => void }>) {
  const names = new Map(election.candidates.map((c) => [c.id, c.name]))
  const ballot = election.ballot ?? []
  const ranked = election.method === 'stv'
  const until = election.closes_at ? `until ${fullDate(election.closes_at)}` : 'until voting closes'
  return (
    <>
      <Header election={election} voting={false} />
      <Banner
        tone="accent"
        action={
          <Button size="sm" variant="outline" icon="edit" onClick={onChange}>
            Change ballot
          </Button>
        }
      >
        Your ballot is in. You can change it {until}.
      </Banner>
      <Panel title="Your ballot" actions={<Chip tone="ok">{election.voted_at ? `Submitted ${fullDate(election.voted_at)}` : 'Submitted'}</Chip>}>
        <ol className="ballot">
          {ballot.map((cid, i) => (
            <li key={cid} className="ballot__row">
              {ranked ? (
                <span className="ballot__rank">{i + 1}</span>
              ) : (
                <Icon name="check_circle" />
              )}
              <span className="ballot__name">{names.get(cid)}</span>
            </li>
          ))}
        </ol>
      </Panel>
    </>
  )
}

function Vote({
  election,
  onVoted,
  onCancel,
}: Readonly<{ election: Election; onVoted: () => void; onCancel?: () => void }>) {
  const [choices, setChoices] = useState<number[]>(election.ballot ?? [])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const changing = election.ballot != null
  let submitLabel = election.method === 'plurality' ? 'Submit vote' : 'Submit ballot'
  if (changing) submitLabel = 'Update ballot'

  const submit = async () => {
    setBusy(true)
    setError(undefined)
    try {
      unwrap(
        await api.PUT('/api/v1/elections/{election_id}/ballot', {
          params: { path: { election_id: election.id } },
          body: { choices },
        }),
      )
      onVoted()
    } catch (e) {
      setError((e as Error).message)
      setBusy(false)
    }
  }

  return (
    <>
      <Header election={election} />
      {changing && <Banner tone="info">Your ballot is in. Change it below and press Update ballot, or Cancel to keep it.</Banner>}
      {error && <Banner tone="error">{error}</Banner>}
      {election.method === 'stv' ? (
        <RankedChoices election={election} ranking={choices} onChange={setChoices} />
      ) : (
        <Tiles election={election} picked={choices} onChange={setChoices} />
      )}
      <div className="t-actions t-actions--end ballot__submit mt-3">
        {onCancel ? (
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        ) : (
          <Button variant="outline" disabled={choices.length === 0} onClick={() => setChoices([])}>
            Clear
          </Button>
        )}
        <Button icon="how_to_vote" disabled={choices.length === 0} busy={busy} busyLabel="Submitting" onClick={submit}>
          {submitLabel}
        </Button>
      </div>
    </>
  )
}

/** Tap to rank: ranked candidates on top in order (with arrows), the rest below. */
function RankedChoices({
  election,
  ranking,
  onChange,
}: Readonly<{ election: Election; ranking: number[]; onChange: (ranking: number[]) => void }>) {
  const byId = new Map(election.candidates.map((c) => [c.id, c]))
  const unranked = election.candidates.filter((c) => !ranking.includes(c.id))
  return (
    <Panel
      title="Candidates"
      actions={<Chip tone={ranking.length ? 'pending' : 'neutral'}>{ranking.length ? `${ranking.length} ranked` : 'None ranked'}</Chip>}
    >
      <ol className="ballot" aria-label="Your ranking">
        {ranking.map((cid, i) => {
          const name = byId.get(cid)?.name ?? ''
          return (
            <li key={cid} className="ballot__row ballot__row--ranked">
              <button type="button" className="ballot__pick" aria-label={`Take ${name} out of your ranking`} onClick={() => onChange(remove(ranking, cid))}>
                <span className="ballot__rank">{i + 1}</span>
                <span className="ballot__name">{name}</span>
                <span className="muted-sub">{ordinal(i + 1)} choice</span>
              </button>
              <span className="ballot__moves">
                <IconButton icon="arrow_upward" label={`Move ${name} up`} disabled={i === 0} onClick={() => onChange(move(ranking, cid, -1))} />
                <IconButton
                  icon="arrow_downward"
                  label={`Move ${name} down`}
                  disabled={i === ranking.length - 1}
                  onClick={() => onChange(move(ranking, cid, 1))}
                />
              </span>
            </li>
          )
        })}
      </ol>
      {unranked.length > 0 && (
        <>
          {ranking.length > 0 && <div className="ballot__group">Not ranked</div>}
          <ul className="ballot" aria-label="Not ranked">
            {unranked.map((c) => (
              <li key={c.id} className="ballot__row">
                <button type="button" className="ballot__pick" aria-label={`Rank ${c.name}`} onClick={() => onChange(add(ranking, c.id))}>
                  <span className="ballot__rank ballot__rank--none" aria-hidden="true" />
                  <span className="ballot__name">{c.name}</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </Panel>
  )
}

/** Approval (tick any) and plurality (pick one) as big tiles. */
function Tiles({
  election,
  picked,
  onChange,
}: Readonly<{ election: Election; picked: number[]; onChange: (picked: number[]) => void }>) {
  const one = election.method === 'plurality'
  return (
    <fieldset className="field choice-fieldset">
      <legend className="visually-hidden">{one ? 'Your vote' : 'Your choices'}</legend>
      <div className="choice-tiles">
        {election.candidates.map((c) => (
          <label key={c.id} className="choice-tile choice-tile--center">
            <input
              type={one ? 'radio' : 'checkbox'}
              name="choice"
              checked={picked.includes(c.id)}
              onChange={(e) => {
                if (one) onChange([c.id])
                else onChange(e.target.checked ? add(picked, c.id) : remove(picked, c.id))
              }}
            />
            <b>{c.name}</b>
          </label>
        ))}
      </div>
    </fieldset>
  )
}
