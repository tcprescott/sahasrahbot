import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../components/ui/Badge';
import '../styles/submit.css';

// ---------------------------------------------------------------------------
// Validation — must mirror the server-side allowlist regex.
// ---------------------------------------------------------------------------

const LINE_REGEX =
  /^[A-Za-z0-9 ?!,\-….~～''↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげござなにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ]{0,19}$/u;
const MAX_LEN = 19;

interface MeData { id: string; name: string; avatar_url: string }

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
  | { status: 'ready'; userName: string };

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function TriforceTextsPage() {
  const { pool } = useParams<{ pool: string }>();
  const safePool = pool ?? '';

  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });
  const [lines, setLines] = useState(['', '', '']);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const load = useCallback(async () => {
    setPageState({ status: 'loading' });
    try {
      const me = await fetchMe();
      if (!me) { setPageState({ status: 'unauthenticated' }); return; }
      setPageState({ status: 'ready', userName: me.name });
    } catch (e) {
      setPageState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load.' });
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  function setLine(i: number, value: string) {
    setLines((prev) => prev.map((l, idx) => (idx === i ? value : l)));
  }

  const lineValid = lines.map((l) => l.length <= MAX_LEN && LINE_REGEX.test(l));
  const allValid = lineValid.every(Boolean);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!allValid) { setError('One or more lines contain invalid characters or exceed 19 characters.'); return; }
    setSubmitting(true);
    try {
      const r = await fetch(`/triforcetexts/${encodeURIComponent(safePool)}/api`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ first_line: lines[0], second_line: lines[1], third_line: lines[2] }),
      });
      const body = (await r.json().catch(() => ({}))) as { success?: boolean; error?: string };
      if (!r.ok || body.error) { setError(body.error ?? `Submission failed (${r.status}).`); return; }
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <section className="pagehead">
        <div className="glow" />
        <div className="grid" />
        <div className="wrap">
          <nav className="crumb reveal d1" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span className="sep">/</span>
            <span>Triforce Texts</span>
          </nav>
          <h1 className="sb-title reveal d2">TRIFORCE TEXTS</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            <Badge tone="gold">Pool: {safePool || '—'}</Badge>
            {pageState.status === 'ready' && <Badge tone="teal" dot>Signed in as {pageState.userName}</Badge>}
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">
          {pageState.status === 'loading' && (
            <div className="panel"><div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {[60, 60, 60].map((p, i) => <div key={i} className="skel" style={{ width: `${p}%`, height: '2.4rem', borderRadius: 10 }} />)}
            </div></div>
          )}

          {pageState.status === 'unauthenticated' && (
            <div className="panel"><div className="auth-prompt">
              <div className="auth-icon">🔒</div>
              <p>Sign in with Discord to submit triforce text for this pool.</p>
              <a className="btn btn-primary" href={`/login/?next=/triforcetexts/${encodeURIComponent(safePool)}`}>
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

          {pageState.status === 'ready' && (
            <div className="form-cols">
              {success ? (
                <div className="panel success-panel">
                  <div className="panel-head"><h3>Submission received</h3><Badge tone="teal" dot>submitted</Badge></div>
                  <div className="panel-body">
                    <div className="alert alert-success"><span className="alert-icon">✓</span>
                      <p>Your text has been submitted! It will appear in-game after moderation approval.</p>
                    </div>
                    <div className="form-actions">
                      <button className="btn btn-ghost" onClick={() => { setSuccess(false); setLines(['', '', '']); }}>Submit another</button>
                      <Link className="btn btn-ghost" to="/">Return home</Link>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="panel onscroll">
                  <div className="panel-head"><h3>Your text</h3><span className="badge">{safePool}</span></div>
                  <div className="panel-body">
                    {error && <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{error}</p></div>}
                    <form onSubmit={(e) => void handleSubmit(e)} noValidate>
                      {[0, 1, 2].map((i) => {
                        const over = lines[i].length > MAX_LEN;
                        const invalid = !lineValid[i] && lines[i].length > 0;
                        return (
                          <div className="field" key={i}>
                            <label htmlFor={`line-${i}`}>
                              Line {i + 1}
                              <span style={{ float: 'right', fontFamily: "'Space Mono', monospace", fontSize: '.78rem', color: over ? 'var(--crimson)' : 'var(--ink-faint)' }}>
                                {lines[i].length}/{MAX_LEN}
                              </span>
                            </label>
                            <input
                              id={`line-${i}`}
                              className={`control${invalid ? ' error' : ''}`}
                              value={lines[i]}
                              onChange={(e) => setLine(i, e.target.value)}
                              disabled={submitting}
                              autoComplete="off"
                            />
                            {invalid && <p className="hint" style={{ color: 'var(--crimson)' }}>Contains characters outside the allowed set or exceeds {MAX_LEN} characters.</p>}
                          </div>
                        );
                      })}
                      <div className="form-actions">
                        <button className="btn btn-primary" type="submit" disabled={submitting || !allValid}>
                          {submitting ? (<><span className="spinner" aria-hidden="true" />Submitting…</>) : (<>Submit text <span className="arr">→</span></>)}
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}

              <div className="panel onscroll">
                <div className="panel-head"><h3>What is Triforce Text?</h3></div>
                <div className="panel-body">
                  <p style={{ color: 'var(--ink-soft)', fontSize: '.92rem', lineHeight: 1.6 }}>
                    Three lines of up to {MAX_LEN} characters each that appear in your copy of the randomized game.
                    Use English or Japanese characters. Submissions are reviewed by moderators before they go live.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
