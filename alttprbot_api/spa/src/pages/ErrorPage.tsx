import { Link, useSearchParams } from 'react-router-dom';
import { Badge } from '../components/ui/Badge';
import '../styles/submit.css';

// ---------------------------------------------------------------------------
// Generic error page. Server-side error handlers redirect here with the
// title/message in the query string (see api.py _error_response).
// ---------------------------------------------------------------------------

export function ErrorPage() {
  const [searchParams] = useSearchParams();
  const title = searchParams.get('title') ?? 'Something went wrong';
  const message =
    searchParams.get('message') ?? 'An unexpected error occurred. Please try again later.';

  return (
    <>
      <section className="pagehead">
        <div className="glow" />
        <div className="grid" />
        <div className="wrap">
          <nav className="crumb reveal d1" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span className="sep">/</span>
            <span>Error</span>
          </nav>
          <h1 className="sb-title reveal d2">{title}</h1>
          <div className="reveal d3" style={{ marginTop: '1rem', display: 'flex', gap: '.6rem', flexWrap: 'wrap' }}>
            <Badge tone="crimson" dot>error</Badge>
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">
          <div className="panel" style={{ maxWidth: 560 }}>
            <div className="panel-head">
              <h3>{title}</h3>
            </div>
            <div className="panel-body">
              <div className="alert alert-error" role="alert">
                <span className="alert-icon">⚠</span>
                <p>{message}</p>
              </div>
              <div className="form-actions">
                <Link className="btn btn-primary" to="/">
                  Return home <span className="arr">→</span>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
