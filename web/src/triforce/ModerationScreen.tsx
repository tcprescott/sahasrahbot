import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { api, unwrap, type TriforceText } from '../api/client'
import { Loaded } from '../api/Loaded'
import { useQuery } from '../api/useQuery'
import { RequireSignIn } from '../auth/SessionProvider'
import { Banner, Button, Chip, EmptyState, Icon, PageHeader, Panel } from '../components'
import { ago, fullDate } from '../lib/time'
import { STATUS_LABEL, STATUS_TONE } from './TriforcePoolScreen'
import { TriforcePreview } from './TriforceText'

type Status = 'pending' | 'approved' | 'rejected' | 'all'
const FILTERS: { status: Status; label: string }[] = [
  { status: 'pending', label: 'To review' },
  { status: 'approved', label: 'Approved' },
  { status: 'rejected', label: 'Not used' },
  { status: 'all', label: 'All' },
]

/** /triforcetexts/:pool/moderation — the pool's moderators approve or turn down texts. */
export function ModerationScreen() {
  return <RequireSignIn>{() => <Moderation />}</RequireSignIn>
}

function Moderation() {
  const { pool = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const status = (FILTERS.find((f) => f.status === params.get('approved'))?.status ?? 'pending') as Status
  const query = useQuery(`triforce/${pool}/moderation/${status}`, async () =>
    unwrap(
      await api.GET('/api/v1/triforce-texts/{pool}/moderation', {
        params: { path: { pool }, query: { status } },
      }),
    ),
  )
  const [busyId, setBusyId] = useState<number>()
  const [error, setError] = useState<string>()

  const decide = async (text: TriforceText, approved: boolean) => {
    setBusyId(text.id)
    try {
      unwrap(
        await api.POST('/api/v1/triforce-texts/{pool}/moderation/{text_id}', {
          params: { path: { pool, text_id: text.id } },
          body: { approved },
        }),
      )
      setError(undefined)
      query.reload()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusyId(undefined)
    }
  }

  return (
    <>
      <Link to={`/triforcetexts/${encodeURIComponent(pool)}`} className="back-link">
        <Icon name="chevron_left" size={20} />
        Submission form
      </Link>
      <PageHeader title="Review triforce texts" lede={<>Submissions to <span className="code">{pool}</span>. Approved texts can appear in seeds.</>} />
      <div className="filter-chips" role="group" aria-label="Show">
        {FILTERS.map((f) => (
          <button
            key={f.status}
            type="button"
            className="filter-chip"
            aria-pressed={status === f.status}
            onClick={() => setParams(f.status === 'pending' ? {} : { approved: f.status }, { replace: true })}
          >
            {f.label}
          </button>
        ))}
      </div>
      {error && <Banner tone="error">{error}</Banner>}
      <div className="mt-3">
        <Loaded query={query} label="Loading submissions">
          {(data) =>
            data.texts.length === 0 ? (
              <EmptyState icon="check_circle" title={status === 'pending' ? 'Nothing to review' : 'Nothing here'}>
                {status === 'pending' ? "You're all caught up." : undefined}
              </EmptyState>
            ) : (
              <Panel>
                <ul className="triforce-list">
                  {data.texts.map((t) => (
                    <li key={t.id}>
                      <TriforcePreview lines={t.lines} />
                      <div className="grow">
                        <div>
                          <strong>{t.author ?? 'Unknown'}</strong>
                        </div>
                        <span className="muted" title={fullDate(t.submitted)}>
                          {ago(t.submitted)}
                        </span>{' '}
                        {status === 'all' && <Chip tone={STATUS_TONE[t.status]}>{STATUS_LABEL[t.status]}</Chip>}
                      </div>
                      <div className="t-actions">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busyId === t.id || t.status === 'rejected'}
                          onClick={() => void decide(t, false)}
                        >
                          Don't use
                        </Button>
                        <Button size="sm" disabled={busyId === t.id || t.status === 'approved'} onClick={() => void decide(t, true)}>
                          Approve
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              </Panel>
            )
          }
        </Loaded>
      </div>
    </>
  )
}
