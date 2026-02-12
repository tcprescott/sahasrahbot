# System Patterns

> Last updated: 2026-02-11

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
Each RaceTime game category has a handler class extending `SahasrahBotCoreHandler`. Handlers define game-specific commands and seed generation logic.

### Blueprint Pattern (Web API)
The Quart API uses blueprints to organize routes by feature (presets, tournaments, voting, etc.).

### Preset-Driven Generation
Randomizer seeds are generated via a preset system. `SahasrahBotPresetCore` loads YAML presets (from disk or database) and delegates to game-specific subclasses (`ALTTPRPreset`, `SMPreset`, `SMZ3Preset`, etc.).

### Guild Config Monkey-Patching
`discord.Guild` is monkey-patched with `config_get/set/delete/list` methods backed by database + `aiocache` in-memory caching.

## Data Flow

### Seed Generation
```
User Command → Preset Loader (YAML/DB) → Game-Specific Generator → External API → Embed + Response
```

### Tournament Match Lifecycle
```
SpeedGaming Schedule → Room Creation (RaceTime.gg) → Player Invites → Seed Roll → Race → Results → Google Sheets
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
| Google Sheets | REST API | Results recording |
| AWS S3 | SDK | Spoiler log / patch storage |
| Discord | Gateway + REST | Bot interactions |
| ALTTPR Ladder | REST API | Racer verification |
