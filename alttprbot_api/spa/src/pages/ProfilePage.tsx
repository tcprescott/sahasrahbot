import { Link } from 'react-router-dom';
import { Badge } from '../components/ui/Badge';
import { useMe, type MeData } from '../hooks/useMe';
import '../styles/submit.css';
import '../styles/profile.css';

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div className="panel" style={{ maxWidth: 680 }}>
      <div className="panel-head">
        <div className="profile-skel" style={{ width: 120, height: '1.1rem', borderRadius: 6 }} />
      </div>
      <div className="panel-body">
        {/* identity row */}
        <div className="profile-identity">
          <div className="profile-avatar-skel profile-skel" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.5rem', flex: 1 }}>
            <div className="profile-skel" style={{ width: '55%', height: '1.3rem', borderRadius: 6 }} />
            <div className="profile-skel" style={{ width: '35%', height: '.85rem', borderRadius: 6 }} />
          </div>
        </div>
        {/* section placeholders */}
        {[90, 75, 60].map((w, i) => (
          <div key={i} className="profile-skel" style={{ width: `${w}%`, height: '1rem', borderRadius: 6, marginBottom: '.9rem' }} />
        ))}
      </div>
    </div>
  );
}

function UnauthenticatedPanel() {
  return (
    <div className="panel" style={{ maxWidth: 480 }}>
      <div className="profile-auth-prompt">
        <div className="auth-icon">🔒</div>
        <p>Sign in with Discord to view your profile and manage your account.</p>
        <a className="btn btn-primary" href="/login/">
          Sign in with Discord <span className="arr">→</span>
        </a>
      </div>
    </div>
  );
}

function ProfileCard({ user }: { user: MeData }) {
  return (
    <div className="panel" style={{ maxWidth: 680 }}>
      <div className="panel-head">
        <h3>Account</h3>
        <Badge tone="teal" dot>signed in</Badge>
      </div>
      <div className="panel-body">

        {/* Identity */}
        <div className="profile-identity">
          <img
            className="profile-avatar"
            src={user.avatar_url}
            alt={`${user.name}'s avatar`}
            width={80}
            height={80}
          />
          <div>
            <p className="profile-name">{user.name}</p>
            <p className="profile-id">{user.id}</p>
          </div>
        </div>

        {/* RaceTime Verification */}
        <div className="profile-section">
          <p className="profile-section-title">RaceTime Verification</p>
          <p className="profile-section-desc">
            Link your RaceTime.gg account to participate in bot-managed races.
          </p>
          <a className="btn btn-ghost btn-sm" href="/racetime/verification/initiate">
            Verify RaceTime Account <span className="arr">→</span>
          </a>
        </div>

        {/* Manage Presets */}
        <div className="profile-section">
          <p className="profile-section-title">Manage Presets</p>
          <p className="profile-section-desc">
            Create and manage your personal preset namespace.
          </p>
          <Link className="btn btn-ghost btn-sm" to="/presets">
            Go to Presets <span className="arr">→</span>
          </Link>
        </div>

        {/* Danger Zone */}
        <div className="profile-section danger">
          <p className="profile-section-title">Danger Zone</p>
          <p className="profile-section-desc">
            Permanently delete all data associated with your account, including preset namespaces and race records.
          </p>
          <a className="btn btn-ghost btn-sm" href="/purgeme" style={{ color: 'var(--crimson)', borderColor: 'color-mix(in srgb, var(--crimson) 40%, transparent)' }}>
            Purge my data
          </a>
        </div>

      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page export
// ---------------------------------------------------------------------------

export function ProfilePage() {
  const { data: user, isLoading, error } = useMe();

  const pageHead = (
    <section className="pagehead">
      <div className="glow" />
      <div className="grid" />
      <div className="wrap">
        <nav className="crumb reveal d1" aria-label="Breadcrumb">
          <Link to="/">Home</Link>
          <span className="sep">/</span>
          <span>Profile</span>
        </nav>
        <h1 className="profile-title reveal d2">My Profile</h1>
        <div
          className="reveal d3"
          style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}
        >
          {user && (
            <Badge tone="gold">{user.name}</Badge>
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

          {isLoading && <LoadingSkeleton />}

          {!isLoading && !error && !user && <UnauthenticatedPanel />}

          {error && (
            <div className="panel" style={{ maxWidth: 480 }}>
              <div className="panel-body">
                <div className="alert alert-error" role="alert">
                  <span className="alert-icon">⚠</span>
                  <p>{error instanceof Error ? error.message : 'Failed to load profile.'}</p>
                </div>
                <a className="btn btn-ghost btn-sm" href="/login/">
                  Sign in again
                </a>
              </div>
            </div>
          )}

          {user && <ProfileCard user={user} />}

        </div>
      </section>
    </>
  );
}
