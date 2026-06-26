import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Navbar } from './Navbar';
import { MobileDrawer } from './MobileDrawer';
import { Footer } from './Footer';

/** Reveals `.onscroll` elements as they enter the viewport; re-runs per route.
 *  Uses a MutationObserver so elements rendered after an async data fetch
 *  (e.g. React Query results) are also observed. */
function useScrollReveal() {
  const location = useLocation();
  useEffect(() => {
    if (!('IntersectionObserver' in window)) {
      document.querySelectorAll<HTMLElement>('.onscroll')
        .forEach((e) => e.classList.add('in'));
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('in');
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0 },
    );

    document.querySelectorAll<HTMLElement>('.onscroll').forEach((e) => io.observe(e));

    const mo = new MutationObserver((mutations) => {
      for (const mut of mutations) {
        for (const node of Array.from(mut.addedNodes)) {
          if (!(node instanceof HTMLElement)) continue;
          if (node.classList.contains('onscroll')) io.observe(node);
          node.querySelectorAll<HTMLElement>('.onscroll').forEach((e) => io.observe(e));
        }
      }
    });
    mo.observe(document.body, { childList: true, subtree: true });

    return () => {
      io.disconnect();
      mo.disconnect();
    };
  }, [location.pathname]);
}

export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  useScrollReveal();

  // close the drawer + jump to top on navigation
  useEffect(() => {
    setMenuOpen(false);
    window.scrollTo(0, 0);
  }, [location.pathname]);

  return (
    <>
      <Navbar onOpenMenu={() => setMenuOpen(true)} />
      <MobileDrawer open={menuOpen} onClose={() => setMenuOpen(false)} />
      <main>
        <Outlet />
      </main>
      <Footer />
    </>
  );
}
