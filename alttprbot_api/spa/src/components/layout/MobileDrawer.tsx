import { Link } from 'react-router-dom';
import { NAV_ITEMS } from './nav';

interface MobileDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function MobileDrawer({ open, onClose }: MobileDrawerProps) {
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
      </aside>
    </>
  );
}
