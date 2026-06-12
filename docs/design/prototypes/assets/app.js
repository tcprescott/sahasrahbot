/* ============================================================
   SahasrahBot prototype — shared AppShell + interactions
   Injects the navbar, mobile drawer and footer, then wires the
   theme toggle and scroll-reveal. Each page sets <body data-page="...">.
   ============================================================ */
(function () {
  const NAV = [
    { id: 'home',      label: 'Home',     href: 'home.html' },
    { id: 'presets',   label: 'Presets',  href: 'presets.html' },
    { id: 'leaderboard', label: 'Leaderboard', href: 'leaderboard.html' },
    { id: 'submit',    label: 'Submit',   href: 'submit.html' },
    { id: 'github',    label: 'GitHub',   href: 'https://github.com/tcprescott/sahasrahbot', ext: true },
  ];
  const page = document.body.dataset.page || 'home';

  /* ---- navbar ---- */
  const navLinks = NAV.map(n => {
    const active = n.id === page ? ' class="active"' : '';
    const ext = n.ext ? ' target="_blank" rel="noopener"' : '';
    return `<a href="${n.href}"${active}${ext}>${n.label}</a>`;
  }).join('');

  const drawerLinks = NAV.map(n => {
    const ext = n.ext ? ' target="_blank" rel="noopener"' : '';
    return `<a href="${n.href}"${ext}>${n.label}</a>`;
  }).join('');

  const header = document.createElement('header');
  header.className = 'topbar reveal d1';
  header.innerHTML = `
    <a class="brand" href="home.html" aria-label="SahasrahBot home">
      <img class="sigil" src="sahasrahbot.png" alt="SahasrahBot" width="34" height="36">
      <span>SahasrahBot</span>
    </a>
    <nav class="nav" aria-label="Primary">${navLinks}</nav>
    <button class="toggle" id="themeToggle" aria-label="Toggle color theme">
      <span class="ico" id="themeIco">☾</span><span id="themeTxt">DARK</span>
    </button>
    <button class="burger" id="burger" aria-label="Open menu"><span></span><span></span><span></span></button>`;

  const scrim = document.createElement('div');
  scrim.className = 'scrim';
  const drawer = document.createElement('aside');
  drawer.className = 'drawer';
  drawer.innerHTML = `<button class="drawer-close" aria-label="Close menu">×</button>${drawerLinks}`;

  const mount = document.getElementById('appshell-top');
  if (mount) mount.replaceWith(header); else document.body.prepend(header);
  document.body.append(scrim, drawer);

  /* ---- footer ---- */
  const footMount = document.getElementById('appshell-foot');
  const footer = document.createElement('footer');
  footer.className = 'site';
  footer.innerHTML = `
    <div class="foot-wrap">
      <div>
        <div class="foot-brand">SahasrahBot</div>
        <p>A monolithic async Python companion for the ALTTP randomizer &amp; speedrun communities.</p>
      </div>
      <nav class="foot-links" aria-label="Footer">
        <a href="presets.html">Presets</a>
        <a href="leaderboard.html">Leaderboard</a>
        <a href="submit.html">Submit</a>
        <a href="https://sahasrahbot.synack.live/" target="_blank" rel="noopener">Docs</a>
        <a href="https://github.com/tcprescott/sahasrahbot" target="_blank" rel="noopener">GitHub</a>
      </nav>
    </div>
    <div class="foot-meta">
      <span>© 2026 SahasrahBot · maintained by Synack</span>
      <span>// prototype · "Speedrun the Legend" · dark-first</span>
    </div>`;
  if (footMount) footMount.replaceWith(footer); else document.body.append(footer);

  /* ---- theme toggle ---- */
  const root = document.documentElement;
  const btn = document.getElementById('themeToggle');
  const ico = document.getElementById('themeIco');
  const txt = document.getElementById('themeTxt');
  function applyTheme(t) {
    root.setAttribute('data-theme', t);
    const dark = t === 'dark';
    ico.textContent = dark ? '☾' : '☀';
    txt.textContent = dark ? 'DARK' : 'LIGHT';
    try { localStorage.setItem('sb-theme', t); } catch (e) {}
  }
  let saved = 'dark';
  try { saved = localStorage.getItem('sb-theme') || 'dark'; } catch (e) {}
  applyTheme(saved);
  btn.addEventListener('click', () => applyTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark'));

  /* ---- mobile drawer ---- */
  const burger = document.getElementById('burger');
  function setDrawer(open) { drawer.classList.toggle('open', open); scrim.classList.toggle('open', open); }
  burger.addEventListener('click', () => setDrawer(true));
  scrim.addEventListener('click', () => setDrawer(false));
  drawer.querySelector('.drawer-close').addEventListener('click', () => setDrawer(false));

  /* ---- scroll reveal ---- */
  const els = document.querySelectorAll('.onscroll');
  if (!('IntersectionObserver' in window)) { els.forEach(e => e.classList.add('in')); }
  else {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { threshold: 0.12 });
    els.forEach(e => io.observe(e));
  }
})();
