# SahasrahBot Documentation — Master Index

> Last updated: 2026-02-11

## Context (AI Agent Reference)

Machine-readable reference files for coding agents:

| File | Description |
|------|-------------|
| [Active State](context/active_state.md) | Current sprint focus, known issues, upcoming work |
| [System Patterns](context/system_patterns.md) | Architecture, data flow, design patterns, module layers |
| [Tech Stack](context/tech_stack.md) | All dependencies with versions, AWS services, external APIs |
| [Coding Standards](context/coding_standards.md) | Naming, async patterns, database patterns, project structure |

## Design Documents

Architectural analysis and domain documentation:

| File | Description |
|------|-------------|
| [Discord Bot Domain](design/discord_bot_domain.md) | Main bot & audit bot: cogs, commands, listeners, UI views, background tasks |
| [Tournament System](design/tournament_system_analysis.md) | Tournament framework: base classes, 20+ handlers, SpeedGaming integration, match lifecycle |
| [RaceTime & Web API](design/racetime_and_web_api.md) | RaceTime.gg bot (12 categories, handlers, race flow) and Quart web API (10 blueprints, auth, templates) |
| [Core Library & Data Layer](design/core_library_data_layer.md) | Randomizer generation, Tortoise ORM models (50+), database layer, utilities, preset system, migrations |

## User Guide

End-user documentation (GitHub Pages site at sahasrahbot.synack.live):

| File | Description |
|------|-------------|
| [Index](user-guide/index.md) | Landing page |
| [Discord Commands](user-guide/discord.md) | Discord command reference |
| [Presets](user-guide/presets.md) | Preset usage guide |
| [Mystery](user-guide/mystery.md) | Mystery randomizer guide |
| [Mystery YAML](user-guide/mysteryyaml.md) | Mystery YAML format reference |
| [RaceTime.gg](user-guide/rtgg.md) | RaceTime.gg bot usage |
| [League Season 3 Mystery](user-guide/mystery/league_season3.md) | League-specific mystery settings |
