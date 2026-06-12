import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Badge } from '../components/ui/Badge';
import '../styles/submit.css';

// ---------------------------------------------------------------------------
// Account purge — deletes the user's preset namespaces and nick verifications.
// ---------------------------------------------------------------------------

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

export function PurgeMePage() {
  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });
  const [confirmed, setConfirmed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  async function handlePurge() {
    setError(null);
    setSubmitting(true);
    try {
      const r = await fetch('/purgeme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmpurge: 'yes' }),
      });
      const body = (await r.json().catch(() => ({}))) as { success?: boolean; redirect?: string; error?: string };
      if (!r.ok || body.error) { setError(body.error ?? `Purge failed (${r.status}).`); return; }
      window.location.href = body.redirect ?? '/logout/';
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
            <Link to="/me">Profile</Link>
            <span className="sep">/</span>
            <span>Delete my data</span>
          </nav>
          <h1 className="sb-title reveal d2">DELETE MY DATA</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            <Badge tone="crimson" dot>destructive</Badge>
            {pageState.status === 'ready' && <Badge tone="teal" dot>Signed in as {pageState.userName}</Badge>}
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">
          {pageState.status === 'loading' && (
            <div className="panel"><div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {[70, 50].map((p, i) => <div key={i} className="skel" style={{ width: `${p}%`, height: '2.4rem', borderRadius: 10 }} />)}
            </div></div>
          )}

          {pageState.status === 'unauthenticated' && (
            <div className="panel"><div className="auth-prompt">
              <div className="auth-icon">🔒</div>
              <p>Sign in with Discord to manage your account data.</p>
              <a className="btn btn-primary" href="/login/?next=/purgeme">
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
            <div className="panel" style={{ maxWidth: 560 }}>
              <div className="panel-head"><h3>Delete my data</h3></div>
              <div className="panel-body">
                <div className="alert alert-error" role="alert">
                  <span className="alert-icon">⚠</span>
                  <p>
                    This permanently deletes your preset namespaces (and all presets within them)
                    and your RaceTime/nick verifications. This action cannot be undone, and you will
                    be signed out afterward.
                  </p>
                </div>
                {error && <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{error}</p></div>}
                <div className="field" style={{ display: 'flex', alignItems: 'center', gap: '.6rem' }}>
                  <input
                    id="confirmpurge"
                    type="checkbox"
                    checked={confirmed}
                    onChange={(e) => setConfirmed(e.target.checked)}
                    disabled={submitting}
                  />
                  <label htmlFor="confirmpurge" style={{ margin: 0 }}>
                    I understand this is permanent and want to delete my data.
                  </label>
                </div>
                <div className="form-actions">
                  <button
                    className="btn btn-primary"
                    onClick={() => void handlePurge()}
                    disabled={!confirmed || submitting}
                  >
                    {submitting ? (<><span className="spinner" aria-hidden="true" />Deleting…</>) : (<>Delete my data</>)}
                  </button>
                  <Link className="btn btn-ghost" to="/me">Cancel</Link>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
