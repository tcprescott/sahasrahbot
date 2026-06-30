import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
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

function DisplayNameSection({ user, onChanged }: { user: MeData; onChanged: () => void }) {
  const [value, setValue] = useState(user.display_name ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const dirty = value.trim() !== (user.display_name ?? '');

  async function handleSave() {
    setError(null);
    setSuccess(false);
    setSaving(true);
    try {
      const r = await fetch('/api/me/display-name', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name: value }),
      });
      const body = (await r.json().catch(() => ({}))) as { success?: boolean; display_name?: string; error?: string };
      if (!r.ok || body.error) { setError(body.error ?? `Save failed (${r.status}).`); return; }
      setSuccess(true);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="profile-section">
      <p className="profile-section-title">Display Name</p>
      <p className="profile-section-desc">
        Shown across tournaments and leaderboards instead of your Discord name.
      </p>
      {error && (
        <div className="alert alert-error" role="alert">
          <span className="alert-icon">⚠</span>
          <p>{error}</p>
        </div>
      )}
      {success && (
        <div className="alert alert-success" role="status">
          <span className="alert-icon">✓</span>
          <p>Display name updated.</p>
        </div>
      )}
      <div className="field" style={{ display: 'flex', gap: '.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          className="control"
          value={value}
          onChange={(e) => { setValue(e.target.value); setSuccess(false); }}
          maxLength={32}
          placeholder="Not set"
          disabled={saving}
          aria-label="Display name"
        />
        <button
          className="btn btn-ghost btn-sm"
          onClick={() => void handleSave()}
          disabled={saving || !dirty || value.trim().length === 0}
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  );
}

function LinkedAccountsSection({ user, onChanged }: { user: MeData; onChanged: () => void }) {
  const [unlinking, setUnlinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { discord, racetime, twitch } = user.linked_accounts;

  async function handleUnlinkRacetime() {
    setError(null);
    setUnlinking(true);
    try {
      const r = await fetch('/api/me/racetime/unlink', { method: 'POST' });
      const body = (await r.json().catch(() => ({}))) as { success?: boolean; error?: string };
      if (!r.ok || body.error) { setError(body.error ?? `Unlink failed (${r.status}).`); return; }
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred.');
    } finally {
      setUnlinking(false);
    }
  }

  return (
    <div className="profile-section">
      <p className="profile-section-title">Linked Accounts</p>
      {error && (
        <div className="alert alert-error" role="alert">
          <span className="alert-icon">⚠</span>
          <p>{error}</p>
        </div>
      )}

      <div className="profile-linked-row">
        <div className="profile-linked-label">
          <Badge tone="teal" dot>Discord</Badge>
          <span className="profile-linked-value">{discord.username}</span>
        </div>
      </div>

      <div className="profile-linked-row">
        <div className="profile-linked-label">
          <Badge tone={racetime.linked ? 'teal' : 'default'} dot={racetime.linked}>RaceTime.gg</Badge>
          {racetime.linked ? (
            <a className="profile-linked-value" href={racetime.url ?? undefined} target="_blank" rel="noreferrer">
              {racetime.id}
            </a>
          ) : (
            <span className="profile-linked-value muted">Not linked</span>
          )}
        </div>
        {racetime.linked ? (
          <button className="btn btn-ghost btn-sm" onClick={() => void handleUnlinkRacetime()} disabled={unlinking}>
            {unlinking ? 'Unlinking…' : 'Unlink'}
          </button>
        ) : (
          <a className="btn btn-ghost btn-sm" href="/racetime/verification/initiate">
            Link account <span className="arr">→</span>
          </a>
        )}
      </div>

      <div className="profile-linked-row">
        <div className="profile-linked-label">
          <Badge tone={twitch.linked ? 'teal' : 'default'} dot={twitch.linked}>Twitch</Badge>
          {twitch.linked ? (
            <span className="profile-linked-value">{twitch.name}</span>
          ) : (
            <span className="profile-linked-value muted">Not linked</span>
          )}
        </div>
        <span className="profile-linked-hint">Synced automatically from tournament registration</span>
      </div>
    </div>
  );
}

function ProfileCard({ user, onChanged }: { user: MeData; onChanged: () => void }) {
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

        <DisplayNameSection user={user} onChanged={onChanged} />

        <LinkedAccountsSection user={user} onChanged={onChanged} />

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
  const queryClient = useQueryClient();
  const handleChanged = () => { void queryClient.invalidateQueries({ queryKey: ['me'] }); };

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

          {user && <ProfileCard user={user} onChanged={handleChanged} />}

        </div>
      </section>
    </>
  );
}
