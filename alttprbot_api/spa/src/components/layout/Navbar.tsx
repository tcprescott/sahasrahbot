import { NavLink, Link } from 'react-router-dom';
import { useTheme } from '../../theme/ThemeProvider';
import { NAV_ITEMS } from './nav';

interface NavbarProps {
  onOpenMenu: () => void;
}

export function Navbar({ onOpenMenu }: NavbarProps) {
  const { theme, toggle } = useTheme();
  const dark = theme === 'dark';

  return (
    <header className="topbar reveal d1">
      <Link className="brand" to="/" aria-label="SahasrahBot home">
        <img className="sigil" src="/sahasrahbot.png" alt="SahasrahBot" width={34} height={36} />
        <span>SahasrahBot</span>
      </Link>

      <nav className="nav" aria-label="Primary">
        {NAV_ITEMS.map((item) =>
          item.external ? (
            <a key={item.to} href={item.to} target="_blank" rel="noopener noreferrer">
              {item.label}
            </a>
          ) : (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : undefined)} end={item.to === '/'}>
              {item.label}
            </NavLink>
          ),
        )}
      </nav>

      <button className="toggle" onClick={toggle} aria-label="Toggle color theme">
        <span className="ico">{dark ? '☾' : '☀'}</span>
        <span>{dark ? 'DARK' : 'LIGHT'}</span>
      </button>

      <button className="burger" onClick={onOpenMenu} aria-label="Open menu">
        <span />
        <span />
        <span />
      </button>
    </header>
  );
}
