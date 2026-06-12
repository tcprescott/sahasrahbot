import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Badge } from '../components/ui/Badge';
import '../styles/submit.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TextItem {
  id: number;
  text: string;
  author: string | null;
  approved: boolean | null;
}

interface ModerationData {
  pool_name: string;
  filter: string;
  texts: TextItem[];
}

type PageState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'forbidden' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: ModerationData };

interface MeData { id: string; name: string }

async function fetchMe(): Promise<MeData | null> {
  const r = await fetch('/api/me');
  if (r.status === 401) return null;
  if (!r.ok) throw new Error(`/api/me returned ${r.status}`);
  const body = (await r.json()) as { data: MeData };
  return body.data;
}

const FILTERS = [['pending', 'Pending'], ['true', 'Approved'], ['false', 'Rejected']] as const;

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function TriforceTextsModerationPage() {
  const { pool } = useParams<{ pool: string }>();
  const safePool = pool ?? '';
  const [params, setParams] = useSearchParams();
  const filter = params.get('approved') ?? 'pending';

  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setPageState({ status: 'loading' });
    try {
      const me = await fetchMe();
      if (!me) { setPageState({ status: 'unauthenticated' }); return; }
      const r = await fetch(`/triforcetexts/${encodeURIComponent(safePool)}/moderation/api?approved=${filter}`);
      if (r.status === 403) { setPageState({ status: 'forbidden' }); return; }
      if (!r.ok) {
        const body = (await r.json().catch(() => ({}))) as { error?: string };
        setPageState({ status: 'error', message: body.error ?? `Failed to load (${r.status}).` });
        return;
      }
      const body = (await r.json()) as ModerationData;
      setPageState({ status: 'ready', data: body });
    } catch (e) {
      setPageState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load.' });
    }
  }, [safePool, filter]);

  useEffect(() => { void load(); }, [load]);

  function setFilter(value: string) {
    const next = new URLSearchParams(params);
    next.set('approved', value);
    setParams(next);
  }

  async function act(textId: number, action: 'approve' | 'reject') {
    setBusyId(textId);
    try {
      const r = await fetch(`/triforcetexts/${encodeURIComponent(safePool)}/moderation/api/${textId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });
      const body = (await r.json().catch(() => ({}))) as { success?: boolean; approved?: boolean; error?: string };
      if (r.ok && body.success && pageState.status === 'ready') {
        // Update in place; drop from list if it no longer matches the active filter.
        const stillMatches =
          filter === 'pending' ? false
            : filter === 'true' ? body.approved === true
              : body.approved === false;
        setPageState({
          status: 'ready',
          data: {
            ...pageState.data,
            texts: stillMatches
              ? pageState.data.texts.map((t) => (t.id === textId ? { ...t, approved: body.approved ?? null } : t))
              : pageState.data.texts.filter((t) => t.id !== textId),
          },
        });
      }
    } finally {
      setBusyId(null);
    }
  }

  const texts = pageState.status === 'ready' ? pageState.data.texts : [];

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
            <span className="sep">/</span>
            <span>Moderation</span>
          </nav>
          <h1 className="sb-title reveal d2">TEXT MODERATION</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            <Badge tone="gold">Pool: {safePool}</Badge>
            <Badge tone="crimson">MODERATOR</Badge>
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">

          {pageState.status === 'unauthenticated' && (
            <div className="panel"><div className="auth-prompt">
              <div className="auth-icon">🔒</div>
              <p>Sign in with Discord to moderate triforce texts.</p>
              <a className="btn btn-primary" href={`/login/?next=/triforcetexts/${encodeURIComponent(safePool)}/moderation`}>
                Sign in with Discord <span className="arr">→</span>
              </a>
            </div></div>
          )}

          {pageState.status === 'forbidden' && (
            <div className="panel"><div className="panel-body">
              <div className="alert alert-error"><span className="alert-icon">⚠</span><p>You are not a moderator for this pool.</p></div>
            </div></div>
          )}

          {pageState.status === 'error' && (
            <div className="panel"><div className="panel-body">
              <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{pageState.message}</p></div>
              <button className="btn btn-ghost btn-sm" onClick={() => void load()}>Retry</button>
            </div></div>
          )}

          {(pageState.status === 'loading' || pageState.status === 'ready') && (
            <>
              {/* Filter tabs */}
              <div className="onscroll" style={{ display: 'flex', gap: '.6rem', marginBottom: '1.4rem', flexWrap: 'wrap' }}>
                {FILTERS.map(([v, l]) => (
                  <button
                    key={v}
                    className={`btn btn-sm ${filter === v ? 'btn-primary' : 'btn-ghost'}`}
                    onClick={() => setFilter(v)}
                  >{l}</button>
                ))}
              </div>

              {pageState.status === 'loading' && (
                <div style={{ display: 'grid', gap: '1rem' }}>
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="panel"><div className="panel-body">
                      <div className="skel" style={{ width: '40%', height: '1rem', marginBottom: '.8rem' }} />
                      <div className="skel" style={{ width: '70%', height: '2.4rem', borderRadius: 8 }} />
                    </div></div>
                  ))}
                </div>
              )}

              {pageState.status === 'ready' && texts.length === 0 && (
                <div className="panel"><div className="panel-body">
                  <p style={{ color: 'var(--ink-soft)', textAlign: 'center', padding: '2rem' }}>No texts in this category.</p>
                </div></div>
              )}

              {pageState.status === 'ready' && texts.length > 0 && (
                <div style={{ display: 'grid', gap: '1rem' }}>
                  {texts.map((t) => {
                    const lines = t.text.split('\n');
                    return (
                      <div className="panel" key={t.id}>
                        <div className="panel-head">
                          <h3 style={{ fontSize: '.95rem' }}>{t.author ?? 'Anonymous'}</h3>
                          {t.approved === true && <Badge tone="teal" dot>approved</Badge>}
                          {t.approved === false && <Badge tone="crimson" dot>rejected</Badge>}
                          {t.approved === null && <Badge>pending</Badge>}
                        </div>
                        <div className="panel-body">
                          <div style={{
                            fontFamily: "'Space Mono', monospace", background: 'var(--bg-3)',
                            border: '1px dashed var(--line-glow)', borderRadius: 10, padding: '1rem 1.2rem',
                            color: 'var(--gold)', marginBottom: '1.2rem', whiteSpace: 'pre',
                          }}>
                            {lines.map((line, idx) => <div key={idx}>{line || ' '}</div>)}
                          </div>
                          <div className="form-actions">
                            {t.approved !== true && (
                              <button className="btn btn-primary btn-sm" disabled={busyId === t.id} onClick={() => void act(t.id, 'approve')}>✓ Approve</button>
                            )}
                            {t.approved !== false && (
                              <button className="btn btn-ghost btn-sm" disabled={busyId === t.id} onClick={() => void act(t.id, 'reject')}>✕ Reject</button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}

        </div>
      </section>
    </>
  );
}
