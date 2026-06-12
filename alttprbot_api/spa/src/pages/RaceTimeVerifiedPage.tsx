import { Link, useSearchParams } from 'react-router-dom';
import { Badge } from '../components/ui/Badge';
import '../styles/submit.css';
import '../styles/profile.css';

// ---------------------------------------------------------------------------
// Main page export
// ---------------------------------------------------------------------------

export function RaceTimeVerifiedPage() {
  const [searchParams] = useSearchParams();
  const success = searchParams.get('success') === 'true';
  const name = searchParams.get('name') ?? '';

  const pageHead = (
    <section className="pagehead">
      <div className="glow" />
      <div className="grid" />
      <div className="wrap">
        <nav className="crumb reveal d1" aria-label="Breadcrumb">
          <Link to="/">Home</Link>
          <span className="sep">/</span>
          <Link to="/me">Profile</Link>
          <span className="sep">/</span>
          <span>RaceTime</span>
        </nav>
        <h1 className="profile-title reveal d2">RaceTime Verified</h1>
        <div
          className="reveal d3"
          style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}
        >
          {success && name && (
            <Badge tone="teal" dot>{name}</Badge>
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

          {success ? (
            <div className="panel" style={{ maxWidth: 560 }}>
              <div className="panel-head">
                <h3>Account Linked!</h3>
                <Badge tone="teal" dot>verified</Badge>
              </div>
              <div className="panel-body">

                <div className="alert alert-success" role="status">
                  <span className="alert-icon">✓</span>
                  <p>
                    Your RaceTime.gg account{' '}
                    {name && (
                      <strong style={{ color: 'var(--teal)' }}>{name}</strong>
                    )}{' '}
                    has been linked to your Discord account. You can now participate in bot-managed races.
                  </p>
                </div>

                {name && (
                  <div style={{ marginBottom: '1.4rem', display: 'flex', alignItems: 'center', gap: '.7rem' }}>
                    <span style={{ fontSize: '.85rem', color: 'var(--ink-faint)', textTransform: 'uppercase', letterSpacing: '.07em', fontWeight: 700 }}>
                      RaceTime account
                    </span>
                    <span
                      style={{
                        fontFamily: "'Space Mono', monospace",
                        fontSize: '.9rem',
                        color: 'var(--teal)',
                        background: 'color-mix(in srgb, var(--teal) 10%, transparent)',
                        border: '1px solid color-mix(in srgb, var(--teal) 35%, transparent)',
                        borderRadius: '8px',
                        padding: '.25rem .65rem',
                      }}
                    >
                      {name}
                    </span>
                  </div>
                )}

                <div className="form-actions">
                  <Link className="btn btn-ghost" to="/me">
                    Back to profile <span className="arr">→</span>
                  </Link>
                  <Link className="btn btn-ghost" to="/">
                    Return home
                  </Link>
                </div>

              </div>
            </div>
          ) : (
            <div className="panel" style={{ maxWidth: 560 }}>
              <div className="panel-head">
                <h3>RaceTime Verification</h3>
              </div>
              <div className="panel-body">

                <div className="alert" style={{ background: 'color-mix(in srgb, var(--teal) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--teal) 30%, transparent)', color: 'var(--ink-soft)' }} role="note">
                  <span className="alert-icon" style={{ color: 'var(--teal)' }}>ℹ</span>
                  <p>
                    Linking your RaceTime.gg account lets SahasrahBot manage races on your behalf,
                    including posting seeds and tracking results. You'll need to authorise the bot
                    via the RaceTime.gg OAuth flow.
                  </p>
                </div>

                <div className="form-actions">
                  <a className="btn btn-primary" href="/racetime/verification/initiate">
                    Start Verification <span className="arr">→</span>
                  </a>
                  <Link className="btn btn-ghost" to="/me">
                    Back to profile
                  </Link>
                </div>

              </div>
            </div>
          )}

        </div>
      </section>
    </>
  );
}
