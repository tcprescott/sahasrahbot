import { useState, useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Badge } from '../../components/ui/Badge';
import '../../styles/leaderboard.css';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Tournament metadata returned by GET /async/api/tournaments/:id */
interface Tournament {
  id: number;
  name: string;
  active: boolean;
  runs_per_pool: number;
}

/** A single race within a leaderboard entry */
interface LeaderboardRace {
  id: number;
  start_time: string | null;
  end_time: string | null;
  score: number | null;
  permalink_id: number | null;
  elapsed_time: string | null;
  status: string;
}

/** A single entry in the leaderboard array */
interface LeaderboardEntry {
  player: {
    id: number;
    display_name: string;
    discord_user_id: string;
    twitch_name: string | null;
    rtgg_id: string | null;
  };
  score: number | null;
  rank: number;
  races: Array<LeaderboardRace | null>;
  counts: {
    finished: number;
    forfeited: number;
    unplayed: number;
  };
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchTournament(id: string): Promise<Tournament> {
  const r = await fetch(`/async/races/${id}/info`);
  if (!r.ok) throw new Error(`Failed to load tournament (${r.status})`);
  return r.json() as Promise<Tournament>;
}

async function fetchLeaderboard(id: string): Promise<LeaderboardEntry[]> {
  const r = await fetch(`/async/races/${id}/leaderboard.json`);
  if (!r.ok) throw new Error(`Failed to load leaderboard (${r.status})`);
  return r.json() as Promise<LeaderboardEntry[]>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Format a par score (seconds relative to pool par) as +MM:SS or —. */
function formatScore(score: number | null): { text: string; cls: string } {
  if (score === null || score === undefined) return { text: '—', cls: 'none' };
  const abs = Math.abs(score);
  const h = Math.floor(abs / 3600);
  const m = Math.floor((abs % 3600) / 60);
  const s = abs % 60;
  const sign = score >= 0 ? '+' : '-';
  const time = h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${m}:${String(s).padStart(2, '0')}`;
  return {
    text: `${sign}${time}`,
    cls: score <= 0 ? 'pos' : '',
  };
}

/** Determine podium CSS class for a rank. */
function podiumClass(rank: number): string {
  if (rank === 1) return 'podium-1';
  if (rank === 2) return 'podium-2';
  if (rank === 3) return 'podium-3';
  return '';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <tr>
      {Array.from({ length: cols }, (_, i) => (
        <td key={i}>
          <div className="lb-skel" style={{ width: i === 1 ? '80%' : '50%', height: '.85rem' }} />
        </td>
      ))}
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function AsyncLeaderboardPage() {
  const { id } = useParams<{ id: string }>();
  const [search, setSearch] = useState('');

  // Fetch tournament metadata (for the name, active status, etc.)
  const {
    data: tournament,
    isLoading: tournamentLoading,
  } = useQuery({
    queryKey: ['async-tournament', id],
    queryFn: () => fetchTournament(id!),
    staleTime: 60_000,
    enabled: !!id,
  });

  // Fetch the leaderboard entries
  const {
    data: leaderboard,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['async-leaderboard', id],
    queryFn: () => fetchLeaderboard(id!),
    staleTime: 30_000,
    enabled: !!id,
  });

  // Filter rows by player name search
  const visibleRows = useMemo<LeaderboardEntry[]>(() => {
    if (!leaderboard) return [];
    const q = search.toLowerCase().trim();
    if (!q) return leaderboard;
    return leaderboard.filter((e) =>
      e.player.display_name.toLowerCase().includes(q) ||
      (e.player.twitch_name?.toLowerCase().includes(q) ?? false),
    );
  }, [leaderboard, search]);

  // Derive how many race columns to show from the first entry
  const raceCount = leaderboard?.[0]?.races.length ?? 0;

  // Total column count: rank + player + score + races + fin + ff + unplayed
  const totalCols = 3 + raceCount + 3;

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
            <span>Async Tournaments</span>
            <span className="sep">/</span>
            <span>Leaderboard</span>
          </nav>

          <h1 className="lb-title reveal d2">
            {tournamentLoading
              ? <span className="lb-skel" style={{ display: 'inline-block', width: '18ch', height: '1em', verticalAlign: 'middle' }} />
              : tournamentName
            }
          </h1>

          <div className="lb-meta reveal d3">
            {!tournamentLoading && (
              <>
                <Badge tone={isActive ? 'teal' : 'default'} dot={isActive}>
                  {isActive ? 'Live' : 'Closed'}
                </Badge>
                <Badge>#{id}</Badge>
                {!isLoading && leaderboard && (
                  <Badge tone="gold">{leaderboard.length} runner{leaderboard.length !== 1 ? 's' : ''}</Badge>
                )}
                <Badge>Sorted by Par Score</Badge>
              </>
            )}
          </div>
        </div>
      </section>

      {/* ======== BODY ======== */}
      <section className="block">
        <div className="wrap">

          {/* Filter / sort toolbar */}
          <div className="lb-tools onscroll">
            <label className="lb-search">
              <svg className="lb-search-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
                <circle cx="11" cy="11" r="7" />
                <path d="m21 21-4.3-4.3" />
              </svg>
              <input
                className="lb-search-input"
                type="search"
                placeholder="Find a runner…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="Search by player name"
              />
            </label>
          </div>

          {/* Error state */}
          {isError && !isLoading && (
            <div className="panel">
              <div className="lb-state">
                <div className="state-icon">⚠</div>
                <p>{error instanceof Error ? error.message : 'Failed to load leaderboard.'}</p>
                <button className="btn btn-ghost btn-sm" onClick={() => void refetch()}>
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* Leaderboard table: loading skeleton + loaded + empty */}
          {!isError && (
            <div className="table-wrap onscroll">
              <table className="data">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Player</th>
                    <th>Score</th>
                    {/* Dynamic race columns: shown once data is loaded */}
                    {!isLoading && leaderboard && leaderboard[0]?.races.map((_, i) => (
                      <th key={i}>Run {i + 1}</th>
                    ))}
                    {/* Placeholder headers while loading */}
                    {isLoading && Array.from({ length: 3 }, (_, i) => (
                      <th key={`ph-${i}`}>
                        <div className="lb-skel" style={{ width: '3rem', height: '.7rem' }} />
                      </th>
                    ))}
                    <th>Fin</th>
                    <th>FF</th>
                    <th>—</th>
                  </tr>
                </thead>
                <tbody>
                  {/* Loading: 8 skeleton rows */}
                  {isLoading && Array.from({ length: 8 }, (_, i) => (
                    <SkeletonRow key={i} cols={totalCols > 9 ? totalCols : 9} />
                  ))}

                  {/* Loaded: real rows */}
                  {!isLoading && visibleRows.map((entry) => {
                    const { text: scoreText, cls: scoreCls } = formatScore(entry.score);
                    return (
                      <tr key={entry.player.id} className={podiumClass(entry.rank)}>
                        {/* Rank */}
                        <td>
                          {entry.rank <= 3
                            ? <span className="medal">{entry.rank}</span>
                            : <span className="rank">{entry.rank}</span>
                          }
                        </td>

                        {/* Player name */}
                        <td className="player">{entry.player.display_name}</td>

                        {/* Par score */}
                        <td>
                          <span className={`score-big${scoreCls ? ` ${scoreCls}` : ''}`}>
                            {scoreText}
                          </span>
                        </td>

                        {/* Individual race splits */}
                        {entry.races.map((race, i) => {
                          if (!race) {
                            return <td key={i}><span className="split none">—</span></td>;
                          }
                          if (race.status === 'forfeit') {
                            return <td key={i}><span className="split dnf">DNF</span></td>;
                          }
                          if (race.elapsed_time) {
                            return (
                              <td key={i}>
                                {race.permalink_id
                                  ? (
                                    <a
                                      className="split"
                                      href={`/async/permalink/${id}/${race.permalink_id}`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                    >
                                      {race.elapsed_time}
                                    </a>
                                  )
                                  : <span className="split">{race.elapsed_time}</span>
                                }
                              </td>
                            );
                          }
                          return <td key={i}><span className="split none">—</span></td>;
                        })}

                        {/* Tallies */}
                        <td>
                          <span className="tally">
                            <span className="t fin">{entry.counts.finished}</span>
                          </span>
                        </td>
                        <td>
                          <span className="tally">
                            <span className="t ff">{entry.counts.forfeited}</span>
                          </span>
                        </td>
                        <td>
                          <span className="tally">
                            <span className="t un">{entry.counts.unplayed}</span>
                          </span>
                        </td>
                      </tr>
                    );
                  })}

                  {/* Empty state: no results after search filter */}
                  {!isLoading && !isError && leaderboard && visibleRows.length === 0 && (
                    <tr>
                      <td colSpan={totalCols > 9 ? totalCols : 9}>
                        <div className="lb-state">
                          <div className="state-icon">◇</div>
                          <p>
                            {search
                              ? `No runners match "${search}".`
                              : 'No leaderboard entries yet.'}
                          </p>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Footnote */}
          {!isLoading && !isError && leaderboard && leaderboard.length > 0 && (
            <p className="lb-footnote onscroll">
              Score = cumulative par delta vs. pool estimate · DNF counts as a forfeit · click a split to view that permalink.
            </p>
          )}

        </div>
      </section>
    </>
  );
}
