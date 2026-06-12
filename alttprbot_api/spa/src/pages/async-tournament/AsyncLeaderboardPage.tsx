import { Link, useParams } from 'react-router-dom';
import { PagePlaceholder } from '../PagePlaceholder';

export function AsyncLeaderboardPage() {
  const { id } = useParams();
  return (
    <PagePlaceholder
      crumb={
        <>
          <Link to="/">Home</Link>
          <span className="sep">/</span>
          <span>Async Tournaments</span>
          <span className="sep">/</span>
          <span>Leaderboard #{id}</span>
        </>
      }
      title="Tournament Leaderboard"
      kicker="Standings"
      blurb="Ranked standings with par scores, estimates, per-pool splits and finish/forfeit tallies."
    />
  );
}
