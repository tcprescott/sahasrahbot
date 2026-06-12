import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { safeHref } from '../../lib/safeHref';
import '../../styles/submit.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ReattemptData {
  tournament: { id: number; name: string; active: boolean };
  race: {
    id: number;
    status: string;
    elapsed_time: string | null;
    pool_name: string;
    permalink_url: string;
  };
}

type PageState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'already' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: ReattemptData };

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function AsyncReattemptPage() {
  const { id } = useParams<{ id: string }>();
  const [params] = useSearchParams();
  const raceId = params.get('race_id');
  const navigate = useNavigate();

  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setPageState({ status: 'loading' });
    try {
      const r = await fetch(`/async/races/${id}/reattempt.json?race_id=${encodeURIComponent(raceId ?? '')}`);
      if (r.status === 401) { setPageState({ status: 'unauthenticated' }); return; }
      if (r.status === 403) { setPageState({ status: 'already' }); return; }
      if (!r.ok) {
        const body = (await r.json().catch(() => ({}))) as { error?: string };
        setPageState({ status: 'error', message: body.error ?? `Failed to load (${r.status}).` });
        return;
      }
      const body = (await r.json()) as ReattemptData;
      setPageState({ status: 'ready', data: body });
    } catch (e) {
      setPageState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load.' });
    }
  }, [id, raceId]);

  useEffect(() => { void load(); }, [load]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setSubmitting(true);
    try {
      const r = await fetch(`/async/races/${id}/reattempt.json`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ race_id: Number(raceId), reason }),
      });
      const body = (await r.json().catch(() => ({}))) as { success?: boolean; error?: string };
      if (!r.ok || body.error) {
        setSubmitError(body.error ?? `Submission failed (${r.status}).`);
        return;
      }
      navigate(`/async/races/${id}`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setSubmitting(false);
    }
  }

  const tournamentName =
    pageState.status === 'ready' ? pageState.data.tournament.name : `Tournament #${id ?? ''}`;

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
            <Link to={`/async/races/${id}`}>Dashboard</Link>
            <span className="sep">/</span>
            <span>Reattempt</span>
          </nav>
          <h1 className="sb-title reveal d2">REATTEMPT REQUEST</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            {pageState.status === 'ready' && <Badge tone="gold">{tournamentName}</Badge>}
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap" style={{ maxWidth: 720 }}>

          {pageState.status === 'loading' && (
            <div className="panel">
              <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
                {[60, 80, 70, 50].map((pct, i) => (
                  <div key={i} className="skel" style={{ width: `${pct}%`, height: '1.6rem', borderRadius: 8 }} />
                ))}
              </div>
            </div>
          )}

          {pageState.status === 'unauthenticated' && (
            <div className="panel">
              <div className="auth-prompt">
                <div className="auth-icon">🔒</div>
                <p>Sign in with Discord to request a reattempt.</p>
                <a className="btn btn-primary" href={`/login/?next=/async/races/${id}/reattempt?race_id=${raceId ?? ''}`}>
                  Sign in with Discord <span className="arr">→</span>
                </a>
              </div>
            </div>
          )}

          {pageState.status === 'already' && (
            <div className="panel">
              <div className="panel-head"><h3>Reattempt unavailable</h3><Badge tone="gold">used</Badge></div>
              <div className="panel-body">
                <p style={{ color: 'var(--ink-soft)' }}>
                  You have already used your reattempt for this tournament. If you believe this is in error,
                  contact a tournament admin.
                </p>
                <div className="form-actions">
                  <Link className="btn btn-ghost" to={`/async/races/${id}`}>Back to dashboard</Link>
                </div>
              </div>
            </div>
          )}

          {pageState.status === 'error' && (
            <div className="panel">
              <div className="panel-body">
                <div className="alert alert-error" role="alert">
                  <span className="alert-icon">⚠</span>
                  <p>{pageState.message}</p>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => void load()}>Retry</button>
              </div>
            </div>
          )}

          {pageState.status === 'ready' && (
            <div className="panel onscroll">
              <div className="panel-head"><h3>Confirm reattempt</h3><Badge tone="crimson" dot>one-time</Badge></div>
              <div className="panel-body">
                <div className="alert alert-error" role="alert">
                  <span className="alert-icon">⚠</span>
                  <p>This action cannot be undone. You are allowed one reattempt per tournament.</p>
                </div>

                <div style={{ marginBottom: '1.4rem', display: 'grid', gap: '.5rem' }}>
                  <Row label="Pool" value={pageState.data.race.pool_name} />
                  <Row label="Time" value={pageState.data.race.elapsed_time ?? '—'} mono />
                  <Row
                    label="Permalink"
                    value={
                      <a href={safeHref(pageState.data.race.permalink_url)} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--teal)' }}>
                        {pageState.data.race.permalink_url}
                      </a>
                    }
                  />
                </div>

                {submitError && (
                  <div className="alert alert-error" role="alert">
                    <span className="alert-icon">⚠</span>
                    <p>{submitError}</p>
                  </div>
                )}

                <form onSubmit={(e) => void handleSubmit(e)} noValidate>
                  <div className="field">
                    <label htmlFor="reason">Reason for reattempt</label>
                    <textarea
                      id="reason"
                      className="control"
                      rows={4}
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="Briefly explain why you are reattempting this run."
                      disabled={submitting}
                    />
                  </div>
                  <div className="form-actions">
                    <button className="btn btn-primary" type="submit" disabled={submitting}>
                      {submitting
                        ? (<><span className="spinner" aria-hidden="true" />Submitting…</>)
                        : (<>Confirm reattempt <span className="arr">→</span></>)}
                    </button>
                    <Link className="btn btn-ghost" to={`/async/races/${id}`}>Cancel</Link>
                  </div>
                </form>
              </div>
            </div>
          )}

        </div>
      </section>
    </>
  );
}

function Row({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <span style={{ color: 'var(--ink-faint)', minWidth: '6rem', fontSize: '.85rem' }}>{label}</span>
      <span style={{ color: 'var(--ink)', fontFamily: mono ? "'Space Mono', monospace" : undefined, wordBreak: 'break-all' }}>
        {value}
      </span>
    </div>
  );
}
