import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardBody } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

interface PagePlaceholderProps {
  crumb: ReactNode;
  title: string;
  kicker: string;
  blurb: string;
}

/**
 * Foundation stub: renders the shared page-head band + a panel noting the page
 * is pending its API + build. Replaced by the real page in the page-build phase.
 */
export function PagePlaceholder({ crumb, title, kicker, blurb }: PagePlaceholderProps) {
  return (
    <>
      <section className="pagehead">
        <div className="glow" />
        <div className="grid" />
        <div className="wrap">
          <div className="crumb reveal d1">{crumb}</div>
          <h1
            className="reveal d2"
            style={{
              fontFamily: '"Cinzel Decorative", serif',
              fontWeight: 900,
              lineHeight: 1,
              fontSize: 'clamp(2.1rem, 6vw, 3.8rem)',
              margin: '.8rem 0 0',
              color: 'var(--ink)',
              textShadow: '0 0 50px var(--hero-glow-a)',
            }}
          >
            {title}
          </h1>
          <div className="reveal d3" style={{ marginTop: '1rem' }}>
            <Badge tone="gold">Foundation scaffold</Badge>
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap" style={{ maxWidth: 720 }}>
          <Card className="onscroll">
            <CardBody>
              <span className="sec-kicker">{kicker}</span>
              <p style={{ marginTop: '1rem', color: 'var(--ink-soft)', fontSize: '1.05rem' }}>{blurb}</p>
              <p style={{ marginTop: '1rem', color: 'var(--ink-faint)', fontSize: '.9rem' }}>
                The visual design for this page is locked (see the{' '}
                <a
                  href="https://github.com/tcprescott/sahasrahbot"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: 'var(--teal)' }}
                >
                  prototype
                </a>
                ); it gets wired to its JSON API in the page-build phase.
              </p>
              <p style={{ marginTop: '1.4rem' }}>
                <Link to="/" style={{ color: 'var(--gold)', fontWeight: 600 }}>
                  ← Back home
                </Link>
              </p>
            </CardBody>
          </Card>
        </div>
      </section>
    </>
  );
}
