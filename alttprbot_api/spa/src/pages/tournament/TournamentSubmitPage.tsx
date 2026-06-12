import { Link, useParams } from 'react-router-dom';
import { PagePlaceholder } from '../PagePlaceholder';

export function TournamentSubmitPage() {
  const { event } = useParams();
  return (
    <PagePlaceholder
      crumb={
        <>
          <Link to="/">Home</Link>
          <span className="sep">/</span>
          <span>{event}</span>
          <span className="sep">/</span>
          <span>Submit settings</span>
        </>
      }
      title="Match Submission"
      kicker="Tournament"
      blurb="Submit a match's episode and game settings; SahasrahBot rolls the seed and posts it to the race room."
    />
  );
}
