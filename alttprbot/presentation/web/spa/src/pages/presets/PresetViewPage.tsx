import { useState, useEffect, useCallback } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import '../../styles/submit.css';

// ---------------------------------------------------------------------------
// View a single preset; owners can replace the file or delete it.
// ---------------------------------------------------------------------------

interface PresetData {
  namespace: string;
  is_owner: boolean;
  preset: { preset_name: string; randomizer: string; content: string };
  download_url: string;
}

type PageState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: PresetData };

export function PresetViewPage() {
  const { namespace, randomizer, preset } = useParams<{ namespace: string; randomizer: string; preset: string }>();
  const safeNs = namespace ?? '';
  const safeRand = randomizer ?? '';
  const safePreset = preset ?? '';
  const navigate = useNavigate();

  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const postUrl = `/presets/manage/${encodeURIComponent(safeNs)}/${encodeURIComponent(safeRand)}/${encodeURIComponent(safePreset)}`;

  const load = useCallback(async () => {
    setPageState({ status: 'loading' });
    try {
      const r = await fetch(`${postUrl}/data.json`);
      const body = (await r.json().catch(() => ({}))) as PresetData & { error?: string };
      if (!r.ok || body.error) { setPageState({ status: 'error', message: body.error ?? `Failed to load (${r.status}).` }); return; }
      setPageState({ status: 'ready', data: body });
    } catch (e) {
      setPageState({ status: 'error', message: e instanceof Error ? e.message : 'Failed to load.' });
    }
  }, [postUrl]);

  useEffect(() => { void load(); }, [load]);

  async function handleUpdate() {
    setActionError(null);
    if (!file) { setActionError('Select a preset file to upload.'); return; }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('presetfile', file);
      const r = await fetch(postUrl, { method: 'POST', body: fd });
      const body = (await r.json().catch(() => ({}))) as { success?: boolean; redirect?: string; error?: string };
      if (!r.ok || body.error) { setActionError(body.error ?? `Update failed (${r.status}).`); return; }
      setFile(null);
      await load();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'An unexpected error occurred.');
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setActionError(null);
    if (!window.confirm(`Delete preset "${safePreset}"? This cannot be undone.`)) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('delete', 'true');
      const r = await fetch(postUrl, { method: 'POST', body: fd });
      const body = (await r.json().catch(() => ({}))) as { success?: boolean; redirect?: string; error?: string };
      if (!r.ok || body.error) { setActionError(body.error ?? `Delete failed (${r.status}).`); return; }
      navigate(body.redirect ?? `/presets/manage/${encodeURIComponent(safeNs)}`);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'An unexpected error occurred.');
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
            <span>{safePreset}</span>
          </nav>
          <h1 className="sb-title reveal d2">{safePreset}</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            <Badge tone="gold">{safeRand}</Badge>
            {pageState.status === 'ready' && pageState.data.is_owner && <Badge tone="teal" dot>owner</Badge>}
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">
          {pageState.status === 'loading' && (
            <div className="panel"><div className="panel-body">
              <div className="skel" style={{ width: '100%', height: '12rem', borderRadius: 10 }} />
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
              <div className="panel onscroll">
                <div className="panel-head">
                  <h3>Preset contents</h3>
                  <a className="btn btn-ghost btn-sm" href={pageState.data.download_url}>Download</a>
                </div>
                <div className="panel-body">
                  <pre style={{
                    fontFamily: "'Space Mono', monospace",
                    fontSize: '.82rem',
                    color: 'var(--ink-soft)',
                    background: 'color-mix(in srgb, var(--ink) 4%, transparent)',
                    border: '1px solid color-mix(in srgb, var(--ink) 12%, transparent)',
                    borderRadius: '10px',
                    padding: '1rem',
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                  }}>{pageState.data.preset.content}</pre>
                </div>
              </div>

              {pageState.data.is_owner && (
                <div className="panel onscroll">
                  <div className="panel-head"><h3>Manage</h3></div>
                  <div className="panel-body">
                    {actionError && <div className="alert alert-error"><span className="alert-icon">⚠</span><p>{actionError}</p></div>}
                    <div className="field">
                      <label htmlFor="presetfile">Replace preset file</label>
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
                      <button className="btn btn-primary" onClick={() => void handleUpdate()} disabled={busy || !file}>
                        {busy ? (<><span className="spinner" aria-hidden="true" />Saving…</>) : (<>Update preset</>)}
                      </button>
                      <button className="btn btn-ghost" onClick={() => void handleDelete()} disabled={busy} style={{ color: 'var(--crimson)' }}>
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
