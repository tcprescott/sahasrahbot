import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useMe } from '../../hooks/useMe';

// ---------------------------------------------------------------------------
// Navbar auth control.
//
//  - loading      → render nothing (avoid layout flash)
//  - signed out   → "Sign in with Discord" button
//  - signed in    → avatar + name button that toggles a dropdown menu
// ---------------------------------------------------------------------------

export function UserMenu() {
  const { data: user, isLoading } = useMe();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();

  // Close on route change.
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  // Close on outside-click and Escape.
  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (isLoading) return null;

  if (!user) {
    return (
      <a className="btn btn-primary btn-sm usermenu-signin" href="/login/">
        Sign in with Discord
      </a>
    );
  }

  return (
    <div className="usermenu" ref={ref}>
      <button
        className="usermenu-trigger"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <img className="usermenu-avatar" src={user.avatar_url} alt="" width={28} height={28} />
        <span className="usermenu-name">{user.name}</span>
        <span className="usermenu-caret">▾</span>
      </button>

      {open && (
        <div className="usermenu-dropdown" role="menu">
          <Link className="usermenu-item" to="/me" role="menuitem">
            My Profile
          </Link>
          <a className="usermenu-item" href="/racetime/verification/initiate" role="menuitem">
            Verify RaceTime
          </a>
          <div className="usermenu-divider" />
          <a className="usermenu-item usermenu-danger" href="/logout/" role="menuitem">
            Sign out
          </a>
        </div>
      )}
    </div>
  );
}
