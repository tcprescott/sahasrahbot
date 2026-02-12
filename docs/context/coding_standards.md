# Coding Standards

> Last updated: 2026-02-12
> Derived from existing codebase patterns (not prescriptive — descriptive of current state).

## Python Version

- Minimum: Python 3.11
- Uses `async`/`await` extensively throughout

## Package Management

- **Poetry** for dependency management and virtual environments
- Always use `poetry run python` for execution
- Dependencies declared in `pyproject.toml`

## Project Structure

```
sahasrahbot.py          # Entry point — starts all 4 subsystems
config.py               # Global configuration (module-level constants)
alttprbot/              # Core library (shared across subsystems)
  alttprgen/            # Randomizer generation
  database/             # Legacy raw SQL database modules
  models/               # Tortoise ORM models
  tournament/           # Tournament handler classes
  util/                 # Shared utilities
alttprbot_discord/      # Main Discord bot
  cogs/                 # Discord command groups
  util/                 # Discord-specific utilities
alttprbot_audit/        # Audit Discord bot
  cogs/                 # Audit/moderation cogs
alttprbot_racetime/     # RaceTime.gg bot
  handlers/             # Per-category race handlers
  misc/                 # Misc racetime utilities (KONOT)
alttprbot_api/          # Quart web API
  blueprints/           # Route groups
  templates/            # Jinja2 templates
  static/               # Static assets
  util/                 # API utilities
presets/                # YAML preset files
migrations/             # Aerich database migrations
```

## Naming Conventions

### Files
- Snake case: `tournament_results.py`, `guild_config.py`
- Cog files named after their feature: `generator.py`, `tournament.py`, `asynctournament.py`

### Classes
- PascalCase: `TournamentRace`, `ALTTPRPreset`, `SahasrahBotCoreHandler`
- Tournament handlers: `ALTTPR{Name}Tournament` (e.g., `ALTTPRDETournament`)
- Discord utilities: `{Game}Discord` (e.g., `ALTTPRDiscord`, `SMZ3Discord`)

### Functions
- Snake case: `create_race_room()`, `process_tournament_race()`, `generate_spoiler_game()`
- Async functions: same convention, prefixed with `async def`

### Config Keys
- SCREAMING_SNAKE_CASE for module-level config: `DISCORD_TOKEN`, `SG_API_ENDPOINT`
- PascalCase for guild config keys: `DailyAnnouncerChannel`, `AuditLogging`

## Async Patterns

- All IO operations are async (`aiohttp`, `aioboto3`, `tortoise-orm`, etc.)
- Single event loop drives all 4 subsystems
- Background tasks use `discord.ext.tasks.loop()` decorator
- Database queries use either Tortoise ORM awaitable methods or `await orm.select()`/`orm.execute()`
- Startup currently uses fire-and-forget `loop.create_task(...)` orchestration in entrypoint; this is an observed legacy pattern and should be treated as technical debt unless explicit supervision is added.

## Discord.py Patterns

### Cogs
- Each cog is a class inheriting `commands.Cog` or `commands.GroupCog`
- Loaded as extensions via `bot.load_extension()`
- Slash commands use `@app_commands.command()` decorator
- Legacy prefix commands use `@commands.command()` decorator
- Guild-restricted commands use `@app_commands.guilds()` with guild IDs from config

### UI Components
- Persistent views use `discord.ui.View` with `timeout=None`
- Modals use `discord.ui.Modal`
- Views are re-registered on bot startup via `bot.add_view()`

## Database Patterns

### Tortoise ORM (preferred for new code)
```python
# Create
await models.AuditGeneratedGames.create(field=value, ...)

# Query
result = await models.Presets.get_or_none(randomizer=r, preset_name=n)
results = await models.AsyncTournamentRace.filter(tournament=t).all()

# Update
record.field = value
await record.save()
```

### Legacy Raw SQL (existing code in `alttprbot/database/`)
```python
from alttprbot.util import orm

results = await orm.select("SELECT * FROM table WHERE col=%s", [value])
await orm.execute("INSERT INTO table (col) VALUES (%s)", [value])
```

## Error Handling

- Custom exceptions in `alttprbot/exceptions.py` extend `SahasrahBotException`
- `SahasrahBotException` subclasses are filtered from Sentry reporting
- Discord command errors handled centrally by the `errors` cog
- External API errors generally caught at the command/handler level

## Configuration

- Configuration is provided through `config.py` as module-level constants consumed across the codebase.
- Per-guild config stored in database via `guild.config_get()`/`guild.config_set()`
- Config values cached with `aiocache`
- API startup currently sets `OAUTHLIB_INSECURE_TRANSPORT=1` unconditionally.
- `APP_SECRET_KEY` currently permits empty default in config model.

### Config Ownership Rules (Needed)

- Avoid new cross-layer imports where low-level data modules depend on Discord-layer utilities.
- Treat guild config cache key/value shape as a contract; do not mix scalar and row-list payloads under the same key.
- Prefer ID-based guild channel configuration over name-based configuration.

## Open Intent Questions

- Why should insecure OAuth transport be globally enabled rather than debug-only?
- Why is an empty app secret considered acceptable for any non-test runtime?
- Why is startup supervision intentionally best-effort rather than fail-fast?
- Why is config access still split across raw SQL helpers and ORM-backed guild monkey-patching?
- Why are seasonal enable/disable toggles maintained as commented registry entries instead of explicit configuration?

## Testing

- No formal test suite observed in the codebase
- Debug mode (`config.DEBUG`) enables:
  - Test guild for slash command syncing
  - Test tournament handler
  - Test racetime category
  - Debug-only web API blueprints
  - Local test data fixtures in `test_input/`

## Linting

- `pycodestyle` and `pylint` available as dev dependencies
- `autopep8` for auto-formatting
- No enforced CI/CD lint step observed
