import { Link, Outlet, useLocation } from 'react-router-dom'
import { NavTabs } from './NavTabs'
import { titleFor } from './tabs'
import { useCanRunElections } from './useCanRunElections'
import { UserMenu } from './UserMenu'
import './shell.css'

function Brand() {
  return (
    <Link to="/" className="brand">
      <img className="brand__mark" src="/sahasrahbot.png" alt="" />
      <span className="brand__name">SahasrahBot</span>
    </Link>
  )
}

/** Shell A, as in Wizzrobe: a left rail on desktop, bottom tabs on phone (below 768px). */
export function AppShell() {
  const { pathname } = useLocation()
  const elections = useCanRunElections()
  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <nav className="shell__rail" aria-label="Main">
        <Brand />
        <NavTabs variant="rail" elections={elections} />
      </nav>
      <div className="shell__main">
        <header className="topbar">
          <span className="topbar__title">
            <span className="topbar__page">{titleFor(pathname)}</span>
            <Brand />
          </span>
          <div className="topbar__actions">
            <UserMenu />
          </div>
        </header>
        <main id="main" className="shell__content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
      <nav className="shell__tabbar" aria-label="Main">
        <NavTabs variant="tabbar" elections={elections} />
      </nav>
    </div>
  )
}
