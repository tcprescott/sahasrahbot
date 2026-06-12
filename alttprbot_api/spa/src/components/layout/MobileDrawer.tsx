import { Link } from 'react-router-dom';
import { NAV_ITEMS } from './nav';
import { useMe } from '../../hooks/useMe';

interface MobileDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function MobileDrawer({ open, onClose }: MobileDrawerProps) {
  const { data: user, isLoading } = useMe();

  return (
    <>
      <div className={open ? 'scrim open' : 'scrim'} onClick={onClose} />
      <aside className={open ? 'drawer open' : 'drawer'}>
        <button className="drawer-close" aria-label="Close menu" onClick={onClose}>
          ×
        </button>
        {NAV_ITEMS.map((item) =>
          item.external ? (
            <a key={item.to} href={item.to} target="_blank" rel="noopener noreferrer" onClick={onClose}>
              {item.label}
            </a>
          ) : (
            <Link key={item.to} to={item.to} onClick={onClose}>
              {item.label}
            </Link>
          ),
        )}

        {!isLoading &&
          (user ? (
            <a href="/logout/" onClick={onClose}>
              Sign out
            </a>
          ) : (
            <a href="/login/" onClick={onClose}>
              Sign in
            </a>
          ))}
      </aside>
    </>
  );
}
