import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, unwrap, type Election } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Banner, Button, Chip, IconButton, PageHeader, Panel } from '../components'
import { add, move, remove } from './ranking'
import './ballot.css'

/** /ranked_choice/:electionId — the link SahasrahBot posts with an election. */
export function BallotScreen() {
  return <RequireSignIn>{() => <Ballot />}</RequireSignIn>
}

function Ballot() {
  const { electionId = '' } = useParams()
  const id = Number(electionId)
  const query = useQuery(`ranked/${id}`, async () =>
    unwrap(await api.GET('/api/v1/ranked-choice/{election_id}', { params: { path: { election_id: id } } })),
  )
  return (
    <Loaded query={query} label="Loading your ballot" notFound="This election doesn't exist or has closed.">
      {(election) => (election.ballot ? <Submitted election={election} /> : <Vote election={election} onVoted={query.reload} />)}
    </Loaded>
  )
}

function Header({ election }: Readonly<{ election: Election }>) {
  return (
    <PageHeader
      title={election.title}
      lede={
        election.description ||
        (election.seats > 1 ? `${election.seats} winners will be chosen.` : 'One winner will be chosen.')
      }
    />
  )
}

function Submitted({ election }: Readonly<{ election: Election }>) {
  const names = new Map(election.candidates.map((c) => [c.id, c.name]))
  const ballot = election.ballot ?? []
  return (
    <>
      <Header election={election} />
      <Banner tone="accent">Thanks, your ballot is in. Ballots can't be changed; ask the organiser if you need to.</Banner>
      <Panel title="Your ballot" actions={<Chip tone="ok">Submitted</Chip>}>
        <ol className="ballot">
          {ballot.map((cid, i) => (
            <li key={cid} className="ballot__row">
              <span className="ballot__rank">{i + 1}</span>
              <span className="ballot__name">{names.get(cid)}</span>
            </li>
          ))}
        </ol>
      </Panel>
    </>
  )
}

function Vote({ election, onVoted }: Readonly<{ election: Election; onVoted: () => void }>) {
  const [ranking, setRanking] = useState<number[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const byId = new Map(election.candidates.map((c) => [c.id, c]))
  const unranked = election.candidates.filter((c) => !ranking.includes(c.id))

  return (
    <>
      <Header election={election} />
      <p className="muted">
        Put the candidates you'd be happy with in order, favourite first. Leave out anyone you don't want to rank. Your
        ballot is private and can't be changed once it's in.
      </p>
      {error && <Banner tone="error">{error}</Banner>}
      <Panel
        title="Your ranking"
        actions={<Chip tone={ranking.length ? 'pending' : 'neutral'}>{ranking.length ? 'Not submitted' : 'Empty'}</Chip>}
      >
        {ranking.length === 0 ? (
          <p className="panel__pad muted">Pick candidates below to rank them.</p>
        ) : (
          <ol className="ballot">
            {ranking.map((cid, i) => {
              const name = byId.get(cid)?.name ?? ''
              return (
                <li key={cid} className="ballot__row">
                  <span className="ballot__rank">{i + 1}</span>
                  <span className="ballot__name">{name}</span>
                  <span className="ballot__moves">
                    <IconButton icon="arrow_upward" label={`Move ${name} up`} disabled={i === 0} onClick={() => setRanking(move(ranking, cid, -1))} />
                    <IconButton
                      icon="arrow_downward"
                      label={`Move ${name} down`}
                      disabled={i === ranking.length - 1}
                      onClick={() => setRanking(move(ranking, cid, 1))}
                    />
                    <IconButton icon="close" label={`Unrank ${name}`} onClick={() => setRanking(remove(ranking, cid))} />
                  </span>
                </li>
              )
            })}
          </ol>
        )}
      </Panel>
      {unranked.length > 0 && (
        <Panel title="Not ranked">
          <ul className="ballot">
            {unranked.map((c) => (
              <li key={c.id} className="ballot__row">
                <span className="ballot__rank ballot__rank--none" aria-hidden="true">
                  –
                </span>
                <span className="ballot__name">{c.name}</span>
                <Button variant="outline" size="sm" icon="add" aria-label={`Rank ${c.name}`} onClick={() => setRanking(add(ranking, c.id))}>
                  Rank
                </Button>
              </li>
            ))}
          </ul>
        </Panel>
      )}
      <div className="t-actions t-actions--end ballot__submit">
        <Button variant="outline" disabled={ranking.length === 0} onClick={() => setRanking([])}>
          Clear
        </Button>
        <Button
          icon="how_to_vote"
          disabled={ranking.length === 0}
          busy={busy}
          busyLabel="Submitting"
          onClick={async () => {
            setBusy(true)
            try {
              unwrap(
                await api.POST('/api/v1/ranked-choice/{election_id}/ballot', {
                  params: { path: { election_id: election.id } },
                  body: { ranking },
                }),
              )
              onVoted()
            } catch (e) {
              setError((e as Error).message)
              setBusy(false)
            }
          }}
        >
          Submit ballot
        </Button>
      </div>
    </>
  )
}
