# Interactive Frontend Testing with Playwright

This project is wired so an AI assistant (or a developer) can **drive the SPA in a
real browser** — navigate, click, fill forms, read the accessibility tree, and take
screenshots — via the [Playwright MCP server](https://github.com/microsoft/playwright-mcp).

It has three moving parts:

| Piece | File | Purpose |
|-------|------|---------|
| Playwright MCP server | [`.mcp.json`](../../.mcp.json) | Gives Claude Code live browser tools (`browser_navigate`, `browser_click`, `browser_snapshot`, `browser_take_screenshot`, …). |
| Web-only backend runner | [`helpers/run_web_dev.py`](../../helpers/run_web_dev.py) | Serves just the Quart web + REST API (no Discord/RaceTime bots) so the SPA has a backend to talk to. |
| Dev-server proxy | [`spa/vite.config.ts`](../../alttprbot/presentation/web/spa/vite.config.ts) | Vite dev server proxies `/api`, `/presets`, `/async`, `/submit` to the backend (default `http://127.0.0.1:5001`). |

## The pre-installed browser

Claude Code web environments ship Chromium at **`/opt/pw-browsers/chromium`**
(`PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`). Everything here points at that binary
via `--executable-path`, so **no `playwright install` / browser download is needed** —
it is blocked in restricted-network sessions anyway.

`.mcp.json` launches the MCP server headless, isolated (no on-disk profile), with the
sandbox disabled (required when running as root in a container):

```jsonc
"--headless", "--isolated", "--no-sandbox",
"--executable-path", "/opt/pw-browsers/chromium"
```

> **Local dev override:** on a workstation there is no `/opt/pw-browsers/chromium`.
> Run `npx playwright install chromium` and remove the `--executable-path` line (or
> point it at your own Chromium) so Playwright uses its version-matched build.

## Two ways to serve the frontend

### 1. Full-stack (recommended for interactive testing)

Build the SPA once, then run the web-only backend — Quart serves the built SPA **and**
the API from a single origin on port 5001, so every route works (including client-side
routing and `/api/*`):

```bash
# one-time: install deps
poetry install
(cd alttprbot/presentation/web/spa && npm install)

# build the SPA -> alttprbot/presentation/web/spa/dist/
(cd alttprbot/presentation/web/spa && npm run build)

# serve web + API only (no Discord/RaceTime bots)
poetry run python helpers/run_web_dev.py            # http://127.0.0.1:5001
```

Then point the browser (via the MCP `browser_navigate` tool) at `http://127.0.0.1:5001/`.

`run_web_dev.py` is deliberately forgiving so the **frontend is always testable**:

- **No `.env`?** It injects import-safe placeholders (`DEBUG=true`, a throwaway
  `APP_SECRET_KEY`, `DISCORD_CLIENT_ID=0`). A real `.env` is always respected.
- **No database?** DB init is non-fatal — the SPA and static assets still serve;
  DB-backed endpoints return errors until a MySQL is reachable and migrated.
- **`racetime_bot` not installed?** The REST blueprints (which import it) are skipped
  with a warning; the SPA and all non-RaceTime pages still serve.

### 2. Frontend-only with hot reload (fast UI iteration)

For rapid UI work, run the Vite dev server (HMR). API calls are proxied to a backend if
one is running on 5001:

```bash
cd alttprbot/presentation/web/spa
npm run dev                                         # http://127.0.0.1:5173
# override the proxy target if your backend is elsewhere:
VITE_API_PROXY_TARGET=http://127.0.0.1:5001 npm run dev
```

Navigate the browser to `http://127.0.0.1:5173/`. The static UI (home, layout, theming,
client routing) is fully testable with no backend at all; data-backed pages need the
backend on 5001. Top-level auth-redirect routes (`/login/`, `/callback/`) are **not**
proxied by the dev server — use the full-stack mode (5001) to exercise those.

## What needs real credentials / infrastructure

Pure frontend rendering and client-side behavior need none of the below. Reaching
**live data** or **authenticated** flows does:

- **A MySQL database** for the DB-backed pages (presets, tournaments, async races).
  Configure `DB_*` in `.env` and run `poetry run aerich upgrade`.
- **Real Discord OAuth app credentials** (`DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET`)
  for the Sign-in-with-Discord flow and any logged-in page (`/me`). With the placeholder
  values, `/api/me` correctly returns `401 unauthenticated` and login redirects will not
  complete.
- **`racetime_bot`** (a GitHub-archive dependency) for the REST `/api/racetime` surface.
  Its download can be blocked (HTTP 403) by the agent proxy in some sessions; the runner
  degrades gracefully without it.

## Typical interactive session (what Claude does)

1. `npm run build` the SPA, start `helpers/run_web_dev.py`.
2. `browser_navigate` → `http://127.0.0.1:5001/`.
3. `browser_snapshot` to read the accessibility tree, `browser_click` / `browser_type`
   to interact, `browser_take_screenshot` to capture state (saved under
   `./.playwright-mcp/`, which is git-ignored).
4. Report findings / regressions.

## Smoke-test the setup without the MCP server

To confirm the browser + served frontend work end-to-end from a script:

```bash
poetry run python helpers/run_web_dev.py &          # serve on 5001
node -e "const {chromium}=require('playwright');(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--no-sandbox']});const p=await b.newPage();await p.goto('http://127.0.0.1:5001/');console.log(await p.title());await b.close();})()"
```

(`playwright` isn't a project dependency — install it ad hoc for a manual smoke test:
`npm i -D playwright` in a scratch dir.)
