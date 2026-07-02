# System Patterns

> Last updated: 2026-07-01

## Architecture Overview

SahasrahBot is a **monolithic async Python application** that runs four subsystems concurrently in a single event loop:

```
sahasrahbot.py (entry point)
├── Tortoise ORM init (MySQL)
├── alttprbot/presentation/discord  → Discord bot (discord.py)
├── alttprbot/presentation/audit    → Audit Discord bot (separate token)
├── alttprbot/presentation/racetime → RaceTime.gg bot (racetime-bot)
├── alttprbot/presentation/api → REST API (no session/OAuth)
└── alttprbot/presentation/web → Web BFF for the SPA (Quart app, Discord OAuth)
```

All four subsystems share the same database connection, models, and utility libraries.

## Startup Sequence & Failure Modes

Current boot order in `sahasrahbot.py`:

1. Initialize Tortoise ORM connection.
2. Create async service tasks for Discord bot, audit bot, Quart API (`run_task`), and RaceTime category bots.
3. Register SIGINT/SIGTERM handlers that trigger a shared shutdown event.
4. Wait on shutdown event while monitoring service task exits.
5. On shutdown: stop RaceTime/Discord/Audit subsystems, cancel remaining service tasks, and close DB connections.

Observed failure characteristics:

- Service tasks are now monitored; unexpected service task exits trigger coordinated shutdown.
- Quart API bind host/port is currently hardcoded in entrypoint (`127.0.0.1:5001`).
- RaceTime credential resolution is dynamic per category (`RACETIME_CLIENT_ID_<CATEGORY>`, `RACETIME_CLIENT_SECRET_<CATEGORY>`), so missing keys fail per category at runtime.

## Author Intent (Verified)

These intent notes were confirmed directly with the repository author (2026-02-11) to avoid guessing “why” from code structure alone:

- **Single-process / single event loop:** This is intentionally kept together because multiple parts of the system need access to the live in-process `discordbot` object (notably the Quart API and tournament subsystem). Splitting into separate processes would require reworking those call paths (e.g., RPC/queue) rather than being a drop-in deployment tweak.
- **Audit bot separation:** The audit bot exists as a separate Discord application/token primarily because audit/moderation features require privileged intents (especially message content), while the main bot keeps narrower intents.

## Core Modules

| Module | Responsibility |
|--------|---------------|
| `alttprbot/services/`, `alttprbot/repositories/`, `alttprbot/models/`, `alttprbot/util/` | Core tiers: business logic, data access, ORM models, shared utilities |
| `alttprbot/presentation/discord/` | Main Discord bot with 17+ cogs |
| `alttprbot/presentation/audit/` | Audit/moderation Discord bot (2 cogs) |
| `alttprbot/presentation/racetime/` | RaceTime.gg integration (12+ game categories) |
| `alttprbot/presentation/api/` | REST API surface — public/API-key JSON, no session (5 blueprints) |
| `alttprbot/presentation/web/` | Web BFF — Quart app, Discord OAuth, SPA static serving, session-authenticated JSON for the SPA (6 blueprints) |

## Design Patterns

### Orchestrator + Coordinator Pattern (Tournament System)
Tournament business logic lives in orchestrator classes under `alttprbot/services/tournament/`,
registered in `registry.py` (`AVAILABLE_TOURNAMENT_HANDLERS`, slug → `TournamentEntry`). The Discord
surface drives them through `alttprbot/presentation/discord/tournament/coordinator.py`
(`TournamentCoordinator`) and `dispatch.py`, with rendering in `presenter.py`. (The former
`TournamentRace` template-method hierarchy was decomposed in the three-tier migration, Phase 7.)

### Cog Pattern (Discord Bot)
Discord functionality is organized into cogs — self-contained modules loaded as extensions. Each cog handles a specific domain (generation, tournaments, roles, etc.).

### Handler Pattern (RaceTime Bot)
Each RaceTime game category has a handler class extending `SahasrahBotCoreHandler`. Most handlers define game-specific commands/seed logic, but some are intentionally thin/no-op shells depending on season and category maturity.

### RaceTime Compatibility Adapter (Migration In Progress)
RaceTime integration now includes a compatibility layer to preserve historical SahasrahBot expectations while moving to the official `racetime-bot` package:
- `alttprbot/presentation/racetime/core.py` restores expected bot methods used across app surfaces (`start`, `join_race_room`, `startrace`, `get_team`) and tracks handlers in a task+handler container shape.
- `alttprbot/presentation/racetime/compat.py` provides stable handler lookup (`get_room_handler`) for API/tournament callers.
- `alttprbot/presentation/racetime/handlers/core.py` supports bot-injected context and websocket payload compatibility for `override_stream`.

### Blueprint Pattern (Web API)
The Quart API uses blueprints to organize routes by feature (presets, tournaments, voting, etc.).

### Preset-Driven Generation
Randomizer seeds are generated via a preset system. `SahasrahBotPresetCore` loads YAML presets (from disk or database) and delegates to game-specific subclasses (`ALTTPRPreset`, `SMPreset`, `SMZ3Preset`, etc.).

### Provider Reliability Contract (Phase 1 Complete)
Seed providers now support a shared execution contract for consistent reliability:
- **Shared wrapper** (`alttprbot/services/seedgen/provider_wrapper.py`) enforces:
  - 60-second timeout per attempt
  - 3-attempt exponential retry policy (1s, 2s backoff)
  - Structured logging for observability
- **Normalized exception taxonomy** (`alttprbot/services/seedgen/provider_exceptions.py`):
  - `SeedProviderTimeoutError` - timeout exceeded
  - `SeedProviderUnavailableError` - network/5xx errors
  - `SeedProviderRateLimitError` - HTTP 429 responses
  - `SeedProviderInvalidRequestError` - 4xx validation errors
  - `SeedProviderResponseFormatError` - parsing failures
- **Canonical response object** (`alttprbot/services/seedgen/provider_response.py`) standardizes provider outputs with metadata for audit
- **Provider adapters** (`alttprbot/services/seedgen/provider_adapters.py`) wrap legacy helper providers to use the shared contract
  - SMDashProvider adapter implemented as Phase 1 validation
  - Legacy compatibility wrappers maintain backward compatibility during rollout

### Guild Config Service
Per-guild config is read/written through `GuildConfigService`
(`alttprbot/services/guild_config_service.py`), backed by the guild-config repository with
`aiocache` in-memory caching. (The former `discord.Guild` monkey-patch was removed in Phase 10.)

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
- **Access Pattern**: Data access goes through repository classes (`alttprbot/repositories/`) using Tortoise model operations (the legacy `alttprbot/database/` package was removed)
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
