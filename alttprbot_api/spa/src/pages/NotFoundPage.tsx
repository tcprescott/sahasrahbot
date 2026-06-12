import { Link } from 'react-router-dom';
import { PagePlaceholder } from './PagePlaceholder';

export function NotFoundPage() {
  return (
    <PagePlaceholder
      crumb={
        <>
          <Link to="/">Home</Link>
          <span className="sep">/</span>
          <span>404</span>
        </>
      }
      title="Lost in the Dark World"
      kicker="404 — Not found"
      blurb="That page doesn't exist (or hasn't been built yet). Use the master sword — or just head home."
    />
  );
}
