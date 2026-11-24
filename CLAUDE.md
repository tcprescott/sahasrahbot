# SahasrahBot - Claude Development Guide

SahasrahBot is a Discord and racetime.gg bot for the ALTTPR, SMZ3 and related randomizer
communities. It rolls seeds, runs tournament and daily races, and serves a small Quart web app. One process (`sahasrahbot.py`) starts everything on a
single asyncio loop. It uses Tortoise ORM on MySQL, with Aerich migrations.

This file is the always-loaded guide: the rules to follow on every task, and a map of
where things live. Read it before changing code.

## Standing facts (don't undo these)

- **Privileged intents are permanently off.** The Discord client uses
  `discord.Intents.default()`; requesting members, presences or message_content makes
  Discord refuse the login (close code 4014) and the bot never comes online. Look up
  members with `alttprbot/util/discord_members.py` (`get_member`, `get_member_named`),
  never the member cache, `guild.chunk()`, `guild.members` or `role.members`.
  [docs/privileged_intents.md](docs/privileged_intents.md) lists what can't work without
  them. A hook (`check_privileged_intents.py`) enforces this.
- **The audit bot was removed** (2026-11), along with other dead features (orphaned
  tournament classes, SG Live, `/cc2023`). Don't bring them back without asking.
- **KONOT race series (`!konot`) were removed** (2026-11) at the user's request; the
  `RacetimeKONOTGame` / `RaceTimeKONOTSegment` models and tables stay.
- **The async tournament feature was removed** (2026-11) at the user's request, but its
  `AsyncTournament*` models and tables stay, along with the rows the racetime.gg
  account-merge in `alttprbot_api/blueprints/racetime.py` rewrites. Don't drop them
  without asking.
- **`master` is the base branch.** Branch from `master`, open PRs to `master`. The
  branch `master-backup` holds an abandoned three-tier rewrite (`alttprbot/presentation/`
  and so on); that code is not on master, so ignore any docs that describe it.

## Layout

| Path | What it is |
|---|---|
| `sahasrahbot.py` | Entry point: `init_sentry()`, `Tortoise.init`, then starts the Discord bot, the racetime bots and the API on one loop |
| `config.py` | **Gitignored, holds production secrets.** Never print, edit or commit it |
| `config.example.py` | Every setting the code reads, with placeholders. Tests load it when `config.py` is absent |
| `alttprbot/models/` | Tortoise models (`models.py`, `schedule.py`), re-exported from `alttprbot.models` |
| `alttprbot/services/` | Service layer: one module per domain, called by cogs, routes and racetime handlers. Services may use models directly and must not import any `alttprbot_*` package. `guild_config.py` is the only code that touches the `config` table (per-guild settings, cached) |
| `alttprbot/integrations/` | One small HTTP client per external API (racetime.gg, ALTTPR Ladder, Door Randomizer multiworld server, holy images). Plain data in and out; no Discord, racetime-bot, web or model imports (a test enforces this). New outbound HTTP goes here, not in a cog or handler |
| `alttprbot/alttprgen/` | Seed generation, with no Discord, racetime or web imports: `generator.py` (preset classes per randomizer), `preset.py`, `randomizer/` (one API client per external randomizer, e.g. `alttpr.py`'s `ALTTPRClient`), `spoilers.py` |
| `alttprbot/tournament/` | Tournament race logic, one class per event, built on `core.py`. `alttprbot/tournaments.py` maps racetime category goals to them (`TOURNAMENT_DATA`); each class's `configuration()` is `event_settings.tournament_config("<event slug>")`, built from `tournaments.yaml`; Sheets result recording is `alttprbot/services/tournament_results.py` |
| `alttprbot/observability/` | Sentry: `sentry.py` (init, settings, `sentry_tags`), `metrics.py`, `instrument.py` (times every service/API-client/seed call), `runtime.py` (30s process and bot gauges), `watchdog.py` (blocked event loop). See "Sentry" below |
| `alttprbot/events/` | The event bridge: `types.py` (one frozen dataclass per event, listed in `ALL_EVENTS`), `bus.py` (`publish`, `subscribe`). Imports no front end |
| `alttprbot/util/` | Shared helpers: `discord_members.py`, `speedgaming.py`, `gsheet.py`, `triforce_text.py`, … |
| `alttprbot_discord/` | Main Discord bot: `bot.py` (client and extension list), `cogs/` (commands), `notifications.py` (event bridge subscribers), `util/` (`seed_embeds.py` builds every seed embed, checks) |
| `alttprbot_racetime/` | racetime.gg bots: `config.py` (category → handler map), `core.py`, `handlers/` (one per category) |
| `alttprbot_api/` | Quart app on 127.0.0.1:5001: `api.py` (Discord sign-in, errors, serves `web/dist`), `schemas.py` (API bodies), `blueprints/` (`app_api.py` is the `/api/v1` JSON API the web app uses; the rest are the racetime command API, preset downloads and public preset JSON, settingsgen, tournament games). No server-rendered pages |
| `web/` | **The website**: a React + TypeScript app (Vite), built like Wizzrobe's `web/`. See "The web app" below |
| `tournaments.yaml` | Per-event tournament and daily settings: Discord guild, channel and role ids, racetime goal, and the dailies' room-opened announcements. Read by `alttprbot/tournament/event_settings.py`, validated at startup. Put new event ids here, never in code |
| `presets/` | YAML presets per randomizer (`alttpr/`, `sm/`, `smz3/`, `alttprmystery/`, `ctjets/`). The file name is the preset name |
| `migrations/` | Aerich migrations (generated; don't hand-edit old ones) and `tortoise_config.py` |
| `docs/` | **The public user site** (GitHub Pages, Jekyll, sahasrahbot.synack.live). User-facing command and preset docs only; developer notes belong in this file |
| `devserver/` | Standalone web app for UI work and browser testing: fake Discord, racetime.gg and SpeedGaming, seeded local MariaDB. Started by `scripts/dev.sh`; see below |
| `docker-compose.dev.yml` | The dev server's MariaDB (port 3307). Dev only |
| `helpers/`, `dbtest.py`, `update_docs.py` | One-off maintenance scripts |
| `utils/` | Vendored submodules (door randomizer, enemizer). Not our code; never edit |
| `layer_allowlist.txt` | Baseline of allowed cross-layer imports; empty, and stays that way (see Layers below) |
| `testdata/` | Anonymized production-shaped fixtures, one JSON per feature, generated by `scripts/scrub_prod_dump.py`; `testdata.load()` inserts them. See `testdata/README.md` |
| `tests/` | pytest suite: import smoke tests, guardrail tests, and characterization unit tests per area (`test_<area>.py`); shared fixtures in `conftest.py` |
| `.claude/` | Claude Code hooks and guardrails; see [.claude/README.md](.claude/README.md) |

## Working on the code

### Setup

- Python **3.13** is what CI tests on; `pyproject.toml` allows 3.11 and up. The web app
  needs Node.js 22 (`cd web && npm ci`).
- `poetry install --no-root`, then
  `poetry run python -m pip install --only-binary=:all: -r requirements-test.txt` (pytest,
  pytest-asyncio and pytest-cov are not in the dev group yet). In a cloud session the
  SessionStart hook does both. The
  egress proxy refuses `racetime-bot`'s archive URL, which makes Poetry abort, so the
  hook then installs the locked versions with pip and `racetime-bot` from git.
- Running the bot for real needs a `config.py` with real tokens and a MySQL database.
  You almost never need that: verify changes with the tests instead.

### Checking your work

Run `./scripts/check.sh` before you commit. It runs what CI runs
(`.github/workflows/test.yml`):

1. `ruff check .` with `ruff.toml`: a small rule set (syntax errors, undefined names,
   broken comparisons), so every hit is a real bug.
2. `python3 scripts/guardrails.py --all`: replays the `.claude/scripts/` file checks, including the
   layer-boundary check against `layer_allowlist.txt`.
3. `poetry run python -m pytest -q tests`: imports every entry point and every cog
   `bot.py` loads, each in a fresh interpreter with `config.example.py`, plus the
   guardrail tests and the unit tests (about 35 seconds). Add `--cov` for a coverage
   report (`.coveragerc`).
4. When Node.js is installed, the web app: `gen:api`, typecheck, Vitest and a build.

The import smoke test catches typo'd imports, renamed symbols, circular imports and
missing config keys. The unit tests are **characterization tests**: they pin what the
code on master does today, so a refactor can be checked against them. Rules for them:

- Async tests need no decorator (`asyncio_mode = auto` in `pytest.ini`).
- `db` fixture: a fresh in-memory SQLite database with every model's table. MySQL-only
  SQL (`ON DUPLICATE KEY`, `TIMESTAMPADD`) can't run there; assert on the SQL instead.
- `fake_http` fixture: a real local HTTP server for code that opens its own aiohttp
  sessions. Point the code at it by monkeypatching the config value it builds URLs from
  (e.g. `config.SG_API_ENDPOINT`). aioresponses doesn't work with our aiohttp version.
- Never call Discord, racetime.gg, SpeedGaming, randomizer APIs, S3 or Google: replace
  the client (`ALTTPRClient.generate`, `rtgg_handler`, `discord_members.get_member`, …)
  with a mock. `config.DEBUG` is True in `config.example.py`; monkeypatch it where the
  code branches on it.
- Code that uses the live bots gets them from `alttprbot.services.bots` (`bots.discord()`,
  `bots.racetime_bot(category)`), which nothing registers in tests. Give it a fake with
  `monkeypatch.setattr(bots, "_discord_client", fake)` or
  `monkeypatch.setattr(bots, "_racetime_bots", {"alttpr": fake_bot})`.
- Cogs are tested by calling a command's body with fakes from `tests/discord_fakes.py`:
  `await call(cog.rom, cog, FakeInteraction())`, then `interaction.sent()` for what it
  replied. Buttons and selects: `await view.<item>.callback(interaction)`.
- Coverage has a floor (`fail_under` in `.coveragerc`), enforced by CI's `--cov` run.
  Raise it when coverage goes up; never lower it to get a PR through.
- `testdata` gives realistic data: `await testdata.load("ranked_choice")` (inside the `db`
  fixture) inserts fake users plus that feature's rows, ids from 1001. Regenerate the files
  with `scripts/scrub_prod_dump.py`; never hand-edit them, and never commit a raw dump.
- When today's behaviour looks wrong, still pin it, but name the test
  `test_known_issue_...` and say why in its docstring, or mark it
  `xfail(strict=True)`. When you fix the bug, change that test in the same PR.

When you fix a bug or add behaviour that can be tested without Discord or the network,
add a focused test under `tests/`.

SonarCloud (project `tcprescott_sahasrahbot`, org `tcprescott`) also analyses every PR.
In a cloud session with a `SONAR_TOKEN`, the SessionStart hook installs the `sonar` CLI
(`sonar list issues -p tcprescott_sahasrahbot --pull-request <N>`,
`sonar qg status -p tcprescott_sahasrahbot`). The project is public, so without a token
use the web API: `https://sonarcloud.io/api/issues/search?componentKeys=tcprescott_sahasrahbot&pullRequest=<N>&resolved=false`.

### The web app (`web/`)

The website is a single-page React app, modelled on Wizzrobe's new app (`tcprescott/wizzrobe`,
`web/` and `docs/style-guide.md`): React 19, TypeScript, Vite, react-router, Radix headless
parts styled with Wizzrobe's "Studio" tokens, Material Symbols icons. The accent is
SahasrahBot purple. `npm run build` puts it in `web/dist`, which Quart serves: files by
name, and `index.html` for every other page path. It must stay able to become an iOS and
Android app (Capacitor, as Wizzrobe plans), so no browser-only assumptions.

- **Data:** only through `/api/v1` (`alttprbot_api/blueprints/app_api.py`). Routes are
  thin: who's signed in, call a service in `alttprbot/services/`, return a model from
  `alttprbot_api/schemas.py`. Services raise `NotFoundError` / `PermissionDeniedError` /
  `InvalidInputError` (`alttprbot/exceptions.py`), which become 404/403/400 with
  `{"error": "..."}`, a sentence a person can read.
- **Types:** `npm run gen:api` writes `web/openapi.json` (`scripts/export_openapi.py`) and
  `web/src/api/schema.d.ts` from it. Both are gitignored; CI generates them, so a route
  change that breaks a screen fails the `pytest` CI job (which also checks `web/`). Call the API with
  `api.GET('/api/v1/…')` and `unwrap` (`web/src/api/client.ts`). Discord ids are strings.
- **Sign-in:** the Discord OAuth session cookie (`/login/?next=<path>`). Requests that change
  something need `X-Requested-With: SahasrahBot` (the client adds it), which is the CSRF
  guard. A native app will need token sign-in; that's planned as its own PR.
- **URLs:** pages keep the old server-rendered URLs (`/ranked_choice/<id>`,
  `/triforcetexts/<pool>`, `/submit/<event>`, `/presets/manage/…`), because Discord
  messages already sent link to them. Routes are in `web/src/App.tsx`.
- **Look:** colour from `web/src/styles/tokens.css` only, never a hex in a component. Use
  `web/src/components/` (`Button`, `Panel`, `PageHeader`, `Chip`, `Banner`, `EmptyState`,
  `Dialog`/`ConfirmDialog`, `RowMenu`/`ActionsMenu`) and `web/src/kit/DataTable.tsx` (a table on
  desktop, cards on a phone). One main button plus an Actions menu per page; one button
  plus a ⋮ per row; destructive actions confirm first. Check phone (390px) and desktop,
  light and dark. Icons: add the name to `web/src/components/icons.ts`, in order.
- **Checks:** `npm run typecheck`, `npm test` (Vitest, `src/**/*.test.ts`) and
  `npm run build`, all run by `check.sh` and CI. Node 22.
- **Production:** deploys with `git pull`, then `scripts/build_web.sh` (Node 22 only: `npm ci`
  and `vite build`, no Python or type generation), then a restart. `web/dist` is never committed.

### Running the web app standalone

`./scripts/dev.sh` runs the Quart web app on its own at http://localhost:5001, with no
Discord bot, no racetime bots and no real credentials. Use it to develop UI and to check
a web change in a real browser (Playwright, or the `run` skill).

- **Database:** a MariaDB 11 container from `docker-compose.dev.yml` on 127.0.0.1:3307
  (database and user `sahasrahbot_dev`/`sahasrahbot`; the script generates the password into
  the gitignored `.devdb-password` on first run). The schema is generated from the
  current models, and `devserver/fixtures.py` seeds it the first time.
  `./scripts/dev.sh --reset` drops every table and reseeds. `DEV_DB_URL=mysql://…` uses your
  own MariaDB/MySQL instead of Docker, and `./scripts/dev.sh db-destroy` deletes the
  container's data. In a cloud session the script starts the Docker
  daemon itself. SQLite is not an option: the queries and schema are MySQL-flavoured.
- **Config:** it always loads `config.example.py` with dev overrides
  (`devserver/bootstrap.py`), never a real `config.py`, and `DEBUG` is on.
- **Logging in:** the app's real quart-discord OAuth flow runs against a fake Discord
  served by the app itself under `/_fake/discord/`, whose authorize page is a "log in as"
  picker. Shortcut: `/_dev/login?user=<key>&next=/path` with a key from
  `devserver/fixtures.py` (`admin`, `mod`, `runner1`, `runner2`, `runner3`, `outsider`), or
  `/_dev/login?user=new&name=alice&roles=Admin,Voter` for a throwaway user.
- **Roles and guilds:** `discordbot` is replaced by `devserver/fake_discord.py`'s
  `FakeDiscordBot` before the app imports it. Member lookups behave like production without
  the members intent (empty cache, `fetch_member` works), so
  `alttprbot/util/discord_members.py` is exercised for real. Change anyone's roles at
  `/_dev/` or with `POST /_dev/members/<user_id>`.
- **Outbound effects:** messages the app sends to Discord channels or DMs are recorded,
  not sent; read them at `/_dev/#outbox` or `GET /_dev/api/outbox`. racetime.gg OAuth
  (`/_fake/racetime/`) and SpeedGaming's `/schedule` and `/episode` (`/_fake/speedgaming/`)
  are faked too.
- **Not faked yet:** seed generation (alttpr.com, OoTR, SMZ3 and the other randomizer
  APIs), so preset rolling fails; Google Sheets is a no-op
  stub. Add a fake under `devserver/fake_services.py` and point the setting at it in
  `devserver/bootstrap.py`.
- **testdata:** after its hand-made rows the dev server also loads `testdata/` (ids from
  1001, guilds "Prod-like Community N"). Log in as a testdata user with `/_dev/login?user=<discord id>`.
- **Adding fixtures:** new pages usually need rows. Add them to `seed_database()` in
  `devserver/fixtures.py` with fixed ids, and add the page to `LINKS` in
  `devserver/dev_tools.py`. `tests/test_devserver.py` checks the fakes without a database.

Production code doesn't know about the dev server: nothing in `alttprbot*/` imports
`devserver`, and the dev server doesn't change production modules on disk.

### Sentry

One Sentry project (`sahasrahbot` in the `sahasrahbot` org, region us) gets the server
and the browser, modelled on Wizzrobe's `docs/features/observability.md`. Everything is
off unless `config.SENTRY_URL` (the DSN) is set; every other `SENTRY_*` setting is
optional and documented in `config.example.py`. The SDK is **sentry-sdk 3.x**
(span-first: `sentry_sdk.start_span(name=..., attributes={"sentry.op": ...})`,
`data_collection` instead of `send_default_pii`), not the 2.x API Wizzrobe uses.

- **Errors:** unhandled web errors, plus any `logger.error`/`logger.exception`
  anywhere, so a failure someone relied on must log at ERROR (WARNING is a breadcrumb
  and a Sentry Log only). `SahasrahBotException` is dropped on purpose.
- **Logs:** INFO and up go to Sentry Logs (`SENTRY_LOGS_LEVEL`).
- **Traces:** web requests at 10% in production, scheduled jobs and Discord/racetime
  commands at 100% (each its own trace), browser page loads continuing into the server.
  Inside a trace: MySQL queries, outbound aiohttp calls and a span per service,
  API-client and seed-generator call. Profiles follow traced work.
- **Tags:** `surface` (`server`/`browser`), `job`, `event`/`event_subscriber`,
  `discord_command`/`discord_guild_id`/`discord_user_id`, `racetime_room`/
  `racetime_category`/`racetime_command`, `route`, `loop_blocked_in`. New work that runs
  outside a request wraps itself in `sentry_tags(...)`
  (`alttprbot/observability/sentry.py`).
- **Metrics** (Explore > Metrics). Call-style metrics come as `<x>.calls` (counter) and
  `<x>.duration` (ms) with an `outcome` (`ok`, `rejected`, `cancelled`, `error`):

  | Metric | Attributes | Source |
  |---|---|---|
  | `http.requests`, `http.request_duration` | `route` (URL rule), `method`, `status` | `alttprbot_api/telemetry.py` |
  | `service.*`, `integration.*`, `randomizer.*`, `seed.*` | `target` (`presets.get_preset`, `ALTTPRClient.generate`) | `alttprbot/observability/instrument.py`, automatic for every public async function/method in those packages |
  | `job.*` | `job` | `alttprbot/services/scheduler.py` |
  | `events.published`; `event.*` | `event`; `event`, `subscriber` | `alttprbot/events/bus.py` |
  | `discord.commands.*`, `discord.commands.delay` | `command`, `kind` | `alttprbot_discord/telemetry.py` (`SentryCommandTree`) |
  | `discord.interactions`, `discord.gateway` | `type`; `event` | `alttprbot_discord/cogs/telemetry.py` |
  | `racetime.commands.*`; `racetime.messages` | `category`, `command`; `category`, `type` | `alttprbot_racetime/telemetry.py` |
  | `process.cpu`/`memory_rss`/`asyncio_tasks`/`threads`, `loop.lag_p50`/`p95`/`max`, `loop.stalls`, `gc.pause`, `gc.seconds`, `db_pool.*`, `events.pending`, `discord.latency`/`guilds`/`ready`, `racetime.rooms` | (`generation`, `category`) | `alttprbot/observability/runtime.py`, every 30s |
  | `api.calls`, `api.duration` (browser) | `endpoint` (OpenAPI path), `method`, `status` | `web/src/telemetry.ts` |

- **Blocked loop:** a stall of 2s or more is an ERROR issue fingerprinted
  `event-loop-blocked` + the culprit line (`watchdog.py`); 0.5s+ is a WARNING log.
- **Browser:** `web/src/telemetry.ts`. Settings come inlined in index.html
  (`window.__SAHASRAHBOT_SENTRY__`) or from `GET /api/v1/telemetry`. Errors (own scripts
  only), a masked replay of the minute before an error, page-load and navigation traces
  named by route. Add new API calls through `api` and they are timed automatically.
- **Adding to it:** new services, integrations and randomizer clients are instrumented
  without changes. A new periodic job or event subscriber is too. For new long-running
  work elsewhere, use `metrics.timed("<prefix>", {...})` and `sentry_tags(...)`; keep
  metric attributes to small fixed sets (never an id).

### Conventions

- Everything is async on one event loop. Never block it: no `time.sleep`, no
  `requests`; use `aiohttp`, `asyncio.sleep`, and `aiofiles` for file I/O.
- **New settings go in `config.example.py`** with a placeholder and a comment, read as
  `config.NAME`. Tell the user which real value production needs. A hook
  (`check_config_keys.py`) rejects a `config.X` missing from the example.
- **Notifications go through the event bridge.** When domain or service code (tournaments,
  racetime handlers, web blueprints, scheduled jobs) needs to tell someone something
  happened, it publishes an event instead of calling Discord:
  `events.publish(events.RankedChoiceBallotCast(election_id=...))` with
  `from alttprbot import events`. `publish` is synchronous, never blocks and never raises.
  Define the event in `alttprbot/events/types.py` (frozen dataclass, `name = "object.verb"`,
  plain data only, add it to `ALL_EVENTS`) and handle it in
  `alttprbot_discord/notifications.py`, subscribed in `register()`, which `sahasrahbot.py`
  calls at startup. Delivery is best effort and in-process: keep a direct call where the
  caller needs the result (a reply to a command, a racetime chat message, a DM whose
  failure must change what happens next). The tournament engine
  (`alttprbot/tournament/`) publishes its audit and commentary posts and submitted
  settings (`send_audit_message`, `send_commentary_message`, `publish_settings_submitted`),
  with embeds as `embed.to_dict()`. Its seed DMs (`send_player_message`) and settings
  reminders stay direct: a failed seed DM is reported in the race room, and a failed
  reminder is retried on the next run.
- Raise `SahasrahBotException` (`alttprbot/exceptions.py`) for user-facing errors; Sentry
  drops them on purpose.
- Model changes: edit `alttprbot/models/`, then `poetry run aerich migrate --name <topic>`
  and commit the generated file. That needs a database, so if you can't run it, say so
  in the PR and leave the migration to the user. Never run `aerich downgrade`.
- New Discord commands go in a cog under `alttprbot_discord/cogs/`, registered in
  `load_extensions()` in `alttprbot_discord/bot.py`. Prefer slash commands
  (`app_commands`); prefix commands that read message text can't work without
  message_content.
- **Periodic jobs** run on the in-process scheduler (`alttprbot/services/scheduler.py`),
  registered in `alttprbot/services/scheduled_jobs.py`, never as `discord.ext.tasks`
  loops in a cog (a test enforces this). A job does the work and publishes an event;
  Discord output is a subscriber in `alttprbot_discord/notifications.py` (see the event bridge above).
  When the job needs Discord's answer, it calls a function registered in
  `alttprbot_discord/gateways.py`.
- New racetime categories: add a handler in `alttprbot_racetime/handlers/`, an entry in
  `alttprbot_racetime/config.py`, and its `RACETIME_CLIENT_ID_<SLUG>` /
  `RACETIME_CLIENT_SECRET_<SLUG>` to the loop in `config.example.py`.
- New presets: add a YAML file under `presets/<randomizer>/`, and update the public
  preset docs in `docs/` if users will look for it.
- Dependencies are managed with Poetry. Use `poetry add`, never bare `pip install`.
  Never add `py-cord`: it installs into the same `discord` package as discord.py.
- **Layers.** `alttprbot/` is core and must not import `alttprbot_discord`,
  `alttprbot_api` or `alttprbot_racetime`; those front ends may import
  core but not each other. `.claude/scripts/check_layers.py` enforces this (hook, CI and
  `check.sh`). `layer_allowlist.txt` is empty now; never add a line to it. When core needs
  a front end's live object, the front end registers it at startup instead: the bots via
  `alttprbot/services/bots.py`, other lookups via `alttprbot_discord/gateways.py`.
- **Data access lives in services.** The front ends never query a model themselves:
  `.claude/scripts/check_model_queries.py` rejects `models.X.filter(...)`, `.get_or_none`,
  `.create`, `.update_or_create` and the other query methods in `alttprbot_discord/`,
  `alttprbot_api/` and `alttprbot_racetime/`. Add a function to the domain's module in
  `alttprbot/services/` that takes plain values (ids, names, never a `discord.Interaction`
  or a request) and call it. Reading attributes of the models it returns is fine.
- Leave unrelated code alone. This codebase has lots of old commented-out tournaments
  and unused imports; don't tidy them in a PR about something else.

### Git and PRs

- Commit on a feature branch, PR to `master`, fill in
  `.github/pull_request_template.md`.
- Don't force-push, `git reset --hard`, or commit with `--no-verify`; a hook blocks them.
- Never commit `config.py`, `.env`, ROMs (`*.sfc`) or cookies under `data/`.
