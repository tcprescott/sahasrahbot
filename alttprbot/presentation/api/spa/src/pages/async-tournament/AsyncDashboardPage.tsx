import { useState, useCallback, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import '../../styles/dashboard.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Tournament {
  id: number;
  name: string;
  active: boolean;
  allowed_reattempts: number;
  runs_per_pool: number;
}

interface Player {
  id: number;
  display_name: string;
}

interface DashboardRace {
  id: number;
  status: string;
  review_status: string;
  created: string | null;
  start_time: string | null;
  end_time: string | null;
  elapsed_time: string | null;
  reattempted: boolean;
  reattempt_reason: string | null;
  runner_notes: string | null;
  runner_vod_url: string | null;
  score: number | null;
  score_formatted: string | null;
  reviewer_notes: string | null;
  pool_name: string;
  permalink_url: string;
  permalink_notes: string | null;
  permalink_live_race: boolean;
}

interface DashboardData {
  tournament: Tournament;
  player: Player;
  races: DashboardRace[];
  reattempted: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusLabel(status: string): string {
  switch (status) {
    case 'pending':      return 'PENDING';
    case 'in_progress':  return 'IN PROGRESS';
    case 'finished':     return 'FINISHED';
    case 'forfeit':      return 'FORFEIT';
    case 'disqualified': return 'DISQUALIFIED';
    default:             return status.toUpperCase();
  }
}

function statusCls(status: string): string {
  switch (status) {
    case 'pending':      return 'pending';
    case 'in_progress':  return 'in-progress';
    case 'finished':     return 'finished';
    case 'forfeit':      return 'forfeit';
    case 'disqualified': return 'disqualified';
    default:             return 'pending';
  }
}

function reviewLabel(status: string): string {
  switch (status) {
    case 'pending':  return 'PENDING';
    case 'approved': return 'APPROVED';
    case 'rejected': return 'REJECTED';
    default:         return status.toUpperCase();
  }
}

function reviewCls(status: string): string {
  switch (status) {
    case 'pending':  return 'pending';
    case 'approved': return 'approved';
    case 'rejected': return 'rejected';
    default:         return 'pending';
  }
}

function bestScore(races: DashboardRace[]): string {
  const finished = races.filter((r) => r.status === 'finished' && r.score !== null);
  if (finished.length === 0) return '—';
  const min = Math.min(...finished.map((r) => r.score as number));
  const match = finished.find((r) => r.score === min);
  return match?.score_formatted ?? '—';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SkeletonStats() {
  return (
    <div className="db-stats">
      {Array.from({ length: 4 }, (_, i) => (
        <div key={i} className="db-stat">
          <span className="skel" style={{ width: '6rem', height: '.65rem' }} />
          <span className="skel" style={{ width: '3rem', height: '1.4rem', marginTop: '.3rem' }} />
        </div>
      ))}
    </div>
  );
}

function SkeletonTable() {
  return (
    <div className="db-table-wrap">
      <table className="db-table">
        <thead>
          <tr>
            {['Pool', 'Status', 'Time', 'Score', 'Review', 'VoD', 'Actions'].map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: 4 }, (_, i) => (
            <tr key={i}>
              {Array.from({ length: 7 }, (__, j) => (
                <td key={j}>
                  <span className="skel" style={{ width: j === 6 ? '5rem' : j === 1 ? '4.5rem' : '3.5rem', height: '.8rem' }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuthPrompt({ tournamentId }: { tournamentId: string }) {
  const loginUrl = `/login/?next=/async/races/${encodeURIComponent(tournamentId)}`;
  return (
    <div className="panel">
      <div className="panel-body">
        <div className="db-auth-prompt">
          <div className="db-auth-icon">🔒</div>
          <p>Sign in with Discord to view your async tournament dashboard.</p>
          <a className="btn btn-primary" href={loginUrl}>
            Sign in with Discord <span className="arr">→</span>
          </a>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function AsyncDashboardPage() {
  const { id } = useParams<{ id: string }>();

  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [unauthenticated, setUnauthenticated] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    setUnauthenticated(false);

    try {
      const r = await fetch(`/async/races/${id}/dashboard.json`);
      if (r.status === 401) {
        setUnauthenticated(true);
        return;
      }
      if (r.status === 404) {
        setError('Tournament not found.');
        return;
      }
      if (!r.ok) {
        const body = (await r.json().catch(() => ({}))) as { error?: string };
        setError(body.error ?? `Failed to load dashboard (${r.status})`);
        return;
      }
      const body = (await r.json()) as DashboardData;
      setData(body);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void fetchDashboard();
  }, [fetchDashboard]);

  const tournament = data?.tournament;
  const races = data?.races ?? [];
  const reattempted = data?.reattempted ?? false;
  const tournamentName = tournament?.name ?? `Tournament #${id ?? ''}`;
  const isActive = tournament?.active ?? false;

  return (
    <>
      {/* ======== PAGE HEAD ======== */}
      <section className="pagehead">
        <div className="glow" />
        <div className="grid" />
        <div className="wrap">
          <nav className="crumb reveal d1" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span className="sep">/</span>
            <span>Async Tournament</span>
            <span className="sep">/</span>
            <span>Dashboard</span>
          </nav>

          <h1 className="db-title reveal d2">MY DASHBOARD</h1>

          <div className="db-meta reveal d3">
            {!loading && tournament && (
              <>
                <Badge tone="gold">{tournamentName}</Badge>
                <Badge tone={isActive ? 'teal' : 'default'} dot={isActive}>
                  {isActive ? 'LIVE' : 'CLOSED'}
                </Badge>
                <Badge>#{id}</Badge>
              </>
            )}
            {loading && (
              <span className="skel" style={{ width: '14rem', height: '1.4rem' }} />
            )}
          </div>
        </div>
      </section>

      {/* ======== BODY ======== */}
      <section className="block">
        <div className="wrap">

          {/* Loading state */}
          {loading && (
            <>
              <SkeletonStats />
              <SkeletonTable />
            </>
          )}

          {/* Unauthenticated */}
          {!loading && unauthenticated && (
            <AuthPrompt tournamentId={id ?? ''} />
          )}

          {/* Error */}
          {!loading && error && (
            <div className="panel">
              <div className="panel-body">
                <div className="db-state">
                  <div className="state-icon">⚠</div>
                  <p>{error}</p>
                  <button className="btn btn-ghost btn-sm" onClick={() => void fetchDashboard()}>
                    Retry
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Ready */}
          {!loading && !unauthenticated && !error && data && (
            <>
              {/* Summary stats bar */}
              <div className="db-stats onscroll">
                <div className="db-stat">
                  <span className="db-stat-label">Total Runs</span>
                  <span className="db-stat-value">{races.length}</span>
                </div>
                <div className="db-stat">
                  <span className="db-stat-label">Finished</span>
                  <span className="db-stat-value teal">
                    {races.filter((r) => r.status === 'finished').length}
                  </span>
                </div>
                <div className="db-stat">
                  <span className="db-stat-label">Best Score</span>
                  <span className="db-stat-value highlight">{bestScore(races)}</span>
                </div>
                <div className="db-stat">
                  <span className="db-stat-label">Reattempt Used</span>
                  <span className={`db-stat-value${reattempted ? ' crimson' : ''}`}>
                    {tournament && tournament.allowed_reattempts > 0
                      ? reattempted ? 'Yes' : 'No'
                      : 'N/A'}
                  </span>
                </div>
              </div>

              {/* Runs table */}
              {races.length === 0 ? (
                <div className="panel onscroll">
                  <div className="panel-body">
                    <div className="db-state">
                      <div className="state-icon">◇</div>
                      <p>No runs yet.</p>
                      <p>
                        Join the tournament Discord channel to receive a permalink
                        and start your run.
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="db-table-wrap onscroll">
                  <table className="db-table">
                    <thead>
                      <tr>
                        <th>Pool</th>
                        <th>Status</th>
                        <th>Time</th>
                        <th>Score</th>
                        <th>Review</th>
                        <th>VoD</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {races.map((race) => {
                        const canReattempt =
                          race.status === 'finished' &&
                          !race.reattempted &&
                          !reattempted &&
                          tournament != null &&
                          tournament.allowed_reattempts > 0;

                        return (
                          <tr key={race.id}>
                            {/* Pool */}
                            <td>{race.pool_name}</td>

                            {/* Status */}
                            <td>
                              <span className={`run-status ${statusCls(race.status)}`}>
                                {race.status === 'in_progress' && (
                                  <span
                                    style={{
                                      display: 'inline-block',
                                      width: '6px',
                                      height: '6px',
                                      borderRadius: '50%',
                                      background: 'var(--teal)',
                                      marginRight: '5px',
                                      verticalAlign: 'middle',
                                    }}
                                  />
                                )}
                                {statusLabel(race.status)}
                              </span>
                            </td>

                            {/* Time */}
                            <td>
                              {race.elapsed_time && race.elapsed_time !== 'N/A'
                                ? <span className="db-time">{race.elapsed_time}</span>
                                : <span className="db-none">—</span>
                              }
                            </td>

                            {/* Score */}
                            <td>
                              {race.score_formatted && race.score_formatted !== 'N/A'
                                ? <span className="db-score">{race.score_formatted}</span>
                                : <span className="db-none">—</span>
                              }
                            </td>

                            {/* Review */}
                            <td>
                              <span className={`run-review ${reviewCls(race.review_status)}`}>
                                {reviewLabel(race.review_status)}
                              </span>
                            </td>

                            {/* VoD */}
                            <td>
                              {race.runner_vod_url ? (
                                <a
                                  className="vod-link"
                                  href={race.runner_vod_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  aria-label="Watch VoD"
                                  title="Watch VoD"
                                >
                                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                                    <polygon points="5 3 19 12 5 21 5 3" />
                                  </svg>
                                </a>
                              ) : (
                                <span className="db-none">—</span>
                              )}
                            </td>

                            {/* Actions */}
                            <td>
                              <div className="db-actions">
                                <a
                                  className="db-action-link"
                                  href={race.permalink_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  title={race.permalink_notes ?? 'View permalink'}
                                >
                                  permalink →
                                </a>
                                {canReattempt && (
                                  <Link
                                    className="db-action-link reattempt"
                                    to={`/async/races/${id}/reattempt?race_id=${race.id}`}
                                  >
                                    reattempt →
                                  </Link>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {races.length > 0 && (
                <p className="db-footnote onscroll">
                  Score is relative to pool par · click permalink to view seed details.
                </p>
              )}
            </>
          )}

        </div>
      </section>
    </>
  );
}
