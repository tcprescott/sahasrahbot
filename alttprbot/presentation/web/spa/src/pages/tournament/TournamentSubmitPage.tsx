import { useState, useEffect, useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import '../../styles/submit.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SettingField {
  key: string;
  label: string;
  settings: Record<string, string>;
}

interface MeData {
  id: string;
  name: string;
  avatar_url: string;
}

interface SubmitResponse {
  success?: boolean;
  versus?: string;
  error?: string;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchMe(): Promise<MeData | null> {
  const r = await fetch('/api/me');
  if (r.status === 401) return null;
  if (!r.ok) throw new Error(`/api/me returned ${r.status}`);
  const body = (await r.json()) as { data: MeData };
  return body.data;
}

async function fetchFormConfig(event: string): Promise<SettingField[]> {
  const r = await fetch(`/api/tournament/form-config/${encodeURIComponent(event)}`);
  if (!r.ok) {
    const body = (await r.json().catch(() => ({}))) as { error?: string };
    throw new Error(body.error ?? `Failed to load form config (${r.status})`);
  }
  const body = (await r.json()) as { settings: SettingField[] };
  return body.settings;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function AuthPrompt({ event }: { event: string }) {
  const loginUrl = `/login/?next=/submit/${encodeURIComponent(event)}`;
  return (
    <div className="auth-prompt">
      <div className="auth-icon">🔒</div>
      <p>Sign in with Discord to submit match settings for this event.</p>
      <a className="btn btn-primary" href={loginUrl}>
        Sign in with Discord <span className="arr">→</span>
      </a>
    </div>
  );
}

interface SuccessPanelProps {
  versus: string;
  event: string;
  onReset: () => void;
}

function SuccessPanel({ versus, event, onReset }: SuccessPanelProps) {
  return (
    <div className="panel success-panel">
      <div className="panel-head">
        <h3>Submission Received</h3>
        <Badge tone="teal" dot>confirmed</Badge>
      </div>
      <div className="panel-body">
        <div className="alert alert-success">
          <span className="alert-icon">✓</span>
          <p>
            Settings submitted successfully. SahasrahBot will roll the seed and post it
            to the race room at start time. Check your DMs for details.
          </p>
        </div>
        {versus && <p className="versus">{versus}</p>}
        <p style={{ color: 'var(--ink-soft)', fontSize: '.9rem', marginBottom: '1.4rem' }}>
          Event:{' '}
          <span style={{ fontFamily: "'Space Mono', monospace", color: 'var(--gold)' }}>
            {event}
          </span>
        </p>
        <div className="form-actions">
          <button className="btn btn-ghost" onClick={onReset}>
            Submit another
          </button>
          <Link className="btn btn-ghost" to="/">
            Return home
          </Link>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main form component
// ---------------------------------------------------------------------------

interface SubmitFormProps {
  event: string;
  fields: SettingField[];
  userName: string;
}

function SubmitForm({ event, fields, userName }: SubmitFormProps) {
  const defaultFieldValues = (): Record<string, string> => {
    const init: Record<string, string> = {};
    for (const f of fields) {
      const firstKey = Object.keys(f.settings)[0];
      if (firstKey !== undefined) init[f.key] = firstKey;
    }
    return init;
  };

  const [episodeId, setEpisodeId] = useState('');
  const [fieldValues, setFieldValues] = useState<Record<string, string>>(defaultFieldValues);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ versus: string } | null>(null);

  function setField(key: string, value: string) {
    setFieldValues((prev) => ({ ...prev, [key]: value }));
  }

  function handleReset() {
    setEpisodeId('');
    setFieldValues(defaultFieldValues());
    setError(null);
    setSuccess(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!episodeId.trim()) {
      setError('SpeedGaming Episode ID is required.');
      return;
    }

    const parsed = parseInt(episodeId, 10);
    if (isNaN(parsed) || parsed <= 0) {
      setError('Episode ID must be a positive integer.');
      return;
    }

    setLoading(true);
    try {
      const body: Record<string, string | number> = {
        event,
        episodeid: parsed,
        ...fieldValues,
      };

      const r = await fetch('/api/tournament/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = (await r.json().catch(() => ({ error: `HTTP ${r.status}` }))) as SubmitResponse;

      if (!r.ok || data.error) {
        setError(data.error ?? `Submission failed (${r.status}).`);
        return;
      }

      setSuccess({ versus: data.versus ?? '' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return <SuccessPanel versus={success.versus} event={event} onReset={handleReset} />;
  }

  return (
    <div className="panel onscroll">
      <div className="panel-head">
        <h3>Game settings</h3>
        <span className="badge">SpeedGaming</span>
      </div>
      <div className="panel-body">

        {error && (
          <div className="alert alert-error" role="alert">
            <span className="alert-icon">⚠</span>
            <p>{error}</p>
          </div>
        )}

        <form onSubmit={(e) => void handleSubmit(e)} noValidate>

          {/* Episode ID */}
          <div className="field">
            <label htmlFor="episodeid">
              SpeedGaming Episode ID <span className="req">*</span>
            </label>
            <input
              id="episodeid"
              name="episodeid"
              type="number"
              className={`control${episodeId === '' && error !== null ? ' error' : ''}`}
              placeholder="e.g. 48217"
              value={episodeId}
              onChange={(e) => setEpisodeId(e.target.value)}
              required
              min={1}
              disabled={loading}
            />
            <p className="hint">
              Find the episode ID on the match's{' '}
              <a
                href="https://speedgaming.org"
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: 'var(--teal)' }}
              >
                SpeedGaming
              </a>{' '}
              page.
            </p>
          </div>

          {/* Dynamic setting fields from event config */}
          {fields.map((field) => (
            <div className="field" key={field.key}>
              <label htmlFor={`field-${field.key}`}>{field.label}</label>
              <select
                id={`field-${field.key}`}
                name={field.key}
                className="control"
                value={fieldValues[field.key] ?? ''}
                onChange={(e) => setField(field.key, e.target.value)}
                disabled={loading}
              >
                {Object.entries(field.settings).map(([optKey, optLabel]) => (
                  <option key={optKey} value={optKey}>
                    {optLabel}
                  </option>
                ))}
              </select>
            </div>
          ))}

          <div className="form-actions">
            <button
              className="btn btn-primary"
              type="submit"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  Submitting…
                </>
              ) : (
                <>
                  Submit match <span className="arr">→</span>
                </>
              )}
            </button>
            <button
              className="btn btn-ghost"
              type="button"
              onClick={handleReset}
              disabled={loading}
            >
              Reset
            </button>
          </div>

          <p style={{ marginTop: '1.2rem', fontSize: '.82rem', color: 'var(--ink-faint)' }}>
            Submitting as{' '}
            <span style={{ color: 'var(--ink-soft)', fontWeight: 600 }}>{userName}</span>
          </p>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Help sidebar
// ---------------------------------------------------------------------------

function HelpPanel({ hasFields }: { hasFields: boolean }) {
  const steps = [
    {
      n: '1',
      title: 'Find the episode',
      body: "The Episode ID is on the match's SpeedGaming page.",
    },
    ...(hasFields
      ? [{
          n: '2',
          title: 'Choose settings',
          body: 'Select the game settings that will be used for this race.',
        }]
      : []),
    {
      n: hasFields ? '3' : '2',
      title: 'Submit',
      body: 'SahasrahBot rolls the seed and posts it to the race room at start time.',
    },
    {
      n: hasFields ? '4' : '3',
      title: 'Check your DMs',
      body: 'SahasrahBot will send you a confirmation with the seed details.',
    },
  ];

  return (
    <div className="panel onscroll">
      <div className="panel-head">
        <h3>How it works</h3>
      </div>
      <div className="panel-body">
        <ol className="steps">
          {steps.map((step) => (
            <li key={step.n}>
              <span className="n">{step.n}</span>
              <span className="step-body">
                <b>{step.title}</b>
                <span>{step.body}</span>
              </span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page state machine
// ---------------------------------------------------------------------------

type PageState =
  | { status: 'loading' }
  | { status: 'unauthenticated' }
  | { status: 'error'; message: string }
  | { status: 'ready'; fields: SettingField[]; userName: string };

// ---------------------------------------------------------------------------
// Main page export
// ---------------------------------------------------------------------------

export function TournamentSubmitPage() {
  const { event } = useParams<{ event: string }>();
  const safeEvent = event ?? '';

  const [pageState, setPageState] = useState<PageState>({ status: 'loading' });

  const load = useCallback(async () => {
    setPageState({ status: 'loading' });
    try {
      const me = await fetchMe();
      if (!me) {
        setPageState({ status: 'unauthenticated' });
        return;
      }

      const fields = await fetchFormConfig(safeEvent);
      setPageState({ status: 'ready', fields, userName: me.name });
    } catch (err) {
      setPageState({
        status: 'error',
        message: err instanceof Error ? err.message : 'Failed to load form.',
      });
    }
  }, [safeEvent]);

  useEffect(() => {
    void load();
  }, [load]);

  const pageHead = (
    <section className="pagehead">
      <div className="glow" />
      <div className="grid" />
      <div className="wrap">
        <nav className="crumb reveal d1" aria-label="Breadcrumb">
          <Link to="/">Home</Link>
          <span className="sep">/</span>
          <span>Tournaments</span>
          <span className="sep">/</span>
          <span>Submit settings</span>
        </nav>
        <h1 className="sb-title reveal d2">Match Submission</h1>
        <div
          className="reveal d3"
          style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}
        >
          <Badge tone="gold">Event: {safeEvent || '—'}</Badge>
          {pageState.status === 'ready' && (
            <Badge tone="teal" dot>
              Signed in as {pageState.userName}
            </Badge>
          )}
        </div>
      </div>
    </section>
  );

  return (
    <>
      {pageHead}

      <section className="block">
        <div className="wrap">

          {/* Loading skeleton */}
          {pageState.status === 'loading' && (
            <div className="form-cols">
              <div className="panel">
                <div className="panel-head">
                  <div className="skel" style={{ width: 140, height: '1.15rem', borderRadius: 6 }} />
                </div>
                <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
                  {[80, 60, 70, 65, 50].map((pct, i) => (
                    <div
                      key={i}
                      className="skel"
                      style={{ width: `${pct}%`, height: '2.4rem', borderRadius: 10 }}
                    />
                  ))}
                </div>
              </div>
              <div className="panel">
                <div className="panel-head">
                  <div className="skel" style={{ width: 100, height: '1.15rem', borderRadius: 6 }} />
                </div>
                <div
                  className="panel-body"
                  style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
                >
                  {[90, 80, 85].map((pct, i) => (
                    <div
                      key={i}
                      className="skel"
                      style={{ width: `${pct}%`, height: '1rem', borderRadius: 6 }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Unauthenticated */}
          {pageState.status === 'unauthenticated' && (
            <div className="form-cols">
              <div className="panel">
                <AuthPrompt event={safeEvent} />
              </div>
              <HelpPanel hasFields={false} />
            </div>
          )}

          {/* Error */}
          {pageState.status === 'error' && (
            <div className="panel" style={{ maxWidth: 640 }}>
              <div className="panel-body">
                <div className="alert alert-error" role="alert">
                  <span className="alert-icon">⚠</span>
                  <p>{pageState.message}</p>
                </div>
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => void load()}
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* Ready */}
          {pageState.status === 'ready' && (
            <div className="form-cols">
              <SubmitForm
                event={safeEvent}
                fields={pageState.fields}
                userName={pageState.userName}
              />
              <HelpPanel hasFields={pageState.fields.length > 0} />
            </div>
          )}

        </div>
      </section>
    </>
  );
}
