import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="site">
      <div className="foot-wrap">
        <div>
          <div className="foot-brand">SahasrahBot</div>
          <p>A monolithic async Python companion for the ALTTP randomizer &amp; speedrun communities.</p>
        </div>
        <nav className="foot-links" aria-label="Footer">
          <Link to="/presets">Presets</Link>
          <Link to="/async/leaderboard/418">Leaderboard</Link>
          <Link to="/submit/alttprleague">Submit</Link>
          <a href="https://sahasrahbot.synack.live/" target="_blank" rel="noopener noreferrer">
            Docs
          </a>
          <a href="https://github.com/tcprescott/sahasrahbot" target="_blank" rel="noopener noreferrer">
            GitHub
          </a>
        </nav>
      </div>
      <div className="foot-meta">
        <span>© 2026 SahasrahBot · maintained by Synack</span>
        <span>// "Speedrun the Legend" · dark-first</span>
      </div>
    </footer>
  );
}
