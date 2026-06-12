import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import '../../styles/submit.css';

// ---------------------------------------------------------------------------
// Lists presets within a namespace (optionally filtered by randomizer).
// ---------------------------------------------------------------------------

interface PresetEntry { id: number; preset_name: string; randomizer: string }

interface NamespaceData {
  namespace: string;
  is_owner: boolean;
  randomizers: string[];
  randomizer: string | null;
  presets: PresetEntry[];
}

type PageState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: NamespaceData };

export function PresetNamespacePage() {
  const { namespace, randomizer } = useParams<{ namespace: string; randomizer?: string }>();
  const safeNs = namespace ?? '';

  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });

  const load = useCallback(async () => {
    setPageState({ status: 'loading' });
    try {
      const qs = randomizer ? `?randomizer=${encodeURIComponent(randomizer)}` : '';
      const r = await fetch(`/presets/manage/${encodeURIComponent(safeNs)}/data.json${qs}`);
      const body = (await r.json().catch(() => ({}))) as NamespaceData & { error?: string };
      if (!r.ok || body.error) { setPageState({ status: 'error', message: body.error ?? `Failed to load (${r.status}).` }); return; }
      setPageState({ status: 'ready', data: body });
    } catch (e) {
      setPageState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load.' });
    }
  }, [safeNs, randomizer]);

  useEffect(() => { void load(); }, [load]);

  return (
    <>
      <section className="pagehead">
        <div className="glow" />
        <div className="grid" />
        <div className="wrap">
          <nav className="crumb reveal d1" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span className="sep">/</span>
            <Link to="/presets">Presets</Link>
            <span className="sep">/</span>
            <span>{safeNs}</span>
          </nav>
          <h1 className="sb-title reveal d2">{safeNs.toUpperCase()}</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            <Badge tone="gold">Namespace</Badge>
            {randomizer && <Badge tone="teal">{randomizer}</Badge>}
            {pageState.status === 'ready' && pageState.data.is_owner && <Badge tone="teal" dot>owner</Badge>}
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">
          {pageState.status === 'loading' && (
            <div className="panel"><div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '.8rem' }}>
              {[80, 70, 75, 60].map((p, i) => <div key={i} className="skel" style={{ width: `${p}%`, height: '2rem', borderRadius: 8 }} />)}
            </div></div>
          )}

          {pageState.status === 'error' && (
            <div className="panel"><div className="panel-body">
              <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{pageState.message}</p></div>
              <button className="btn btn-ghost btn-sm" onClick={() => void load()}>Retry</button>
            </div></div>
          )}

          {pageState.status === 'ready' && (
            <div className="panel onscroll">
              <div className="panel-head">
                <h3>Presets</h3>
                {pageState.data.is_owner && (
                  <Link className="btn btn-primary btn-sm" to={`/presets/${encodeURIComponent(safeNs)}/create`}>
                    New preset <span className="arr">→</span>
                  </Link>
                )}
              </div>
              <div className="panel-body">
                {pageState.data.presets.length === 0 ? (
                  <p style={{ color: 'var(--ink-faint)' }}>No presets in this namespace yet.</p>
                ) : (
                  <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '.5rem' }}>
                    {pageState.data.presets.map((p) => (
                      <li key={p.id} style={{ display: 'flex', alignItems: 'center', gap: '.7rem' }}>
                        <Badge tone="default">{p.randomizer}</Badge>
                        <Link
                          to={`/presets/manage/${encodeURIComponent(safeNs)}/${encodeURIComponent(p.randomizer)}/${encodeURIComponent(p.preset_name)}`}
                          style={{ fontFamily: "'Space Mono', monospace", color: 'var(--gold)' }}
                        >
                          {p.preset_name}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
