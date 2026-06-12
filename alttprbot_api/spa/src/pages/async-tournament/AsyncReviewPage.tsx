import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import { safeHref } from '../../lib/safeHref';
import '../../styles/submit.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ReviewRace {
  id: number;
  status: string;
  review_status: string;
  elapsed_time: string | null;
  score_formatted: string | null;
  created: string | null;
  start_time: string | null;
  end_time: string | null;
  runner_notes: string | null;
  runner_vod_url: string | null;
  run_collection_rate: string | null;
  run_igt: string | null;
  reattempted: boolean;
  reviewer_notes: string | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
  pool_name: string;
  permalink_url: string;
  permalink_notes: string | null;
  user_id: number;
  user_display_name: string;
}

interface ReviewData {
  tournament: { id: number; name: string };
  race: ReviewRace;
  reviewable: boolean;
  already_claimed: boolean;
  reviewer_is_self: boolean;
}

type PageState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'forbidden' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: ReviewData };

function reviewTone(s: string): 'teal' | 'crimson' | 'default' {
  if (s === 'approved') return 'teal';
  if (s === 'rejected') return 'crimson';
  return 'default';
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function AsyncReviewPage() {
  const { id, raceId } = useParams<{ id: string; raceId: string }>();
  const navigate = useNavigate();

  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });
  const [reviewStatus, setReviewStatus] = useState('pending');
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id || !raceId) return;
    setPageState({ status: 'loading' });
    try {
      const r = await fetch(`/async/races/${id}/review/${raceId}/data.json`);
      if (r.status === 401) { setPageState({ status: 'unauthenticated' }); return; }
      if (r.status === 403) { setPageState({ status: 'forbidden' }); return; }
      if (!r.ok) {
        const body = (await r.json().catch(() => ({}))) as { error?: string };
        setPageState({ status: 'error', message: body.error ?? `Failed to load (${r.status}).` });
        return;
      }
      const body = (await r.json()) as ReviewData;
      setReviewStatus(body.race.review_status || 'pending');
      setReviewerNotes(body.race.reviewer_notes ?? '');
      setPageState({ status: 'ready', data: body });
    } catch (e) {
      setPageState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load review.' });
    }
  }, [id, raceId]);

  useEffect(() => { void load(); }, [load]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setSubmitting(true);
    try {
      const r = await fetch(`/async/races/${id}/review/${raceId}/submit.json`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ review_status: reviewStatus, reviewer_notes: reviewerNotes }),
      });
      const body = (await r.json().catch(() => ({}))) as { success?: boolean; error?: string };
      if (!r.ok || body.error) {
        setSubmitError(body.error ?? `Submission failed (${r.status}).`);
        return;
      }
      navigate(`/async/races/${id}/queue`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setSubmitting(false);
    }
  }

  const race = pageState.status === 'ready' ? pageState.data.race : null;

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
            <Link to={`/async/races/${id}/queue`}>Queue</Link>
            <span className="sep">/</span>
            <span>Review</span>
          </nav>
          <h1 className="sb-title reveal d2">RACE REVIEW</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            {race && <Badge tone="gold">{race.user_display_name}</Badge>}
            {race && <Badge tone={reviewTone(race.review_status)}>{race.review_status.toUpperCase()}</Badge>}
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">

          {pageState.status === 'unauthenticated' && (
            <div className="panel"><div className="auth-prompt">
              <div className="auth-icon">🔒</div>
              <p>Sign in with Discord to review this run.</p>
              <a className="btn btn-primary" href={`/login/?next=/async/races/${id}/review/${raceId}`}>
                Sign in with Discord <span className="arr">→</span>
              </a>
            </div></div>
          )}

          {pageState.status === 'forbidden' && (
            <div className="panel"><div className="panel-body">
              <div className="alert alert-error"><span className="alert-icon">⚠</span><p>Admin or moderator access required.</p></div>
            </div></div>
          )}

          {pageState.status === 'error' && (
            <div className="panel"><div className="panel-body">
              <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{pageState.message}</p></div>
              <button className="btn btn-ghost btn-sm" onClick={() => void load()}>Retry</button>
            </div></div>
          )}

          {pageState.status === 'loading' && (
            <div className="form-cols">
              <div className="panel"><div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {[70, 90, 60, 80, 50].map((p, i) => <div key={i} className="skel" style={{ width: `${p}%`, height: '1.2rem', borderRadius: 6 }} />)}
              </div></div>
              <div className="panel"><div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {[80, 60].map((p, i) => <div key={i} className="skel" style={{ width: `${p}%`, height: '2.2rem', borderRadius: 8 }} />)}
              </div></div>
            </div>
          )}

          {pageState.status === 'ready' && race && (
            <div className="form-cols">
              {/* Left: details */}
              <div className="panel onscroll">
                <div className="panel-head"><h3>Run details</h3></div>
                <div className="panel-body" style={{ display: 'grid', gap: '.55rem' }}>
                  <Detail label="Player" value={
                    <Link to={`/async/player/${id}/${race.user_id}`}>{race.user_display_name}</Link>
                  } />
                  <Detail label="Pool" value={race.pool_name} />
                  <Detail label="Time" value={race.elapsed_time ?? '—'} mono />
                  <Detail label="Score" value={race.score_formatted ?? '—'} mono />
                  <Detail label="Status" value={race.status} />
                  <Detail label="Collection" value={race.run_collection_rate ?? '—'} mono />
                  <Detail label="IGT" value={race.run_igt ?? '—'} mono />
                  <Detail label="Created" value={fmt(race.created)} mono />
                  <Detail label="Start" value={fmt(race.start_time)} mono />
                  <Detail label="End" value={fmt(race.end_time)} mono />
                  <Detail label="Permalink" value={
                    <a href={safeHref(race.permalink_url)} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--teal)', wordBreak: 'break-all' }}>
                      {race.permalink_url}
                    </a>
                  } />
                  <Detail label="VoD" value={
                    race.runner_vod_url
                      ? <a href={safeHref(race.runner_vod_url)} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--teal)', wordBreak: 'break-all' }}>{race.runner_vod_url}</a>
                      : '—'
                  } />
                  {race.runner_notes && (
                    <div style={{ marginTop: '.6rem' }}>
                      <div style={{ color: 'var(--ink-faint)', fontSize: '.8rem', marginBottom: '.3rem' }}>RUNNER NOTES</div>
                      <p style={{ color: 'var(--ink-soft)', whiteSpace: 'pre-wrap' }}>{race.runner_notes}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Right: review form or read-only */}
              <div className="panel onscroll">
                <div className="panel-head"><h3>Review decision</h3></div>
                <div className="panel-body">
                  {pageState.data.reviewer_is_self && (
                    <div className="alert alert-error"><span className="alert-icon">⚠</span><p>You cannot review your own run.</p></div>
                  )}
                  {pageState.data.already_claimed && !pageState.data.reviewer_is_self && (
                    <div className="alert" style={{ background: 'color-mix(in srgb, var(--gold) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--gold) 40%, transparent)', color: 'var(--gold)' }}>
                      <span className="alert-icon">⚑</span>
                      <p>This run is claimed by {race.reviewed_by_name}. You can still submit a review decision.</p>
                    </div>
                  )}
                  {!pageState.data.reviewable && (
                    <p style={{ color: 'var(--ink-faint)', marginBottom: '1rem' }}>
                      This run is not reviewable{race.reattempted ? ' (reattempted)' : race.status !== 'finished' ? ` (status: ${race.status})` : ''}.
                    </p>
                  )}

                  {pageState.data.reviewable && !pageState.data.reviewer_is_self ? (
                    <>
                      {submitError && <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{submitError}</p></div>}
                      <form onSubmit={(e) => void handleSubmit(e)} noValidate>
                        <div className="field">
                          <label htmlFor="review_status">Decision</label>
                          <select id="review_status" className="control" value={reviewStatus} onChange={(e) => setReviewStatus(e.target.value)} disabled={submitting}>
                            <option value="pending">Pending</option>
                            <option value="approved">Approved</option>
                            <option value="rejected">Rejected</option>
                          </select>
                        </div>
                        <div className="field">
                          <label htmlFor="reviewer_notes">Reviewer notes</label>
                          <textarea id="reviewer_notes" className="control" rows={5} value={reviewerNotes} onChange={(e) => setReviewerNotes(e.target.value)} disabled={submitting} />
                        </div>
                        <div className="form-actions">
                          <button className="btn btn-primary" type="submit" disabled={submitting}>
                            {submitting ? (<><span className="spinner" aria-hidden="true" />Saving…</>) : (<>Submit review <span className="arr">→</span></>)}
                          </button>
                          <Link className="btn btn-ghost" to={`/async/races/${id}/queue`}>Back to queue</Link>
                        </div>
                      </form>
                    </>
                  ) : (
                    <div style={{ display: 'grid', gap: '.55rem' }}>
                      <Detail label="Decision" value={<Badge tone={reviewTone(race.review_status)}>{race.review_status.toUpperCase()}</Badge>} />
                      <Detail label="Reviewer" value={race.reviewed_by_name ?? '—'} />
                      <Detail label="Reviewed" value={fmt(race.reviewed_at)} mono />
                      {race.reviewer_notes && (
                        <div style={{ marginTop: '.6rem' }}>
                          <div style={{ color: 'var(--ink-faint)', fontSize: '.8rem', marginBottom: '.3rem' }}>REVIEWER NOTES</div>
                          <p style={{ color: 'var(--ink-soft)', whiteSpace: 'pre-wrap' }}>{race.reviewer_notes}</p>
                        </div>
                      )}
                      <div className="form-actions">
                        <Link className="btn btn-ghost" to={`/async/races/${id}/queue`}>Back to queue</Link>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

        </div>
      </section>
    </>
  );
}

function Detail({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', gap: '1rem' }}>
      <span style={{ color: 'var(--ink-faint)', minWidth: '6.5rem', fontSize: '.82rem' }}>{label}</span>
      <span style={{ color: 'var(--ink)', fontFamily: mono ? "'Space Mono', monospace" : undefined }}>{value}</span>
    </div>
  );
}

function fmt(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}
