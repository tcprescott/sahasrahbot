import { useState, useCallback, useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Badge } from '../../components/ui/Badge';
import '../../styles/player.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PlayerTournament {
  id: number;
  name: string;
  active: boolean;
  runs_per_pool: number;
}

interface Player {
  id: number;
  display_name: string;
}

interface PlayerRace {
  id: number;
  status: string;
  review_status: string | null;
  created: string | null;
  start_time: string | null;
  end_time: string | null;
  elapsed_time: string | null;
  reattempted: boolean;
  score: number | null;
  score_formatted: string | null;
  pool_name: string;
  permalink_url: string | null;
  permalink_notes: string | null;
  permalink_live_race: boolean;
}

interface PlayerData {
  tournament: PlayerTournament;
  player: Player;
  races: PlayerRace[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusLabel(status: string): string {
  switch (status) {
    case 'in_progress': return 'IN PROGRESS';
    case 'finished':    return 'FINISHED';
    case 'forfeit':     return 'FORFEIT';
    case 'disqualified': return 'DQ';
    default:            return 'PENDING';
  }
}

function statusCls(status: string): string {
  switch (status) {
    case 'in_progress':  return 'pl-status progress';
    case 'finished':     return 'pl-status finished';
    case 'forfeit':      return 'pl-status forfeit';
    case 'disqualified': return 'pl-status dq';
    default:             return 'pl-status pending';
  }
}

function reviewLabel(review: string | null): string {
  switch (review) {
    case 'approved': return 'APPROVED';
    case 'rejected': return 'REJECTED';
    default:         return 'PENDING';
  }
}

function reviewCls(review: string | null): string {
  switch (review) {
    case 'approved': return 'pl-status pl-review approved';
    case 'rejected': return 'pl-status pl-review rejected';
    default:         return 'pl-status pl-review pending';
  }
}

/** Shortest elapsed_time string among finished races (lexicographically safe for HH:MM:SS). */
function bestTime(races: PlayerRace[]): string | null {
  const times = races
    .filter((r) => r.status === 'finished' && !r.reattempted && r.elapsed_time)
    .map((r) => r.elapsed_time as string);
  if (times.length === 0) return null;
  return times.reduce((a, b) => (a < b ? a : b));
}

/** Lowest (most negative = best) score among finished, non-reattempted races. */
function bestScore(races: PlayerRace[]): string | null {
  const scored = races.filter(
    (r) => r.status === 'finished' && !r.reattempted && r.score !== null,
  );
  if (scored.length === 0) return null;
  const best = scored.reduce((a, b) =>
    (a.score as number) < (b.score as number) ? a : b,
  );
  return best.score_formatted;
}

// ---------------------------------------------------------------------------
// Skeleton rows
// ---------------------------------------------------------------------------

function SkeletonRow() {
  return (
    <tr>
      {[55, 80, 60, 60, 70].map((w, i) => (
        <td key={i}>
          <div className="pl-skel" style={{ width: `${w}%`, height: '.8rem' }} />
        </td>
      ))}
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function AsyncPlayerPage() {
  const { tournamentId, userId } = useParams<{ tournamentId: string; userId: string }>();

  const [data, setData] = useState<PlayerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!tournamentId || !userId) return;
    setLoading(true);
    setForbidden(false);
    setError(null);
    try {
      const r = await fetch(`/async/player/${tournamentId}/${userId}/data.json`);
      if (r.status === 403) {
        setForbidden(true);
        return;
      }
      if (!r.ok) {
        const body = await r.json().catch(() => ({})) as { error?: string };
        setError(body.error ?? `Failed to load player data (${r.status})`);
        return;
      }
      const payload = await r.json() as PlayerData;
      setData(payload);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Network error');
    } finally {
      setLoading(false);
    }
  }, [tournamentId, userId]);

  useEffect(() => { void fetchData(); }, [fetchData]);

  // Derived values (safe to compute when data exists)
  const tournamentName = data?.tournament.name ?? `Tournament #${tournamentId ?? ''}`;
  const isActive = data?.tournament.active ?? false;
  const playerName = data?.player.display_name ?? `Player #${userId ?? ''}`;

  const races = data?.races ?? [];
  const totalRuns = races.length;
  const finishedRuns = races.filter((r) => r.status === 'finished' && !r.reattempted).length;
  const bt = data ? bestTime(races) : null;
  const bs = data ? bestScore(races) : null;

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
            <span>Player</span>
          </nav>

          <h1 className="pl-title reveal d2">
            {loading
              ? <span className="pl-skel" style={{ width: '14ch', height: '1em', verticalAlign: 'middle' }} />
              : 'PLAYER PROFILE'
            }
          </h1>

          <div className="pl-meta reveal d3">
            {!loading && (
              <>
                <Badge tone="gold">{playerName}</Badge>
                <Badge>{tournamentName}</Badge>
                <Badge tone={isActive ? 'teal' : 'default'} dot={isActive}>
                  {isActive ? 'LIVE' : 'CLOSED'}
                </Badge>
              </>
            )}
          </div>
        </div>
      </section>

      {/* ======== BODY ======== */}
      <section className="block">
        <div className="wrap">

          {/* ---- 403 locked state ---- */}
          {forbidden && !loading && (
            <div className="panel onscroll">
              <div className="pl-locked">
                <div className="lock-icon">🔒</div>
                <p>
                  This tournament is currently active. Results are not public yet.
                </p>
              </div>
            </div>
          )}

          {/* ---- generic error state ---- */}
          {error && !loading && !forbidden && (
            <div className="panel onscroll">
              <div className="pl-state">
                <div className="state-icon">⚠</div>
                <p>{error}</p>
                <button className="btn btn-ghost btn-sm" onClick={() => void fetchData()}>
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* ---- loading or ready ---- */}
          {!forbidden && !error && (
            <>
              {/* Stats summary */}
              <div className="pl-stats onscroll">
                {loading ? (
                  <>
                    {[0, 1, 2, 3].map((i) => (
                      <div className="pl-stat" key={i}>
                        <div className="pl-skel" style={{ width: '60%', height: '.65rem', marginBottom: '.4rem' }} />
                        <div className="pl-skel" style={{ width: '40%', height: '1.3rem' }} />
                      </div>
                    ))}
                  </>
                ) : (
                  <>
                    <div className="pl-stat">
                      <span className="pl-stat-label">Total Runs</span>
                      <span className="pl-stat-value">{totalRuns}</span>
                    </div>
                    <div className="pl-stat">
                      <span className="pl-stat-label">Finished</span>
                      <span className="pl-stat-value teal">{finishedRuns}</span>
                    </div>
                    <div className="pl-stat">
                      <span className="pl-stat-label">Best Time</span>
                      <span className="pl-stat-value gold" style={{ fontSize: '1rem' }}>
                        {bt ?? '—'}
                      </span>
                    </div>
                    <div className="pl-stat">
                      <span className="pl-stat-label">Best Score</span>
                      <span className="pl-stat-value" style={{ fontSize: '1rem' }}>
                        {bs ?? '—'}
                      </span>
                    </div>
                  </>
                )}
              </div>

              {/* Runs table */}
              <div className="pl-table-wrap onscroll">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Pool</th>
                      <th>Status</th>
                      <th>Time</th>
                      <th>Score</th>
                      <th>Review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Loading skeleton */}
                    {loading && Array.from({ length: 5 }, (_, i) => (
                      <SkeletonRow key={i} />
                    ))}

                    {/* Loaded rows */}
                    {!loading && races.map((race) => (
                      <tr key={race.id} className={race.reattempted ? 'reattempted' : undefined}>
                        <td>{race.pool_name}</td>
                        <td>
                          <span className={statusCls(race.status)}>
                            {statusLabel(race.status)}
                          </span>
                          {race.reattempted && (
                            <> <span className="pl-status pending" style={{ marginLeft: '.3rem' }}>REATTEMPTED</span></>
                          )}
                        </td>
                        <td>
                          {race.elapsed_time
                            ? (
                              race.permalink_url
                                ? (
                                  <a
                                    className="pl-time"
                                    href={race.permalink_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                  >
                                    {race.elapsed_time}
                                  </a>
                                )
                                : <span className="pl-time">{race.elapsed_time}</span>
                            )
                            : <span className="pl-time" style={{ color: 'var(--ink-faint)' }}>—</span>
                          }
                        </td>
                        <td>
                          <span className={`pl-score${race.score !== null && race.score <= 0 ? ' pos' : ''}`}>
                            {race.score_formatted ?? '—'}
                          </span>
                        </td>
                        <td>
                          <span className={reviewCls(race.review_status)}>
                            {reviewLabel(race.review_status)}
                          </span>
                        </td>
                      </tr>
                    ))}

                    {/* Empty state */}
                    {!loading && races.length === 0 && (
                      <tr>
                        <td colSpan={5}>
                          <div className="pl-state">
                            <div className="state-icon">◇</div>
                            <p>No runs recorded for this player yet.</p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}

        </div>
      </section>
    </>
  );
}
