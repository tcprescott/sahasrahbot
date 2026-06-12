import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../components/ui/Badge';
import '../styles/submit.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Candidate { id: number; name: string }

interface BallotData {
  election: { id: number; name: string; description: string | null; candidates: Candidate[] };
  existing_votes: Array<{ candidate_id: number; rank: number }> | null;
  already_voted: boolean;
}

interface MeData { id: string; name: string }

async function fetchMe(): Promise<MeData | null> {
  const r = await fetch('/api/me');
  if (r.status === 401) return null;
  if (!r.ok) throw new Error(`/api/me returned ${r.status}`);
  const body = (await r.json()) as { data: MeData };
  return body.data;
}

type PageState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: BallotData };

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function RankedChoicePage() {
  const { id } = useParams<{ id: string }>();

  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });
  // rank selections keyed by candidate id; '' means unranked
  const [ranks, setRanks] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [voted, setVoted] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setPageState({ status: 'loading' });
    try {
      const me = await fetchMe();
      if (!me) { setPageState({ status: 'unauthenticated' }); return; }
      const r = await fetch(`/ranked_choice/${id}/api`);
      if (!r.ok) {
        const body = (await r.json().catch(() => ({}))) as { error?: string };
        setPageState({ status: 'error', message: body.error ?? `Failed to load (${r.status}).` });
        return;
      }
      const body = (await r.json()) as BallotData;
      setVoted(body.already_voted);
      setPageState({ status: 'ready', data: body });
    } catch (e) {
      setPageState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load ballot.' });
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  function setRank(candidateId: number, value: string) {
    setRanks((prev) => ({ ...prev, [candidateId]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    const votes = Object.entries(ranks)
      .filter(([, v]) => v !== '')
      .map(([cid, v]) => ({ candidate_id: Number(cid), rank: Number(v) }));

    if (votes.length === 0) { setSubmitError('Rank at least one candidate.'); return; }
    const usedRanks = votes.map((v) => v.rank);
    if (usedRanks.length !== new Set(usedRanks).size) { setSubmitError('Each rank must be unique.'); return; }

    setSubmitting(true);
    try {
      const r = await fetch(`/ranked_choice/${id}/api`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ votes }),
      });
      const body = (await r.json().catch(() => ({}))) as { success?: boolean; error?: string };
      if (!r.ok || body.error) { setSubmitError(body.error ?? `Submission failed (${r.status}).`); return; }
      // Transition to "already voted" read-only state using current selections.
      if (pageState.status === 'ready') {
        setPageState({
          status: 'ready',
          data: { ...pageState.data, already_voted: true, existing_votes: votes.map((v) => ({ candidate_id: v.candidate_id, rank: v.rank })) },
        });
      }
      setVoted(true);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setSubmitting(false);
    }
  }

  const data = pageState.status === 'ready' ? pageState.data : null;
  const candidates = data?.election.candidates ?? [];

  return (
    <>
      <section className="pagehead">
        <div className="glow" />
        <div className="grid" />
        <div className="wrap">
          <nav className="crumb reveal d1" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span className="sep">/</span>
            <span>Ranked Choice</span>
          </nav>
          <h1 className="sb-title reveal d2">RANKED CHOICE</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            {data && <Badge tone="gold">{data.election.name}</Badge>}
            {voted && <Badge tone="teal" dot>voted</Badge>}
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap" style={{ maxWidth: 760 }}>

          {pageState.status === 'unauthenticated' && (
            <div className="panel"><div className="auth-prompt">
              <div className="auth-icon">🔒</div>
              <p>Sign in with Discord to cast your ballot.</p>
              <a className="btn btn-primary" href={`/login/?next=/ranked_choice/${id}`}>
                Sign in with Discord <span className="arr">→</span>
              </a>
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
              {[60, 80, 70, 50].map((p, i) => <div key={i} className="skel" style={{ width: `${p}%`, height: '2.2rem', borderRadius: 8 }} />)}
            </div></div>
          )}

          {pageState.status === 'ready' && data && (
            data.already_voted ? (
              <div className="panel onscroll">
                <div className="panel-head"><h3>Your votes are locked</h3><Badge tone="teal" dot>submitted</Badge></div>
                <div className="panel-body">
                  <p style={{ color: 'var(--ink-soft)', marginBottom: '1.2rem' }}>
                    You have already voted in this election. Your rankings are shown below.
                  </p>
                  <div className="table-wrap">
                    <table className="data">
                      <thead><tr><th>Rank</th><th>Candidate</th></tr></thead>
                      <tbody>
                        {(data.existing_votes ?? [])
                          .slice()
                          .sort((a, b) => a.rank - b.rank)
                          .map((v) => {
                            const c = candidates.find((cand) => cand.id === v.candidate_id);
                            return (
                              <tr key={v.candidate_id}>
                                <td><span className="num">{v.rank}</span></td>
                                <td>{c?.name ?? `Candidate #${v.candidate_id}`}</td>
                              </tr>
                            );
                          })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : (
              <div className="panel onscroll">
                <div className="panel-head"><h3>Cast your ballot</h3></div>
                <div className="panel-body">
                  {data.election.description && (
                    <p style={{ color: 'var(--ink-soft)', marginBottom: '1.4rem' }}>{data.election.description}</p>
                  )}
                  <p style={{ color: 'var(--ink-faint)', fontSize: '.85rem', marginBottom: '1.4rem' }}>
                    Assign a unique rank to the candidates you wish to vote for. Leave a candidate unranked to omit them.
                  </p>
                  {submitError && <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{submitError}</p></div>}
                  <form onSubmit={(e) => void handleSubmit(e)} noValidate>
                    {candidates.map((c) => (
                      <div className="field" key={c.id} style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                        <label htmlFor={`cand-${c.id}`} style={{ flex: 1, margin: 0 }}>{c.name}</label>
                        <select
                          id={`cand-${c.id}`}
                          className="control"
                          style={{ width: '8rem' }}
                          value={ranks[c.id] ?? ''}
                          onChange={(e) => setRank(c.id, e.target.value)}
                          disabled={submitting}
                        >
                          <option value="">—</option>
                          {candidates.map((_, idx) => <option key={idx + 1} value={idx + 1}>{idx + 1}</option>)}
                        </select>
                      </div>
                    ))}
                    <div className="form-actions">
                      <button className="btn btn-primary" type="submit" disabled={submitting}>
                        {submitting ? (<><span className="spinner" aria-hidden="true" />Submitting…</>) : (<>Submit ballot <span className="arr">→</span></>)}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )
          )}

        </div>
      </section>
    </>
  );
}
