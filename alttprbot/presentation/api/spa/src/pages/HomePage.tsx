import { ButtonLink } from '../components/ui/Button';
import { SplitTimer } from '../components/ui/SplitTimer';
import '../styles/home.css';

const DISCORD_INVITE =
  'https://discord.com/api/oauth2/authorize?client_id=572269659290861578&permissions=0&scope=bot%20applications.commands';

export function HomePage() {
  return (
    <>
      {/* ============ HERO ============ */}
      <section className="hero">
        <div className="hero-glow" />
        <div className="hero-grid" />

        <svg className="motif tri-1" viewBox="0 0 100 88" fill="currentColor" aria-hidden="true">
          <path d="M50 0 L62 21 L38 21 Z" />
          <path d="M26 44 L38 23 L50 44 Z" opacity=".8" />
          <path d="M50 44 L62 23 L74 44 Z" opacity=".8" />
          <path d="M2 88 L26 46 L50 88 Z" opacity=".55" />
          <path d="M50 88 L74 46 L98 88 Z" opacity=".55" />
        </svg>
        <svg className="motif tri-2" viewBox="0 0 100 88" fill="currentColor" aria-hidden="true">
          <path d="M50 0 L62 21 L38 21 Z" />
          <path d="M26 44 L38 23 L50 44 Z" opacity=".8" />
          <path d="M50 44 L62 23 L74 44 Z" opacity=".8" />
        </svg>
        <svg className="motif tri-3" viewBox="0 0 30 27" fill="currentColor" aria-hidden="true">
          <path d="M15 0 L19 7 L11 7 Z" />
          <path d="M2 22 L6 15 L10 22 Z" opacity=".7" />
          <path d="M20 22 L24 15 L28 22 Z" opacity=".7" />
        </svg>

        <div className="hero-inner">
          <span className="eyebrow reveal d1">
            <span className="dot" />
            Now serving the randomizer multiverse
          </span>

          <h1 className="headline reveal d2">
            <span className="b">Speedrun</span>
            <span className="b accent">the Legend.</span>
          </h1>

          <SplitTimer />

          <div className="cta-row reveal d4">
            <ButtonLink variant="primary" href={DISCORD_INVITE} target="_blank" rel="noopener noreferrer">
              Invite the Bot <span className="arr">→</span>
            </ButtonLink>
            <ButtonLink variant="ghost" href="https://sahasrahbot.synack.live/" target="_blank" rel="noopener noreferrer">
              Read the Docs <span className="arr">↗</span>
            </ButtonLink>
          </div>

          <div className="statline reveal d5">
            <div className="stat">
              <div className="n">
                12<span className="u">+</span>
              </div>
              <div className="l">Game categories</div>
            </div>
            <div className="stat">
              <div className="n">4</div>
              <div className="l">Concurrent subsystems</div>
            </div>
            <div className="stat">
              <div className="n">∞</div>
              <div className="l">Seeds rolled</div>
            </div>
            <div className="stat">
              <div className="n">1</div>
              <div className="l">Event loop</div>
            </div>
          </div>
        </div>
      </section>

      {/* ============ FEATURES ============ */}
      <section className="block" id="features">
        <div className="wrap">
          <div className="sec-head onscroll">
            <span className="sec-kicker">What it does</span>
            <h2 className="sec-title">From a single slash command to a full tournament night.</h2>
          </div>

          <div className="features">
            <article className="feat f1 wide onscroll">
              <div className="fnum">01 / SEEDS</div>
              <div className="ficon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="12 2 2 7 12 12 22 7 12 2" />
                  <polyline points="2 17 12 22 22 17" />
                  <polyline points="2 12 12 17 22 12" />
                </svg>
              </div>
              <h3>Seed Generation</h3>
              <p>
                Roll randomized seeds from YAML presets across alttpr.com and a dozen other providers — with a reliability
                contract of timeouts, retries, and normalized errors so a flaky upstream never ruins race night.
              </p>
            </article>

            <article className="feat f2 third onscroll">
              <div className="fnum">02 / RACETIME</div>
              <div className="ficon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="9" />
                  <polyline points="12 7 12 12 15 14" />
                </svg>
              </div>
              <h3>Race Rooms</h3>
              <p>Auto-opens RaceTime.gg rooms, DMs runners, and manages live races per game category.</p>
            </article>

            <article className="feat f3 third onscroll">
              <div className="fnum">03 / ASYNC</div>
              <div className="ficon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
                  <path d="M21 3v5h-5" />
                  <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
                  <path d="M3 21v-5h5" />
                </svg>
              </div>
              <h3>Async Tournaments</h3>
              <p>Self-serve queues, leaderboards, pools and review tooling for run-when-you-can brackets.</p>
            </article>

            <article className="feat f4 third onscroll">
              <div className="fnum">04 / DAILY</div>
              <div className="ficon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1" />
                </svg>
              </div>
              <h3>Daily Challenges</h3>
              <p>A fresh seed every day, posted to Discord with its own thread and hash — automatically.</p>
            </article>

            <article className="feat f1 third onscroll">
              <div className="fnum">05 / PRESETS</div>
              <div className="ficon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 4h16v4H4zM4 10h16v10H4z" />
                  <path d="M8 14h8" />
                </svg>
              </div>
              <h3>Shared Presets</h3>
              <p>Publish, browse and download community preset namespaces straight from the web.</p>
            </article>
          </div>
        </div>
      </section>

      {/* ============ WHY ============ */}
      <section className="block" id="why" style={{ background: 'var(--bg-0)', borderBlock: '1px solid var(--line)' }}>
        <div className="wrap">
          <div className="sec-head onscroll">
            <span className="sec-kicker">Why this exists</span>
            <h2 className="sec-title">A minimalist console for everything Discord can't do well.</h2>
          </div>
          <div className="why-grid">
            <div className="why-prose onscroll">
              <p>
                SahasrahBot lives in Discord — but some things, like editing presets, submitting tournament settings,
                casting ranked-choice votes, or verifying your RaceTime.gg account, just want a real web form. That's what
                this site is for.
              </p>
              <p>
                It's also an <strong>API surface</strong>: a clean set of endpoints other bots and websites can build on.
                No bloat, no dashboard theme you didn't ask for — just the operations that matter, wired straight into the
                live bot.
              </p>
            </div>
            <blockquote className="pullquote onscroll">
              <q>Maybe someday I'll build a full-featured website. For now, this will more than do.</q>
              <span className="by">— Synack, maintainer</span>
            </blockquote>
          </div>
        </div>
      </section>
    </>
  );
}
