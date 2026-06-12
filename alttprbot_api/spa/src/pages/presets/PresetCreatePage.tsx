import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import '../../styles/submit.css';

// ---------------------------------------------------------------------------
// Create a new preset within a namespace (owner only). Reuses the namespace
// data.json endpoint for ownership + the list of randomizers.
// ---------------------------------------------------------------------------

interface NamespaceData {
  namespace: string;
  is_owner: boolean;
  randomizers: string[];
}

type PageState =
  | { status: 'loading' }
  | { status: 'unauthorized' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: NamespaceData };

const PRESET_NAME_REGEX = /^[a-zA-Z0-9_]*$/;

export function PresetCreatePage() {
  const { namespace } = useParams<{ namespace: string }>();
  const safeNs = namespace ?? '';
  const navigate = useNavigate();

  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });
  const [presetName, setPresetName] = useState('');
  const [randomizer, setRandomizer] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setPageState({ status: 'loading' });
    try {
      const r = await fetch(`/presets/manage/${encodeURIComponent(safeNs)}/data.json`);
      const body = (await r.json().catch(() => ({}))) as NamespaceData & { error?: string };
      if (!r.ok || body.error) { setPageState({ status: 'error', message: body.error ?? `Failed to load (${r.status}).` }); return; }
      if (!body.is_owner) { setPageState({ status: 'unauthorized' }); return; }
      setPageState({ status: 'ready', data: body });
      setRandomizer((prev) => prev || body.randomizers[0] || '');
    } catch (e) {
      setPageState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load.' });
    }
  }, [safeNs]);

  useEffect(() => { void load(); }, [load]);

  const nameValid = PRESET_NAME_REGEX.test(presetName) && presetName.length > 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!nameValid) { setError('Preset name may only contain letters, numbers, and underscores.'); return; }
    if (!file) { setError('Select a preset file to upload.'); return; }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('preset_name', presetName);
      fd.append('randomizer', randomizer);
      fd.append('presetfile', file);
      const r = await fetch(`/presets/${encodeURIComponent(safeNs)}/create`, { method: 'POST', body: fd });
      const body = (await r.json().catch(() => ({}))) as { success?: boolean; redirect?: string; error?: string };
      if (!r.ok || body.error) { setError(body.error ?? `Create failed (${r.status}).`); return; }
      navigate(body.redirect ?? `/presets/manage/${encodeURIComponent(safeNs)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setBusy(false);
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
            <Link to="/presets">Presets</Link>
            <span className="sep">/</span>
            <Link to={`/presets/manage/${encodeURIComponent(safeNs)}`}>{safeNs}</Link>
            <span className="sep">/</span>
            <span>New preset</span>
          </nav>
          <h1 className="sb-title reveal d2">NEW PRESET</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            <Badge tone="gold">{safeNs}</Badge>
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">
          {pageState.status === 'loading' && (
            <div className="panel"><div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {[70, 60, 50].map((p, i) => <div key={i} className="skel" style={{ width: `${p}%`, height: '2.4rem', borderRadius: 10 }} />)}
            </div></div>
          )}

          {pageState.status === 'unauthorized' && (
            <div className="panel"><div className="panel-body">
              <div className="alert alert-error"><span className="alert-icon">⚠</span>
                <p>You are not authorized to create presets in this namespace.</p>
              </div>
              <Link className="btn btn-ghost btn-sm" to={`/presets/manage/${encodeURIComponent(safeNs)}`}>Back to namespace</Link>
            </div></div>
          )}

          {pageState.status === 'error' && (
            <div className="panel"><div className="panel-body">
              <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{pageState.message}</p></div>
              <button className="btn btn-ghost btn-sm" onClick={() => void load()}>Retry</button>
            </div></div>
          )}

          {pageState.status === 'ready' && (
            <div className="panel onscroll" style={{ maxWidth: 560 }}>
              <div className="panel-head"><h3>Preset details</h3></div>
              <div className="panel-body">
                {error && <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{error}</p></div>}
                <form onSubmit={(e) => void handleSubmit(e)} noValidate>
                  <div className="field">
                    <label htmlFor="preset_name">Preset name <span className="req">*</span></label>
                    <input
                      id="preset_name"
                      className={`control${presetName.length > 0 && !nameValid ? ' error' : ''}`}
                      value={presetName}
                      onChange={(e) => setPresetName(e.target.value)}
                      placeholder="my_preset"
                      autoComplete="off"
                      disabled={busy}
                    />
                    {presetName.length > 0 && !nameValid && (
                      <p className="hint" style={{ color: 'var(--crimson)' }}>Only letters, numbers, and underscores are allowed.</p>
                    )}
                  </div>
                  <div className="field">
                    <label htmlFor="randomizer">Randomizer</label>
                    <select
                      id="randomizer"
                      className="control"
                      value={randomizer}
                      onChange={(e) => setRandomizer(e.target.value)}
                      disabled={busy}
                    >
                      {pageState.data.randomizers.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="presetfile">Preset file <span className="req">*</span></label>
                    <input
                      id="presetfile"
                      type="file"
                      className="control"
                      accept=".yaml,.yml"
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                      disabled={busy}
                    />
                  </div>
                  <div className="form-actions">
                    <button className="btn btn-primary" type="submit" disabled={busy || !nameValid || !file}>
                      {busy ? (<><span className="spinner" aria-hidden="true" />Creating…</>) : (<>Create preset <span className="arr">→</span></>)}
                    </button>
                    <Link className="btn btn-ghost" to={`/presets/manage/${encodeURIComponent(safeNs)}`}>Cancel</Link>
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
