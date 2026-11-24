---
name: run-web-app
description: >-
  Start SahasrahBot's web app standalone (fake Discord, racetime.gg and SpeedGaming,
  seeded MariaDB) and drive it in a browser as a chosen fake user. Use to run, screenshot
  or check any change to the React app in web/ or the /api/v1 routes in alttprbot_api/ in
  the real app, or to develop UI.
---

# Run the web app standalone

1. **Start it in the background:** `./scripts/dev.sh` (add `--reset` for a fresh,
   reseeded database). It starts MariaDB in Docker (and the Docker daemon itself in a
   cloud session), then serves http://localhost:5001. Wait for the log line
   `SahasrahBot dev server on http://localhost:5001`. The script builds `web/` first when
   `web/dist` is missing or older than its sources; Python changes need a restart. For
   live reload of the React app, also run `cd web && npm run dev` and open
   http://localhost:5173, which proxies the API and sign-in routes to :5001.
2. **Log in as someone:** open `http://localhost:5001/_dev/login?user=<key>&next=<path>`.
   Keys: `admin` (owner, Admin role, async tournament admin), `mod` (Async Mod role, so
   async `mod`), `runner1`, `runner2`, `runner3` (racers), `outsider` (in no server, no
   DB row). A throwaway user: `?user=new&name=alice&roles=Admin,Voter`. Through the UI,
   any login link goes to the fake Discord picker instead.
3. **Drive it with Playwright** (preinstalled in cloud sessions; `require('playwright')`).
   Use `localhost`, not `127.0.0.1`, so the session cookie matches the OAuth redirect.
   `/_dev/` lists every user, their roles (editable) and the main pages with seeded data.
4. **Check side effects:** Discord messages the app would send are in
   `GET /_dev/api/outbox`. API errors are JSON (`{"error": ...}`) with real status
   codes; a server error on a page redirects to `/error`, so read the dev server's log
   for tracebacks.
5. **Missing data?** Add rows to `seed_database()` in `devserver/fixtures.py` with fixed
   ids, restart with `--reset`, and add the page to `LINKS` in `devserver/dev_tools.py`.

Seed generation (randomizer APIs) is not faked yet, so pages that roll seeds fail.
Stop the database with `./scripts/dev.sh db-down`; `db-destroy` also deletes its data.
