# SahasrahBot SPA

React frontend for SahasrahBot — the **"Speedrun the Legend"** redesign. Replaces the legacy
Chameleon/Jinja2 templates (clean-break). See
[`docs/design/web_frontend_spa_redesign.md`](../../../../docs/design/web_frontend_spa_redesign.md).

## Stack
- **React 18** + **React Router v6** + **TanStack Query v5**
- **Vite** (build/dev) · **TypeScript** · **Tailwind CSS v3**

## Develop
This repo has no native Linux Node by default. With nvm:

```bash
nvm use 20            # or: nvm install --lts=iron
npm install
npm run dev           # http://127.0.0.1:5173
```

## Build
```bash
npm run build         # type-check + Vite build → dist/
npm run preview       # serve the production build locally
```

Quart serves the built `dist/` via the SPA catch-all route in
`alttprbot/presentation/api/api.py`; hashed assets land under `/spa-assets/`
(`assetsDir` in `vite.config.ts`).

> **Frontend assets are built, not vendored.** The legacy
> `static/theme-assets/` and `static/assets/` trees (a 42 MB Chameleon/jQuery
> bundle, including `jquery-1.12.3` with known XSS CVEs) were removed once the
> Jinja templates were retired. Run `npm install && npm run build` to produce
> the frontend; do not re-vendor third-party JS/CSS into the repo.

## Design system
- `src/styles/tokens.css` — design tokens (CSS variables, dark + light) + element base +
  shared component classes. Ported verbatim from the approved prototype
  (`docs/design/prototypes/assets/theme.css`).
- `src/styles/home.css` — home-page-specific hero/feature/editorial styles.
- Tailwind (`tailwind.config.js`) surfaces the tokens as color/font utilities; preflight is
  disabled because `tokens.css` ships its own reset.
- Theming is `[data-theme]` + CSS variables via `ThemeProvider` (persisted to `localStorage`),
  **not** Tailwind's `dark:` variant — both themes are first-class.

## Structure
```
src/
  main.tsx              # providers + RouterProvider
  router.tsx            # routes
  theme/ThemeProvider   # dark/light + persistence
  components/layout/     # AppShell, Navbar, MobileDrawer, Footer
  components/ui/         # Button, Card, Badge, Table, SplitTimer
  pages/                 # HomePage (built) + stubs (presets, async, submit, 404)
  styles/                # tokens.css, home.css, index.css (tailwind)
```
