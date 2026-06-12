# SahasrahBot SPA

React frontend for SahasrahBot — the **"Speedrun the Legend"** redesign. Replaces the legacy
Chameleon/Jinja2 templates (clean-break). See
[`docs/design/web_frontend_spa_redesign.md`](../../docs/design/web_frontend_spa_redesign.md).

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

Quart will serve the built `dist/` via a catch-all route (backend phase — not wired yet).

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
