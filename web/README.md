# SahasrahBot web app

The website: a React 19 + TypeScript single-page app built with Vite, on the same
model as Wizzrobe's `web/` (Studio tokens, Radix headless parts, Material Symbols).
Its components were ported from Wizzrobe. Quart serves the build from `web/dist`.

```sh
npm ci
npm run gen:api     # web/openapi.json + src/api/schema.d.ts from the Python API (needs poetry)
npm run dev         # http://localhost:5173, proxies /api, /login etc. to localhost:5001
npm run typecheck
npm test            # Vitest
npm run build       # web/dist
```

`npm run dev` needs the backend running: `./scripts/dev.sh` from the repo root (fake
Discord, seeded MariaDB). Set `SAHASRAHBOT_API` to proxy somewhere else.

See "The web app" in the repo's `CLAUDE.md` for the rules (data only through
`/api/v1`, colours from `src/styles/tokens.css`, phone and desktop, light and dark).
