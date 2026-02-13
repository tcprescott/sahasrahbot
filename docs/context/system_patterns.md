# System Patterns

> Last updated: 2026-02-12

## Architecture Overview

SahasrahBot is a **monolithic async Python application** that runs four subsystems concurrently in a single event loop:

```
sahasrahbot.py (entry point)
├── Tortoise ORM init (MySQL)
├── alttprbot_discord  → Discord bot (discord.py)
├── alttprbot_audit    → Audit Discord bot (separate token)
├── alttprbot_racetime → RaceTime.gg bot (racetime-bot)
└── alttprbot_api      → Web API (Quart)
```

All four subsystems share the same database connection, models, and utility libraries.

## Startup Sequence & Failure Modes

Current boot order in `sahasrahbot.py`:

1. Initialize Tortoise ORM connection.
2. Create async tasks for Discord bot, audit bot, and Quart API.
3. Start RaceTime bots.
4. Enter `loop.run_forever()`.

Observed failure characteristics:

- Startup is task-based and not centrally supervised; subsystem failures can become runtime errors without coordinated shutdown.
- Quart API bind host/port is currently hardcoded in entrypoint (`127.0.0.1:5001`).
- RaceTime credential resolution is dynamic per category (`RACETIME_CLIENT_ID_<CATEGORY>`, `RACETIME_CLIENT_SECRET_<CATEGORY>`), so missing keys fail per category at runtime.

## Author Intent (Verified)

These intent notes were confirmed directly with the repository author (2026-02-11) to avoid guessing “why” from code structure alone:

- **Single-process / single event loop:** This is intentionally kept together because multiple parts of the system need access to the live in-process `discordbot` object (notably the Quart API and tournament subsystem). Splitting into separate processes would require reworking those call paths (e.g., RPC/queue) rather than being a drop-in deployment tweak.
- **Audit bot separation:** The audit bot exists as a separate Discord application/token primarily because audit/moderation features require privileged intents (especially message content), while the main bot keeps narrower intents.

## Core Modules

| Module | Responsibility |
|--------|---------------|
| `alttprbot/` | Core library: randomizer generation, models, database, utilities |
| `alttprbot_discord/` | Main Discord bot with 17+ cogs |
| `alttprbot_audit/` | Audit/moderation Discord bot (2 cogs) |
| `alttprbot_racetime/` | RaceTime.gg integration (12+ game categories) |
| `alttprbot_api/` | Quart web API (10 blueprints) |

## Design Patterns

### Template Method Pattern (Tournament System)
The tournament system uses `TournamentRace` as a base class defining the match lifecycle. 20+ concrete subclasses override `configuration()`, `roll()`, and form handling. Intermediate class `ALTTPRTournamentRace` adds ALTTPR-specific seed/DM workflow.

### Cog Pattern (Discord Bot)
Discord functionality is organized into cogs — self-contained modules loaded as extensions. Each cog handles a specific domain (generation, tournaments, roles, etc.).

### Handler Pattern (RaceTime Bot)
Each RaceTime game category has a handler class extending `SahasrahBotCoreHandler`. Most handlers define game-specific commands/seed logic, but some are intentionally thin/no-op shells depending on season and category maturity.

### RaceTime Compatibility Adapter (Migration In Progress)
RaceTime integration now includes a compatibility layer to preserve historical SahasrahBot expectations while moving to the official `racetime-bot` package:
- `alttprbot_racetime/core.py` restores expected bot methods used across app surfaces (`start`, `join_race_room`, `startrace`, `get_team`) and tracks handlers in a task+handler container shape.
- `alttprbot_racetime/compat.py` provides stable handler lookup (`get_room_handler`) for API/tournament callers.
- `alttprbot_racetime/handlers/core.py` supports bot-injected context and websocket payload compatibility for `override_stream`.

### Blueprint Pattern (Web API)
The Quart API uses blueprints to organize routes by feature (presets, tournaments, voting, etc.).

### Preset-Driven Generation
Randomizer seeds are generated via a preset system. `SahasrahBotPresetCore` loads YAML presets (from disk or database) and delegates to game-specific subclasses (`ALTTPRPreset`, `SMPreset`, `SMZ3Preset`, etc.).

### Provider Reliability Contract (Phase 1 Complete)
Seed providers now support a shared execution contract for consistent reliability:
- **Shared wrapper** (`alttprbot/alttprgen/provider_wrapper.py`) enforces:
  - 60-second timeout per attempt
  - 3-attempt exponential retry policy (1s, 2s backoff)
  - Structured logging for observability
- **Normalized exception taxonomy** (`alttprbot/alttprgen/provider_exceptions.py`):
  - `SeedProviderTimeoutError` - timeout exceeded
  - `SeedProviderUnavailableError` - network/5xx errors
  - `SeedProviderRateLimitError` - HTTP 429 responses
  - `SeedProviderInvalidRequestError` - 4xx validation errors
  - `SeedProviderResponseFormatError` - parsing failures
- **Canonical response object** (`alttprbot/alttprgen/provider_response.py`) standardizes provider outputs with metadata for audit
- **Provider adapters** (`alttprbot/alttprgen/provider_adapters.py`) wrap legacy helper providers to use the shared contract
  - SMDashProvider adapter implemented as Phase 1 validation
  - Legacy compatibility wrappers maintain backward compatibility during rollout

### Guild Config Monkey-Patching
`discord.Guild` is monkey-patched with `config_get/set/delete/list` methods backed by database + `aiocache` in-memory caching.

### Seasonal Registry Toggles
Seasonal enable/disable currently relies on code-level registry edits (including commented entries) in tournament and RaceTime category registries.

### Anonymous Telemetry (Added 2026-02-12)
Privacy-preserving telemetry for feature usage and reliability tracking:
- **Service interface:** `TelemetryService` protocol with `NoOpTelemetryService` and `DatabaseTelemetryService` implementations
- **Fail-open design:** Telemetry failures never impact user-facing flows; all operations wrapped in try/except
- **Bounded queue:** In-memory queue with configurable size limit to prevent unbounded growth
- **Privacy-first:** No user IDs, usernames, or identifiable data; guild IDs hashed with salt
- **Short retention:** Default 30-day retention with automated purge helper
- **Instrumentation pattern:** `record_event()` convenience function called at command boundaries

## Data Flow

### Seed Generation
```
User Command → Preset Loader (YAML/DB) → Game-Specific Generator → External API → Embed + Response
```

### Tournament Match Lifecycle
```
SpeedGaming Schedule → Room Creation (RaceTime.gg) → Player Invites → Seed Roll → Race → Results persisted in application database
```

### Async Tournament Flow
```
Admin Creates Tournament → Seeds Added to Pools → Players Start Runs via Discord UI → Review Queue → Scoring/Leaderboard
```

## Database Architecture

- **ORM**: Tortoise ORM with MySQL backend
- **Migrations**: Aerich (97 migrations, 2021–2024)
- **Dual Access Pattern**: Legacy raw SQL modules (`alttprbot/database/`) coexist with Tortoise ORM model usage
- **Caching**: `aiocache.SimpleMemoryCache` for guild config and various lookups

## External Integrations

| Service | Protocol | Purpose |
|---------|----------|---------|
| alttpr.com | REST API | ALTTPR seed generation |
| sm.samus.link / samus.link | REST API | SM/SMZ3 seed generation |
| varia.run | REST API | SM Varia generation |
| dashrando.net | REST API | SM Dash generation |
| ctjot.com | Web scraping | CT Jets of Time generation |
| SpeedGaming | REST API | Tournament scheduling |
| RaceTime.gg | WebSocket + REST | Race room management |
| BingoSync | Web scraping | Bingo room creation |
| AWS S3 | SDK | Spoiler log / patch storage |
| Discord | Gateway + REST | Bot interactions |
| Discord Bad Domains Feed | HTTPS JSON | Moderation domain-hash denylist updates |
| ALTTPR Ladder | REST API | Racer verification |

## Audit & Moderation Data Lifecycle

- Audit bot persists message history and prunes records older than 30 days via scheduled cleanup.
- DM content may be recorded in audit history tables for moderation/forensics workflows.
