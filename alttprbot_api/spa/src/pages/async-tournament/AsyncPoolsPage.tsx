import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { safeHref } from '../../lib/safeHref';
import '../../styles/submit.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PoolPermalink {
  id: number;
  url: string;
  notes: string | null;
  par_time: string | null;
  live_race: boolean;
}

interface Pool {
  id: number;
  name: string;
  preset: string | null;
  permalinks: PoolPermalink[];
}

interface PoolsData {
  tournament: { id: number; name: string; active: boolean };
  pools: Pool[];
}

type PageState =
  | { status: 'loading' }
  | { status: 'forbidden' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: PoolsData };

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function AsyncPoolsPage() {
  const { id } = useParams<{ id: string }>();
  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });

  const load = useCallback(async () => {
    if (!id) return;
    setPageState({ status: 'loading' });
    try {
      const r = await fetch(`/async/pools/${id}/data.json`);
      if (r.status === 403) { setPageState({ status: 'forbidden' }); return; }
      if (!r.ok) {
        const body = (await r.json().catch(() => ({}))) as { error?: string };
        setPageState({ status: 'error', message: body.error ?? `Failed to load (${r.status}).` });
        return;
      }
      const body = (await r.json()) as PoolsData;
      setPageState({ status: 'ready', data: body });
    } catch (e) {
      setPageState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load pools.' });
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  const data = pageState.status === 'ready' ? pageState.data : null;
  const tournamentName = data?.tournament.name ?? `Tournament #${id ?? ''}`;
  const isActive = data?.tournament.active ?? false;

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
            <span>Pools</span>
          </nav>
          <h1 className="sb-title reveal d2">POOLS</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            {data && <Badge tone="gold">{tournamentName}</Badge>}
            {data && <Badge tone={isActive ? 'teal' : 'default'} dot={isActive}>{isActive ? 'LIVE' : 'CLOSED'}</Badge>}
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
              {[60, 90, 75].map((p, i) => <div key={i} className="skel" style={{ width: `${p}%`, height: '1.6rem', borderRadius: 8 }} />)}
            </div></div>
          )}

          {pageState.status === 'ready' && pageState.data.pools.length === 0 && (
            <div className="panel"><div className="panel-body">
              <p style={{ color: 'var(--ink-soft)', textAlign: 'center', padding: '2rem' }}>No pools configured.</p>
            </div></div>
          )}

          {pageState.status === 'ready' && pageState.data.pools.map((pool) => (
            <div className="panel onscroll" key={pool.id} style={{ marginBottom: '1.4rem' }}>
              <div className="panel-head">
                <h3>{pool.name}</h3>
                {pool.preset && <Badge>{pool.preset}</Badge>}
              </div>
              <div className="panel-body" style={{ padding: 0 }}>
                <div className="table-wrap" style={{ border: 'none' }}>
                  <table className="data">
                    <thead>
                      <tr><th>Permalink</th><th>Notes</th><th>Par Time</th><th>Live</th></tr>
                    </thead>
                    <tbody>
                      {pool.permalinks.map((p) => (
                        <tr key={p.id}>
                          <td>
                            <Link to={`/async/permalink/${id}/${p.id}`}>view</Link>
                            {' · '}
                            <a href={safeHref(p.url)} target="_blank" rel="noopener noreferrer" style={{ wordBreak: 'break-all' }}>permalink ↗</a>
                          </td>
                          <td>{p.notes ?? <span style={{ color: 'var(--ink-faint)' }}>—</span>}</td>
                          <td><span className="num">{p.par_time ?? '—'}</span></td>
                          <td>{p.live_race ? <Badge tone="teal">LIVE</Badge> : <span style={{ color: 'var(--ink-faint)' }}>—</span>}</td>
                        </tr>
                      ))}
                      {pool.permalinks.length === 0 && (
                        <tr><td colSpan={4} style={{ color: 'var(--ink-faint)', padding: '1.2rem' }}>No permalinks in this pool.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ))}

        </div>
      </section>
    </>
  );
}
