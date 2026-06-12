import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { safeHref } from '../../lib/safeHref';
import '../../styles/submit.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PermalinkRace {
  id: number;
  status: string;
  elapsed_time: string | null;
  score_formatted: string | null;
  review_status: string;
}

interface PermalinkData {
  tournament: { id: number; name: string; active: boolean };
  permalink: {
    id: number;
    url: string;
    notes: string | null;
    par_time: string | null;
    live_race: boolean;
    pool_name: string;
  };
  races: PermalinkRace[];
}

type PageState =
  | { status: 'loading' }
  | { status: 'forbidden' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: PermalinkData };

function reviewTone(s: string): 'teal' | 'crimson' | 'default' {
  if (s === 'approved') return 'teal';
  if (s === 'rejected') return 'crimson';
  return 'default';
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function AsyncPermalinkPage() {
  const { id, pid } = useParams<{ id: string; pid: string }>();
  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });

  const load = useCallback(async () => {
    if (!id || !pid) return;
    setPageState({ status: 'loading' });
    try {
      const r = await fetch(`/async/permalink/${id}/${pid}/data.json`);
      if (r.status === 403) { setPageState({ status: 'forbidden' }); return; }
      if (!r.ok) {
        const body = (await r.json().catch(() => ({}))) as { error?: string };
        setPageState({ status: 'error', message: body.error ?? `Failed to load (${r.status}).` });
        return;
      }
      const body = (await r.json()) as PermalinkData;
      setPageState({ status: 'ready', data: body });
    } catch (e) {
      setPageState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load permalink.' });
    }
  }, [id, pid]);

  useEffect(() => { void load(); }, [load]);

  const data = pageState.status === 'ready' ? pageState.data : null;
  const perma = data?.permalink;

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
            <Link to={`/async/pools/${id}`}>Pools</Link>
            <span className="sep">/</span>
            <span>Permalink</span>
          </nav>
          <h1 className="sb-title reveal d2">PERMALINK</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            {perma && <Badge tone="gold">{perma.pool_name}</Badge>}
            {perma?.par_time && <Badge tone="teal">par {perma.par_time}</Badge>}
            {perma?.live_race && <Badge tone="teal" dot>LIVE</Badge>}
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">

          {pageState.status === 'forbidden' && (
            <div className="panel"><div className="panel-body">
              <div className="alert alert-error"><span className="alert-icon">⚠</span><p>This tournament is active — access is restricted.</p></div>
            </div></div>
          )}

          {pageState.status === 'error' && (
            <div className="panel"><div className="panel-body">
              <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{pageState.message}</p></div>
              <button className="btn btn-ghost btn-sm" onClick={() => void load()}>Retry</button>
            </div></div>
          )}

          {pageState.status === 'loading' && (
            <div className="panel"><div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {[70, 50, 90].map((p, i) => <div key={i} className="skel" style={{ width: `${p}%`, height: '1.5rem', borderRadius: 8 }} />)}
            </div></div>
          )}

          {pageState.status === 'ready' && perma && (
            <>
              <div className="panel onscroll" style={{ marginBottom: '1.4rem' }}>
                <div className="panel-head"><h3>Permalink details</h3></div>
                <div className="panel-body" style={{ display: 'grid', gap: '.55rem' }}>
                  <Detail label="URL" value={
                    <a href={safeHref(perma.url)} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--teal)', wordBreak: 'break-all' }}>{perma.url}</a>
                  } />
                  <Detail label="Notes" value={perma.notes ?? '—'} />
                  <Detail label="Par time" value={perma.par_time ?? '—'} mono />
                  <Detail label="Live race" value={perma.live_race ? 'Yes' : 'No'} />
                </div>
              </div>

              <div className="table-wrap onscroll">
                <table className="data">
                  <thead>
                    <tr><th>Run</th><th>Status</th><th>Time</th><th>Score</th><th>Review</th></tr>
                  </thead>
                  <tbody>
                    {data.races.map((race) => (
                      <tr key={race.id}>
                        <td><Link to={`/async/races/${id}/review/${race.id}`}>#{race.id}</Link></td>
                        <td>{race.status}</td>
                        <td><span className="num">{race.elapsed_time && race.elapsed_time !== 'N/A' ? race.elapsed_time : '—'}</span></td>
                        <td><span className="num">{race.score_formatted && race.score_formatted !== 'N/A' ? race.score_formatted : '—'}</span></td>
                        <td><Badge tone={reviewTone(race.review_status)}>{race.review_status.toUpperCase()}</Badge></td>
                      </tr>
                    ))}
                    {data.races.length === 0 && (
                      <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--ink-soft)', padding: '2rem' }}>No results for this permalink yet.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}

        </div>
      </section>
    </>
  );
}

function Detail({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <span style={{ color: 'var(--ink-faint)', minWidth: '6rem', fontSize: '.82rem' }}>{label}</span>
      <span style={{ color: 'var(--ink)', fontFamily: mono ? "'Space Mono', monospace" : undefined }}>{value}</span>
    </div>
  );
}
