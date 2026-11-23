# SahasrahBot - Claude Development Guide

SahasrahBot is a Discord and racetime.gg bot for the ALTTPR, SMZ3 and related randomizer
communities. It rolls seeds, runs tournament and daily races, manages async tournaments,
and serves a small Quart web app. One process (`sahasrahbot.py`) starts everything on a
single asyncio loop. It uses Tortoise ORM on MySQL, with Aerich migrations.

This file is the always-loaded guide: the rules to follow on every task, and a map of
where things live. Read it before changing code.

## Standing facts (don't undo these)

- **Privileged intents are permanently off.** Both Discord clients use
  `discord.Intents.default()`; requesting members, presences or message_content makes
  Discord refuse the login (close code 4014) and the bot never comes online. Look up
  members with `alttprbot/util/discord_members.py` (`get_member`, `get_member_named`),
  never the member cache, `guild.chunk()`, `guild.members` or `role.members`.
  [docs/privileged_intents.md](docs/privileged_intents.md) lists what can't work without
  them. A hook (`check_privileged_intents.py`) enforces this.
- **The audit bot is disabled by default.** `alttprbot_audit/` only starts when
  `config.AUDIT_BOT_ENABLED = True`. Most of it needs intents it no longer has, so don't
  turn it on or build on it without asking.
- **The async tournament feature stays.** Its code spans
  `alttprbot_discord/cogs/asynctournament.py`, `alttprbot/util/asynctournament.py`,
  `alttprbot_api/blueprints/asynctournament.py` and the `AsyncTournament*` models. Don't
  remove or "clean up" any of it.
- **`master` is the base branch.** Branch from `master`, open PRs to `master`. The
  branch `master-backup` holds an abandoned three-tier rewrite (`alttprbot/presentation/`
  and so on); that code is not on master, so ignore any docs that describe it.

## Layout

| Path | What it is |
|---|---|
| `sahasrahbot.py` | Entry point: Sentry, `Tortoise.init`, then starts the Discord bot, the optional audit bot, the racetime bots and the API on one loop |
| `config.py` | **Gitignored, holds production secrets.** Never print, edit or commit it |
| `config.example.py` | Every setting the code reads, with placeholders. Tests load it when `config.py` is absent |
| `alttprbot/models/` | Tortoise models (`models.py`, `schedule.py`), re-exported from `alttprbot.models` |
| `alttprbot/database/` | Older data-access helpers, mostly raw SQL through `alttprbot/util/orm.py`. Prefer models for new code |
| `alttprbot/alttprgen/` | Seed generation: `generator.py` (preset classes per randomizer), `preset.py`, `randomizer/` (one module per external randomizer), `spoilers.py` |
| `alttprbot/tournament/` | Tournament race logic, one class per event, built on `core.py`. `alttprbot/tournaments.py` maps racetime category goals to them (`TOURNAMENT_DATA`) |
| `alttprbot/util/` | Shared helpers: `discord_members.py`, `speedgaming.py`, `asynctournament.py`, `gsheet.py`, `triforce_text.py`, … |
| `alttprbot_discord/` | Main Discord bot: `bot.py` (client and extension list), `cogs/` (commands), `util/` (per-randomizer embeds, guild config, checks) |
| `alttprbot_racetime/` | racetime.gg bots: `config.py` (category → handler map), `core.py`, `handlers/` (one per category) |
| `alttprbot_api/` | Quart web app on 127.0.0.1:5001: `api.py`, `auth.py` (Discord OAuth), `blueprints/`, `templates/`, `static/` |
| `alttprbot_audit/` | Second Discord bot for moderation/audit logs. Disabled by default (see above) |
| `presets/` | YAML presets per randomizer (`alttpr/`, `sm/`, `smz3/`, `alttprmystery/`, `ctjets/`). The file name is the preset name |
| `migrations/` | Aerich migrations (generated; don't hand-edit old ones) and `tortoise_config.py` |
| `docs/` | **The public user site** (GitHub Pages, Jekyll, sahasrahbot.synack.live). User-facing command and preset docs only; developer notes belong in this file |
| `devserver/` | Standalone web app for UI work and browser testing: fake Discord, racetime.gg and SpeedGaming, seeded local MariaDB. Started by `scripts/dev.sh`; see below |
| `docker-compose.dev.yml` | The dev server's MariaDB (port 3307). Dev only |
| `helpers/`, `dbtest.py`, `update_docs.py` | One-off maintenance scripts |
| `utils/` | Vendored submodules (door randomizer, enemizer). Not our code; never edit |
| `tests/` | pytest suite: import smoke tests, guardrail tests, and characterization unit tests per area (`test_<area>.py`); shared fixtures in `conftest.py` |
| `.claude/` | Claude Code hooks and guardrails; see [.claude/README.md](.claude/README.md) |

## Working on the code

### Setup

- Python **3.13** is what CI tests on; `pyproject.toml` allows 3.11 and up.
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
2. `python3 scripts/guardrails.py --all`: replays the `.claude/scripts/` file checks.
3. `poetry run python -m pytest -q tests`: imports every entry point and every cog
   `bot.py` loads, each in a fresh interpreter with `config.example.py`, plus the
   guardrail tests and the unit tests (about 35 seconds). Add `--cov` for a coverage
   report (`.coveragerc`).

The import smoke test catches typo'd imports, renamed symbols, circular imports and
missing config keys. The unit tests are **characterization tests**: they pin what the
code on master does today, so a refactor can be checked against them. Rules for them:

- Async tests need no decorator (`asyncio_mode = auto` in `pytest.ini`).
- `db` fixture: a fresh in-memory SQLite database with every model's table. `raw_sql`
  also routes `alttprbot/util/orm.py` (MySQL `%s` SQL) to it. MySQL-only SQL
  (`ON DUPLICATE KEY`, `TIMESTAMPADD`) can't run there; assert on the SQL instead.
- `fake_http` fixture: a real local HTTP server for code that opens its own aiohttp
  sessions. Point the code at it by monkeypatching the config value it builds URLs from
  (e.g. `config.SG_API_ENDPOINT`). aioresponses doesn't work with our aiohttp version.
- Never call Discord, racetime.gg, SpeedGaming, randomizer APIs, S3 or Google: replace
  the client (`ALTTPRDiscord.generate`, `rtgg_handler`, `discord_members.get_member`, …)
  with a mock. `config.DEBUG` is True in `config.example.py`; monkeypatch it where the
  code branches on it.
- Import `alttprbot_racetime.bot` before `alttprbot.tournament.*` or `alttprbot.tournaments`:
  importing the tournament code first is a circular import.
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
  APIs), so SG Live "generate" buttons and preset rolling fail; Google Sheets is a no-op
  stub. Add a fake under `devserver/fake_services.py` and point the setting at it in
  `devserver/bootstrap.py`.
- **Adding fixtures:** new pages usually need rows. Add them to `seed_database()` in
  `devserver/fixtures.py` with fixed ids, and add the page to `LINKS` in
  `devserver/dev_tools.py`. `tests/test_devserver.py` checks the fakes without a database.

Production code doesn't know about the dev server: nothing in `alttprbot*/` imports
`devserver`, and the dev server doesn't change production modules on disk.

### Conventions

- Everything is async on one event loop. Never block it: no `time.sleep`, no
  `requests`; use `aiohttp`, `asyncio.sleep`, and `aiofiles` for file I/O.
- **New settings go in `config.example.py`** with a placeholder and a comment, read as
  `config.NAME`. Tell the user which real value production needs. A hook
  (`check_config_keys.py`) rejects a `config.X` missing from the example.
- Raise `SahasrahBotException` (`alttprbot/exceptions.py`) for user-facing errors; Sentry
  drops them on purpose.
- Model changes: edit `alttprbot/models/`, then `poetry run aerich migrate --name <topic>`
  and commit the generated file. That needs a database, so if you can't run it, say so
  in the PR and leave the migration to the user. Never run `aerich downgrade`.
- New Discord commands go in a cog under `alttprbot_discord/cogs/`, registered in
  `load_extensions()` in `alttprbot_discord/bot.py`. Prefer slash commands
  (`app_commands`); prefix commands that read message text can't work without
  message_content.
- New racetime categories: add a handler in `alttprbot_racetime/handlers/`, an entry in
  `alttprbot_racetime/config.py`, and its `RACETIME_CLIENT_ID_<SLUG>` /
  `RACETIME_CLIENT_SECRET_<SLUG>` to the loop in `config.example.py`.
- New presets: add a YAML file under `presets/<randomizer>/`, and update the public
  preset docs in `docs/` if users will look for it.
- Dependencies are managed with Poetry. Use `poetry add`, never bare `pip install`.
  Never add `py-cord`: it installs into the same `discord` package as discord.py.
- Leave unrelated code alone. This codebase has lots of old commented-out tournaments
  and unused imports; don't tidy them in a PR about something else.

### Git and PRs

- Commit on a feature branch, PR to `master`, fill in
  `.github/pull_request_template.md`.
- Don't force-push, `git reset --hard`, or commit with `--no-verify`; a hook blocks them.
- Never commit `config.py`, `.env`, ROMs (`*.sfc`) or cookies under `data/`.
