import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { safeHref } from '../../lib/safeHref';
import '../../styles/submit.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface QueueRace {
  id: number;
  status: string;
  review_status: string;
  elapsed_time: string | null;
  score_formatted: string | null;
  created: string | null;
  pool_name: string;
  permalink_url: string;
  user_id: number;
  user_display_name: string;
  reviewed_by_name: string | null;
  runner_vod_url: string | null;
}

interface QueueData {
  tournament: { id: number; name: string; active: boolean };
  races: QueueRace[];
  page: number;
  page_size: number;
  filters: { status: string; reviewed: string; review_status: string; live: string };
}

type PageState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'forbidden' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: QueueData };

// ---------------------------------------------------------------------------
// Filter option config
// ---------------------------------------------------------------------------

const STATUS_OPTS = [
  ['finished', 'Finished'], ['in_progress', 'In Progress'], ['pending', 'Pending'],
  ['forfeit', 'Forfeit'], ['all', 'All'],
] as const;
const REVIEW_OPTS = [
  ['pending', 'Pending'], ['approved', 'Approved'], ['rejected', 'Rejected'], ['all', 'All'],
] as const;
const REVIEWED_OPTS = [
  ['all', 'Anyone'], ['unreviewed', 'Unreviewed'], ['me', 'Me'],
] as const;
const LIVE_OPTS = [
  ['false', 'Async only'], ['true', 'Live only'], ['all', 'All'],
] as const;

function reviewTone(s: string): 'teal' | 'crimson' | 'default' {
  if (s === 'approved') return 'teal';
  if (s === 'rejected') return 'crimson';
  return 'default';
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function AsyncQueuePage() {
  const { id } = useParams<{ id: string }>();
  const [params, setParams] = useSearchParams();

  const status = params.get('status') ?? 'finished';
  const review_status = params.get('review_status') ?? 'pending';
  const reviewed = params.get('reviewed') ?? 'all';
  const live = params.get('live') ?? 'false';
  const page = Math.max(1, parseInt(params.get('page') ?? '1', 10) || 1);

  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });

  const load = useCallback(async () => {
    if (!id) return;
    setPageState({ status: 'loading' });
    const qs = new URLSearchParams({ status, review_status, reviewed, live, page: String(page) });
    try {
      const r = await fetch(`/async/races/${id}/queue.json?${qs.toString()}`);
      if (r.status === 401) { setPageState({ status: 'unauthenticated' }); return; }
      if (r.status === 403) { setPageState({ status: 'forbidden' }); return; }
      if (!r.ok) {
        const body = (await r.json().catch(() => ({}))) as { error?: string };
        setPageState({ status: 'error', message: body.error ?? `Failed to load (${r.status}).` });
        return;
      }
      const body = (await r.json()) as QueueData;
      setPageState({ status: 'ready', data: body });
    } catch (e) {
      setPageState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load queue.' });
    }
  }, [id, status, review_status, reviewed, live, page]);

  useEffect(() => { void load(); }, [load]);

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    next.set(key, value);
    next.set('page', '1'); // reset paging on filter change
    setParams(next);
  }

  function goPage(p: number) {
    const next = new URLSearchParams(params);
    next.set('page', String(p));
    setParams(next);
  }

  const races = pageState.status === 'ready' ? pageState.data.races : [];
  const tournamentName = pageState.status === 'ready' ? pageState.data.tournament.name : `Tournament #${id ?? ''}`;

  return (
    <>
      <section className="pagehead">
        <div className="glow" />
        <div className="grid" />
        <div className="wrap">
          <nav className="crumb reveal d1" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span className="sep">/</span>
            <span>Async Tournament</span>
            <span className="sep">/</span>
            <span>Queue</span>
          </nav>
          <h1 className="sb-title reveal d2">REVIEW QUEUE</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            <Badge tone="gold">{tournamentName}</Badge>
            <Badge tone="crimson">ADMIN</Badge>
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">

          {pageState.status === 'forbidden' && (
            <div className="panel">
              <div className="panel-body">
                <div className="alert alert-error"><span className="alert-icon">⚠</span><p>Admin or moderator access required.</p></div>
              </div>
            </div>
          )}

          {pageState.status === 'unauthenticated' && (
            <div className="panel">
              <div className="auth-prompt">
                <div className="auth-icon">🔒</div>
                <p>Sign in with Discord to view the review queue.</p>
                <a className="btn btn-primary" href={`/login/?next=/async/races/${id}/queue`}>
                  Sign in with Discord <span className="arr">→</span>
                </a>
              </div>
            </div>
          )}

          {pageState.status === 'error' && (
            <div className="panel">
              <div className="panel-body">
                <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{pageState.message}</p></div>
                <button className="btn btn-ghost btn-sm" onClick={() => void load()}>Retry</button>
              </div>
            </div>
          )}

          {(pageState.status === 'loading' || pageState.status === 'ready') && (
            <>
              {/* Filter bar */}
              <div
                className="onscroll"
                style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.4rem', alignItems: 'flex-end' }}
              >
                <FilterSelect label="Status" value={status} opts={STATUS_OPTS} onChange={(v) => setFilter('status', v)} />
                <FilterSelect label="Review" value={review_status} opts={REVIEW_OPTS} onChange={(v) => setFilter('review_status', v)} />
                <FilterSelect label="Reviewed by" value={reviewed} opts={REVIEWED_OPTS} onChange={(v) => setFilter('reviewed', v)} />
                <FilterSelect label="Race type" value={live} opts={LIVE_OPTS} onChange={(v) => setFilter('live', v)} />
              </div>

              <div className="table-wrap onscroll">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Player</th><th>Pool</th><th>Time</th><th>Score</th>
                      <th>Review</th><th>Reviewer</th><th>VoD</th><th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageState.status === 'loading' && Array.from({ length: 6 }, (_, i) => (
                      <tr key={i}>
                        {Array.from({ length: 8 }, (__, j) => (
                          <td key={j}><span className="skel" style={{ width: j === 0 ? '7rem' : '3.5rem', height: '.8rem' }} /></td>
                        ))}
                      </tr>
                    ))}

                    {pageState.status === 'ready' && races.map((race) => (
                      <tr key={race.id}>
                        <td>
                          <Link to={`/async/player/${id}/${race.user_id}`}>{race.user_display_name}</Link>
                        </td>
                        <td>{race.pool_name}</td>
                        <td><span className="num">{race.elapsed_time && race.elapsed_time !== 'N/A' ? race.elapsed_time : '—'}</span></td>
                        <td><span className="num">{race.score_formatted && race.score_formatted !== 'N/A' ? race.score_formatted : '—'}</span></td>
                        <td><Badge tone={reviewTone(race.review_status)}>{race.review_status.toUpperCase()}</Badge></td>
                        <td>{race.reviewed_by_name ?? <span style={{ color: 'var(--ink-faint)' }}>—</span>}</td>
                        <td>
                          {race.runner_vod_url
                            ? <a href={safeHref(race.runner_vod_url)} target="_blank" rel="noopener noreferrer" title="Watch VoD" style={{ color: 'var(--teal)' }}>▶</a>
                            : <span style={{ color: 'var(--ink-faint)' }}>—</span>}
                        </td>
                        <td><Link to={`/async/races/${id}/review/${race.id}`}>review →</Link></td>
                      </tr>
                    ))}

                    {pageState.status === 'ready' && races.length === 0 && (
                      <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--ink-soft)', padding: '2.5rem' }}>
                        No runs match the current filters.
                      </td></tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div style={{ display: 'flex', gap: '.8rem', alignItems: 'center', marginTop: '1.2rem' }}>
                <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => goPage(page - 1)}>← Prev</button>
                <span style={{ color: 'var(--ink-soft)', fontFamily: "'Space Mono', monospace", fontSize: '.85rem' }}>Page {page}</span>
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={pageState.status === 'ready' && races.length < pageState.data.page_size}
                  onClick={() => goPage(page + 1)}
                >Next →</button>
              </div>
            </>
          )}

        </div>
      </section>
    </>
  );
}

function FilterSelect({
  label, value, opts, onChange,
}: {
  label: string;
  value: string;
  opts: ReadonlyArray<readonly [string, string]>;
  onChange: (v: string) => void;
}) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: '.35rem' }}>
      <span style={{ fontSize: '.78rem', color: 'var(--ink-faint)', textTransform: 'uppercase', letterSpacing: '.05em' }}>{label}</span>
      <select className="control" style={{ minWidth: '10rem' }} value={value} onChange={(e) => onChange(e.target.value)}>
        {opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  );
}
