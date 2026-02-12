# SahasrahBot: RaceTime.gg Integration & Web API

> **Generated:** 2026-02-11
> **Scope:** `alttprbot_racetime/` (RaceTime.gg bot) and `alttprbot_api/` (Web API)

---

## Domain 1: RaceTime.gg Integration

### 1. Overview

SahasrahBot integrates with [RaceTime.gg](https://racetime.gg) — a racing platform for speedrunners — using the `racetime_bot` Python library (a first-party SDK for building RaceTime bots). The bot joins race rooms across **14 different game categories**, automatically generating randomizer seeds, managing spoiler races, running tournament logistics, and providing chat commands to racers.

The bot authenticates via OAuth2 client credentials (one client ID/secret pair per category) and maintains persistent WebSocket connections to race rooms. It tracks unlisted rooms in the database (`RTGGUnlistedRooms` model) so it can rejoin them after restarts.

### 2. Bot Architecture

**Startup Flow** (`alttprbot_racetime/bot.py`):

1. `config.py` defines a `RACETIME_CATEGORIES` dict mapping category slugs to `RacetimeBotConfig` dataclasses. Each config holds: `category_slug`, `handler_class`, and `bot_class`.
2. Client credentials are resolved dynamically via `config.RACETIME_CLIENT_ID_{SLUG}` / `config.RACETIME_CLIENT_SECRET_{SLUG}`.
3. At module load time, a `SahasrahBotRaceTimeBot` instance is created for each category and stored in `racetime_bots`.
4. `start_racetime(loop)` schedules `bot.start()` as async tasks on the event loop.

**`SahasrahBotRaceTimeBot`** (`alttprbot_racetime/core.py`) extends `racetime_bot.Bot`:
- Configures host/port/SSL from global config.
- Overrides `get_handler_class()` to return the category-specific handler.
- Overrides `get_handler_kwargs()` to inject `conn`, `logger`, `state`, and `command_prefix`.
- On `start()`: authorizes with RaceTime API, schedules token reauthorization, starts polling for new races, and **rejoins any persisted unlisted rooms** from the database.

**Categories Registered** (production):

| Slug | Handler | Game |
|------|---------|------|
| `alttpr` | `handlers.alttpr` | A Link to the Past Randomizer |
| `contra` | `handlers.contra` | Contra |
| `ct-jets` | `handlers.ctjets` | Chrono Trigger Jets of Time |
| `ff1r` | `handlers.ff1r` | Final Fantasy 1 Randomizer |
| `sgl` | `handlers.sgl` | SpeedGaming Live (minimal) |
| `smb3r` | `handlers.smb3r` | Super Mario Bros 3 Randomizer |
| `smr` | `handlers.smr` | Super Metroid Randomizer |
| `smw-hacks` | `handlers.smwhacks` | SMW Hacks |
| `smz3` | `handlers.smz3` | SM + ALTTP Combo Randomizer |
| `twwr` | `handlers.twwr` | Wind Waker Randomizer |
| `z1r` | `handlers.z1r` | Legend of Zelda Randomizer |
| `z2r` | `handlers.z2r` | Zelda 2 Randomizer |

*Note: `sm` (Super Metroid standalone Total/VARIA) is commented out. In debug mode, only a `test` category is registered.*

### 3. Core Handler (`SahasrahBotCoreHandler`)

All handlers extend `SahasrahBotCoreHandler` (`handlers/core.py`), which itself extends `racetime_bot.RaceHandler`.

**State Management:**
- `seed_rolled` flag prevents double-rolling.
- `state['locked']` flag restricts seed rolling to monitors only.
- Tracks `status`, `unlisted`, `tournament`, `konot`, `spoiler_race`.

**Lifecycle Hooks:**
- `begin()` — Sends intro message, sets up tournament/KONOT/spoiler race associations.
- `race_data()` — Processes every race state update. Handles tournament entrant auto-accept, fires `status_*` methods on status changes, tracks unlisted room state in DB.
- `end()` — Logs departure from room.

**Status Event Handlers:**
- `status_in_progress` — Sends spoiler log (if spoiler race), triggers tournament `on_race_start()`.
- `status_pending` — Triggers tournament `on_race_pending()`.
- `status_finished` — If KONOT series, creates next room.

**Shared Commands:**

| Command | Description |
|---------|-------------|
| `!cancel` | Resets bot state so a new seed can be rolled |
| `!tournamentrace` | Processes a tournament race (delegates to tournament handler) |
| `!konot` | Starts a King of the North Tournament elimination series |
| `!lock` | (Monitor only) Locks seed rolling to monitors |
| `!unlock` | (Monitor only) Unlocks seed rolling |
| `!promote` | Self-promotes a tournament gatekeep user to monitor |
| `!override` | Overrides streaming requirements for whitelisted users |

**Spoiler Race Support:**
- `schedule_spoiler_race()` / `send_spoiler_log()` / `countdown_timer()` — Creates a timed spoiler race where the log URL is revealed at race start, followed by a study-time countdown with periodic reminders.

**Tournament Integration:**
- On room resume, checks `TournamentResults` DB for a matching race name.
- Auto-accepts entrants who are known tournament players or gatekeepers.

### 4. Game-Specific Handlers

#### `alttpr` — A Link to the Past Randomizer

The richest handler. Commands:

| Command | Description |
|---------|-------------|
| `!newrace --preset=X [--quickswap] [--spoiler_race] [--countdown=N] [--branch=X]` | Primary command. Generates preset or spoiler race with full option support. Uses `msg_actions` survey UI. |
| `!race <preset> [branch]` | (Deprecated) Generate a preset race |
| `!noqsrace <preset>` | (Deprecated) Race without quickswap |
| `!spoiler <preset> [studytime]` | (Deprecated) Spoiler race with countdown |
| `!tournamentspoiler <preset>` | Spoiler race on tournament branch |
| `!progression <preset>` | Progression spoiler race (log sent with 0s study time) |
| `!mystery [weightset]` | Generates a mystery randomizer game |
| `!help` | Shows available commands |
| `!cancel` | (Monitor only) Resets state and deletes spoiler race |

Intro message uses RaceTime's `msg_actions` API to present a **survey-style UI** for rolling games.

#### `smz3` — SM + ALTTP Combo Randomizer

| Command | Description |
|---------|-------------|
| `!race <preset>` / `!preset <preset>` | Generates an SMZ3 preset game |
| `!multiworld <preset> [seed]` | Team-based multiworld seeds (requires team race with equal teams) |
| `!spoiler <preset> [studytime]` | SMZ3 spoiler race (default 25min study) |

#### `smr` — Super Metroid Randomizer

The most complex handler after ALTTPR, supporting multiple randomizer backends:

| Command | Description |
|---------|-------------|
| `!total <preset>` | SM Total Randomizer preset |
| `!varia <settings> <skills>` | SM VARIA Randomizer with settings + skills presets |
| `!dash [--spoiler] <preset>` | SM Dash Randomizer |
| `!choozorace <7 args>` | Choozo Randomizer with full custom params |
| `!multiworld <preset> [seed]` | SM Multiworld (team race) |
| `!smleagueplayoff <preset> <arg1> <arg2>` | SM League playoff seeds |

#### `z1r` — Legend of Zelda Randomizer

Large `PRESETS` dictionary mapping preset names to flag strings. Commands: `!race <preset>`, `!flags <flagstring>`, named shortcuts (`!power`, `!courage`, `!wisdom`, `!ttp3`, `!sglonline`, `!sglirl`).

#### `z2r` — Zelda 2 Randomizer

Commands: `!flags <flags>`, `!mrb`, and named presets (`!maxrando`, `!groups1-4`, `!brackets`, `!nit`, `!sgl`, `!sgl4`).

#### Other Handlers

| Handler | Game | Commands |
|---------|------|----------|
| `ff1r` | Final Fantasy Randomizer | `!ff1url <url>` |
| `smb3r` | Super Mario Bros 3 Randomizer | `!flags <flags>` |
| `ctjets` | Chrono Trigger: Jets of Time | `!preset <preset>` |
| `contra` | Contra | KONOT support only |
| `sgl` | SpeedGaming Live | Passive (all commands are no-ops) |
| `smwhacks` / `twwr` | SMW Hacks / Wind Waker | Passive (no commands) |

### 5. KONOT System (`misc/konot.py`)

**King of the North Tournament** — An elimination series:
1. `!konot` creates a `RacetimeKONOTGame` + first `RaceTimeKONOTSegment`.
2. On `status_finished`, advancing players (all non-DNF except last place) are invited to a new room.
3. Series ends when ≤2 entrants remain.

### 6. Race Flow

**Standard Race (e.g., ALTTPR):**
1. Bot detects new room via polling → `begin()` → sends intro with `msg_actions` UI.
2. User issues command (e.g., `!newrace --preset=standard`).
3. Handler generates seed, posts URL, sets race info, marks `seed_rolled = True`.
4. `race_data()` dispatches `status_*` events on state changes.
5. `status_in_progress` → sends spoiler log if applicable.
6. `status_finished` → if KONOT, creates next elimination room.
7. `end()` → bot leaves room.

**Tournament Race:**
1. `TournamentResults` DB record associates room to tournament event/episode.
2. Tournament entrants are auto-accepted; gatekeepers get monitor status.
3. `!tournamentrace` delegates to tournament handler's `process_tournament_race()`.

---

## Domain 2: Web API

### 1. Overview

The web API is built on **Quart** (an async Flask-compatible framework) defined in `alttprbot_api/api.py`. It serves both:
- **HTML pages** (rendered via Jinja2 templates) for user-facing dashboards
- **JSON API endpoints** for programmatic access

Authentication uses **Discord OAuth2** via `quart_discord.DiscordOAuth2Session` with the `identify` scope. Some API endpoints use **API key authentication** via the `Authorization` header (checked against `AuthorizationKeyPermissions` model).

### 2. Blueprints

**10 blueprints** are registered:

| Blueprint | URL Prefix | Purpose |
|-----------|-----------|---------|
| `presets` | `/presets` | User-managed randomizer presets (CRUD) |
| `racetime` | `/` | RaceTime.gg bot commands API + RTGG OAuth verification |
| `ranked_choice` | `/ranked_choice` | Ranked-choice voting system |
| `settingsgen` | `/api/settingsgen` | Mystery randomizer settings generation API |
| `sglive` | `/sglive` | SpeedGaming Live event seed generators & reports |
| `tournament` | `/` | Tournament submission forms |
| `triforcetexts` | `/triforcetexts` | Community Triforce text submissions + moderation |
| `asynctournament` | `/async` | Async tournament dashboard, review queue, leaderboard |
| `schedule` | `/schedule` | Event scheduling (DEBUG only) |
| `user` | `/user` | User profiles (DEBUG only, not implemented) |

### 3. Authentication

**Two auth mechanisms:**

1. **Discord OAuth2** — Login redirects to Discord with `identify` scope. `@requires_authorization` decorator protects routes. Handles `Unauthorized`, `AccessDenied`, `InvalidGrantError`, and `TokenExpiredError`.

2. **API Key Auth** (`auth.py`) — `@authorized_key(auth_key_type)` decorator checks the `Authorization` header against `AuthorizationKeyPermissions` model. Used by async tournament API and racetime command API.

### 4. Core Routes

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/` | None | Homepage |
| GET | `/login/` | None | Initiates Discord OAuth |
| GET | `/callback/discord/` | None | OAuth callback |
| GET | `/me/` | Discord | User profile page |
| GET | `/logout/` | None | Revokes session |
| GET | `/healthcheck` | None | Checks Discord bot is alive |
| GET/POST | `/purgeme` | Discord | GDPR-style data deletion |

### 5. Key Blueprint Endpoints

#### Presets (`/presets`)
CRUD for user-managed randomizer presets. Browse namespaces, create/edit/delete presets, download YAML. JSON API at `/presets/api/<rand>/list` and `/presets/api/<rand>?preset=X`.

#### RaceTime (`/`)
- `POST /api/racetime/cmd` — Execute bot command remotely (API key auth).
- `GET /racetime/verification/initiate` — Starts RaceTime.gg account linking via OAuth.
- `GET /racetime/verify/return` — Completes RTGG→Discord account verification.

#### Async Tournament (`/async`)
Full API + web UI for asynchronous tournament management:
- **API** (key auth): List tournaments, races, pools, permalinks, leaderboard.
- **Web UI** (Discord auth): Player dashboard, review queue, leaderboard, reattempt forms.

#### SG Live (`/sglive`)
Dashboard with seed generators for SpeedGaming Live events (ALTTPR, OoTR, SMZ3, SMR, FFR). Capacity report for scheduling analysis.

#### Settings Generator (`/api/settingsgen`)
Mystery settings generation from weight JSON or named weightsets.

#### Tournament (`/submit`)
Tournament settings submission forms with per-event templates.

#### Triforce Texts (`/triforcetexts`)
Community-submitted end-game texts with moderation queue. Character-validated (19 chars × 3 lines, JP + ASCII).

#### Ranked Choice (`/ranked_choice`)
Ranked-choice voting interface with guild role access control.

### 6. Templates

**38 templates** organized by feature: core pages (index, profile, error), presets CRUD, async tournament dashboard, triforce text moderation, ranked choice voting, tournament submission forms, SGL dashboard, and schedule management.
