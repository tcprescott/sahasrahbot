# CLAUDE.md

> Guidelines for AI assistants working on SahasrahBot.

## Project Overview

SahasrahBot is a **monolithic async Python application** that generates randomized game seeds and organizes community races for the ALTTP randomizer community. It runs four concurrent subsystems in a single event loop:

```
sahasrahbot.py (entry point)
├── Tortoise ORM init (MySQL)
├── alttprbot.presentation.discord   → Main Discord bot (discord.py v2)
├── alttprbot.presentation.audit     → Audit/moderation Discord bot (separate token)
├── alttprbot.presentation.racetime  → RaceTime.gg race bot (racetime-bot SDK)
└── alttprbot.presentation.{api,web} → Web (Quart): REST API (api) + OAuth/SPA backend (web), one app/port
```

> The four surfaces were folded into a single `alttprbot/` package under
> `alttprbot/presentation/` during the three-tier migration (Phase 1). See the
> Project Structure below and [docs/architecture-layers.md](docs/architecture-layers.md).

All subsystems share the same database connection, ORM models, and utility libraries. They run in a single process intentionally — the Quart API and tournament system need direct access to the live `discordbot` object.

## Quick Reference

| Item | Detail |
|------|--------|
| Language | Python 3.11+ |
| Package manager | Poetry |
| Database | MySQL via Tortoise ORM (async) |
| Migrations | Aerich (`aerich migrate` / `aerich upgrade`) |
| Entry point | `python sahasrahbot.py` |
| Config | `config.py` — pydantic-settings, env vars / `.env` file |
| Tests | `pytest` + `pytest-asyncio` (`poetry run pytest`); debug mode also enables test fixtures |
| Linting | `pycodestyle`, `pylint`, `autopep8` (dev deps) |

## Project Structure

```
sahasrahbot.py              # Entry point — starts all 4 subsystems
config.py                   # Runtime config (pydantic-settings, env-backed)
alttprbot/                  # Single package — top-level directories ARE the tiers
  presentation/             # Tier 1 — thin adapters (folded-in surfaces, Phase 1)
    discord/                #   Main Discord bot (bot.py, cogs/, util/)
    audit/                  #   Audit Discord bot (separate token, privileged intents)
    racetime/               #   RaceTime.gg integration (bot.py, core.py, handlers/)
    api/                    #   REST API — no session/OAuth (auth.py, blueprints/)
    web/                    #   Web BFF — Quart app, OAuth, SPA (web.py, oauth_client.py, blueprints/, spa/)
  services/                 # Tier 2 — business logic
    seedgen/                #   Seed generation, was alttprgen/ (presets, providers)
    tournament/             #   Tournament orchestrators + registry (was alttprbot/tournament/)
    _notify/                #   Fire-and-forget notification queue + presentation gateways
    audit_service.py        #   AuditService + AuditActions
  repositories/             # Tier 3 — pure Tortoise CRUD (returns models)
  models/                   # Tier 4 — Tortoise ORM models (50+ entities, unchanged)
  util/                     # Shared utilities (telemetry, config contract, etc.)
  exceptions.py             # Custom exception hierarchy
presets/                    # YAML preset files for randomizer generation
config/                     # Tournament YAML config
migrations/                 # Aerich database migrations
helpers/                    # Standalone utility scripts (validation, conversion)
utils/                      # Runtime tools: door-rando git submodules, enemizer installer, flips binaries
data/                       # Runtime state dir (e.g. bingosync cookie); contents gitignored
tests/                      # pytest + pytest-asyncio (unit/, integration/)
docs/                       # All documentation (context, design, guides, plans, user-guide)
```

## Development Setup

```bash
# Install dependencies
poetry install

# Door-randomizer presets need the utils/ submodules + enemizer binaries
git submodule update --init
(cd utils/enemizer && ./install.sh)

# Configure environment — copy and fill in required values
cp .env.example .env

# Validate config before running
poetry run python helpers/validate_runtime_config.py

# Run the application
poetry run python sahasrahbot.py

# Database migrations
poetry run aerich upgrade    # Apply pending migrations
poetry run aerich migrate    # Create new migration

# Seed local DB with test fixtures (DEBUG only)
poetry run python helpers/seed_test_fixtures.py
```

## Key Conventions

### Code Style
- **Snake case** for files, functions, variables: `tournament_results.py`, `create_race_room()`
- **PascalCase** for classes: `TournamentRace`, `ALTTPRPreset`, `SahasrahBotCoreHandler`
- **SCREAMING_SNAKE_CASE** for config constants: `DISCORD_TOKEN`, `SG_API_ENDPOINT`
- All IO operations are async (`async def` / `await`)
- Use Tortoise ORM for new database code (the legacy raw SQL `alttprbot/database/` layer has been removed)

### Async Patterns
- Single event loop drives all 4 subsystems — never use `asyncio.run()` inside the app
- Background tasks use `discord.ext.tasks.loop()` decorator
- External HTTP calls via `aiohttp` (async)
- Database queries via Tortoise ORM awaitable methods

### Discord.py Patterns
- Cogs inherit `commands.Cog` or `commands.GroupCog`, loaded via `bot.load_extension()`
- Slash commands: `@app_commands.command()` decorator
- Persistent views: `discord.ui.View` with `timeout=None`, re-registered on startup
- Guild-restricted commands use `@app_commands.guilds()` with guild IDs from config

### Error Handling
- Custom exceptions extend `SahasrahBotException` (in `alttprbot/exceptions.py`)
- `SahasrahBotException` subclasses are filtered from Sentry reporting
- Discord command errors handled centrally by the `errors` cog

### Configuration
- Runtime config via `config.py` using pydantic-settings (`Settings` class)
- Access as module-level constants: `import config; config.DISCORD_TOKEN`
- Per-guild config stored in DB via `GuildConfigService` (`alttprbot/services/guild_config_service.py`)
- Feature flags: `DISCORD_ROLE_ASSIGNMENT_ENABLED`, `TOURNAMENT_CONFIG_ENABLED`, `TELEMETRY_ENABLED`, `DEBUG`

### Database
- **ORM (preferred):** Tortoise ORM — `await models.Thing.create(...)`, `.get_or_none(...)`, `.filter(...)`
- **Legacy:** Previous raw SQL helper (`alttprbot/util/orm.py`) has been removed; use model-based ORM operations
- **Migrations:** Aerich manages schema evolution; migrations in `migrations/models/`

### Dependencies
- All direct imports must have explicit declarations in `pyproject.toml`
- Run `poetry run python helpers/check_dependency_declarations.py` to validate
- No intentional transitive-only reliance on packages

## Architecture: Three-Tier Layering

SahasrahBot uses a strict three-tier architecture inside a single `alttprbot/` package (migration completed 2026). Respect these boundaries — imports may only point downward:

```
Presentation (alttprbot/presentation/{discord,audit,racetime,api,web}/)
  → Service (alttprbot/services/)  → Repository (alttprbot/repositories/)  → Models (alttprbot/models/)
```

- **Presentation:** thin — calls services, renders results, catches their errors. No business logic; no `alttprbot.repositories`/`alttprbot.models` import. `api/` (REST, no session/OAuth) and `web/` (Quart app owner, OAuth, SPA) share one process/port but never import each other — enforced by import-linter; `sahasrahbot.py` is the only place that wires them together.
- **Service:** business rules/validation/authz/orchestration/audit/notify. Raises `ValueError`/`PermissionError`/`SahasrahBotException`. Never imports `discord`/`racetime_bot`/`quart`/`alttprbot.presentation`; reach surfaces via a `_notify` gateway.
- **Repository:** pure Tortoise CRUD; returns models. No business logic/notify.

The four `alttprbot_*` packages have been folded into `alttprbot/presentation/`, and `alttprgen`/`tournament` into `alttprbot/services/`. Enforcement: `poetry run lint-imports` (import-linter, **blocking in CI** — see [.github/workflows/lint.yml](.github/workflows/lint.yml) and `.pre-commit-config.yaml`; all five contracts are green) + edit-time Claude Code hooks. **Full rules and phase plan:** [docs/architecture-layers.md](docs/architecture-layers.md), [docs/plans/three_tier_migration.md](docs/plans/three_tier_migration.md).

## Architecture Patterns

### Seed Generation
```
User Command → Preset Loader (YAML/DB) → Game-Specific Generator → External API → Embed + Response
```
- Provider reliability contract: 60s timeout, 3-attempt exponential retry
- Normalized exceptions in `alttprbot/services/seedgen/provider_exceptions.py`

### Tournament System
- Orchestrator classes in `alttprbot/services/tournament/` (business logic), registered in
  `registry.py` (`AVAILABLE_TOURNAMENT_HANDLERS`, slug → `TournamentEntry`)
- Driven from presentation by `presentation/discord/tournament/coordinator.py` (`TournamentCoordinator`)
  and `dispatch.py`; Discord rendering in `presenter.py`
- Seasonal enable/disable via registry (code-level; DB-backed self-service design approved — see
  `docs/design/self_service_tournaments.md`)

### RaceTime Integration
- Handler pattern: game-specific handlers extend `SahasrahBotCoreHandler`
- Compatibility adapter in `core.py` bridges official `racetime-bot` SDK with legacy expectations
- Per-category OAuth credentials resolved dynamically from env vars

### Web API
- Quart (async Flask-compatible) with blueprint pattern
- Discord OAuth via Authlib

## Important Files to Read First

When working on a task, start with these context files:

1. `docs/context/active_state.md` — Current focus, known issues, upcoming work
2. `docs/context/system_patterns.md` — Architecture, data flow, design patterns
3. `docs/context/tech_stack.md` — Dependencies, versions, external APIs
4. `docs/context/coding_standards.md` — Naming, async, database conventions
5. `docs/MASTER_INDEX.md` — Full documentation index

After completing significant work, update the relevant context file(s).

## What NOT to Do

- Do not create Markdown files in the project root (except `README.md` and this file). Place docs under `docs/`.
- Do not guess business reasoning for architectural decisions — ask the maintainer.
- Do not add new raw SQL database modules; use Tortoise ORM.
- Do not introduce synchronous blocking IO in the async event loop.
- Do not commit `.env` files or secrets.
- Do not use `asyncio.run()` inside the running application (the loop is already running).

## External Services

The bot integrates with many external APIs. Key ones:

| Service | Purpose |
|---------|---------|
| alttpr.com | ALTTPR seed generation |
| racetime.gg | Race room management (WebSocket + REST, OAuth2) |
| speedgaming.org | Tournament scheduling |
| Discord API | Bot interactions + OAuth2 web auth |
| AWS S3 | Spoiler log / patch storage |
| Sentry | Error tracking (optional) |
