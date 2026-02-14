# CLAUDE.md

> Guidelines for AI assistants working on SahasrahBot.

## Project Overview

SahasrahBot is a **monolithic async Python application** that generates randomized game seeds and organizes community races for the ALTTP randomizer community. It runs four concurrent subsystems in a single event loop:

```
sahasrahbot.py (entry point)
├── Tortoise ORM init (MySQL)
├── alttprbot_discord  → Main Discord bot (discord.py v2)
├── alttprbot_audit    → Audit/moderation Discord bot (separate token)
├── alttprbot_racetime → RaceTime.gg race bot (racetime-bot SDK)
└── alttprbot_api      → Web API (Quart)
```

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
| Tests | No formal test suite; debug mode enables test fixtures |
| Linting | `pycodestyle`, `pylint`, `autopep8` (dev deps) |

## Project Structure

```
sahasrahbot.py              # Entry point — starts all 4 subsystems
config.py                   # Runtime config (pydantic-settings, env-backed)
alttprbot/                  # Core shared library
  alttprgen/                # Seed generation (presets, providers, reliability)
  database/                 # Legacy raw SQL modules
  models/                   # Tortoise ORM models (50+ entities)
  tournament/               # Tournament handler classes
  util/                     # Shared utilities (telemetry, config contract, etc.)
  exceptions.py             # Custom exception hierarchy
alttprbot_discord/          # Main Discord bot
  bot.py                    # Bot startup/shutdown
  cogs/                     # 20+ command groups (generator, tournament, daily, admin...)
  util/                     # Discord-specific utilities
alttprbot_audit/            # Audit Discord bot (separate token, privileged intents)
  bot.py                    # Audit bot startup
  cogs/                     # Audit + moderation cogs
alttprbot_racetime/         # RaceTime.gg integration
  bot.py                    # RaceTime bot startup
  core.py                   # Compatibility adapter for official SDK
  handlers/                 # Per-game-category race handlers (12+)
alttprbot_api/              # Quart web API
  api.py                    # App factory
  blueprints/               # Route groups (presets, tournament, racetime, etc.)
  templates/                # Jinja2 templates
  static/                   # Static assets
presets/                    # YAML preset files for randomizer generation
config/                     # Tournament YAML config
migrations/                 # Aerich database migrations (98 files)
helpers/                    # Standalone utility scripts (validation, conversion)
docs/                       # All documentation (context, design, guides, plans, user-guide)
```

## Development Setup

```bash
# Install dependencies
poetry install

# Configure environment — copy and fill in required values
cp config.py.example .env

# Validate config before running
poetry run python helpers/validate_runtime_config.py

# Run the application
poetry run python sahasrahbot.py

# Database migrations
poetry run aerich upgrade    # Apply pending migrations
poetry run aerich migrate    # Create new migration
```

## Key Conventions

### Code Style
- **Snake case** for files, functions, variables: `tournament_results.py`, `create_race_room()`
- **PascalCase** for classes: `TournamentRace`, `ALTTPRPreset`, `SahasrahBotCoreHandler`
- **SCREAMING_SNAKE_CASE** for config constants: `DISCORD_TOKEN`, `SG_API_ENDPOINT`
- All IO operations are async (`async def` / `await`)
- Use Tortoise ORM for new database code (not legacy raw SQL in `alttprbot/database/`)

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
- Per-guild config stored in DB via monkey-patched `guild.config_get()`/`guild.config_set()`
- Feature flags: `DISCORD_ROLE_ASSIGNMENT_ENABLED`, `TOURNAMENT_CONFIG_ENABLED`, `TELEMETRY_ENABLED`, `DEBUG`

### Database
- **ORM (preferred):** Tortoise ORM — `await models.Thing.create(...)`, `.get_or_none(...)`, `.filter(...)`
- **Legacy:** Previous raw SQL helper (`alttprbot/util/orm.py`) has been removed; use model-based ORM operations
- **Migrations:** Aerich manages schema evolution; migrations in `migrations/models/`

### Dependencies
- All direct imports must have explicit declarations in `pyproject.toml`
- Run `poetry run python helpers/check_dependency_declarations.py` to validate
- No intentional transitive-only reliance on packages

## Architecture Patterns

### Seed Generation
```
User Command → Preset Loader (YAML/DB) → Game-Specific Generator → External API → Embed + Response
```
- Provider reliability contract: 60s timeout, 3-attempt exponential retry
- Normalized exceptions in `alttprbot/alttprgen/provider_exceptions.py`

### Tournament System
- Template Method pattern: `TournamentRace` base class with 20+ concrete subclasses
- Subclasses override `configuration()`, `roll()`, and form handling
- Seasonal enable/disable via registry (code-level, migration to config in progress)

### RaceTime Integration
- Handler pattern: game-specific handlers extend `SahasrahBotCoreHandler`
- Compatibility adapter in `core.py` bridges official `racetime-bot` SDK with legacy expectations
- Per-category OAuth credentials resolved dynamically from env vars

### Web API
- Quart (async Flask-compatible) with blueprint pattern
- Discord OAuth via Authlib
- Some blueprints are DEBUG-only stubs (`schedule`, `user`)

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
