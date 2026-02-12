# SahasrahBot: RaceTime.gg Integration

> Last updated: 2026-02-12
> Scope: `alttprbot_racetime/` integration architecture and operational flow

## Canonical Scope Note

This document is now RaceTime-focused.

For Web API documentation, use:

- [Web API JSON Endpoints](web_api_json_endpoints.md)
- [Web Frontend Route Map](web_frontend_routes.md)

## Overview

SahasrahBot integrates with [RaceTime.gg](https://racetime.gg) using the `racetime-bot` SDK. It runs per-category bots that join rooms, handle race lifecycle events, generate seeds through category handlers, and coordinate tournament-specific behavior.

The integration authenticates with OAuth2 client credentials and persists some room state (`RTGGUnlistedRooms`) for room rejoin behavior.

## Runtime Architecture

Startup behavior in `alttprbot_racetime/bot.py`:

1. Loads category configuration from `RACETIME_CATEGORIES`.
2. Resolves credentials from `config.RACETIME_CLIENT_ID_{SLUG}` and `config.RACETIME_CLIENT_SECRET_{SLUG}`.
3. Constructs one `SahasrahBotRaceTimeBot` per configured category and stores in `racetime_bots`.
4. `start_racetime(loop)` schedules all category bots.

`SahasrahBotRaceTimeBot` (`alttprbot_racetime/core.py`) extends `racetime_bot.Bot` and:

- selects handler classes per category,
- injects handler kwargs (`conn`, `logger`, `state`, `command_prefix`),
- authorizes and manages reauthorization,
- polls for new races,
- rejoins persisted unlisted rooms.

## Production Categories (from code)

| Slug | Handler Module | Domain |
|------|----------------|--------|
| `alttpr` | `handlers.alttpr` | ALTTPR |
| `contra` | `handlers.contra` | Contra |
| `ct-jets` | `handlers.ctjets` | Chrono Trigger Jets of Time |
| `ff1r` | `handlers.ff1r` | Final Fantasy 1 Randomizer |
| `sgl` | `handlers.sgl` | SpeedGaming Live |
| `smb3r` | `handlers.smb3r` | SMB3 Randomizer |
| `smr` | `handlers.smr` | Super Metroid Randomizer |
| `smw-hacks` | `handlers.smwhacks` | SMW Hacks |
| `smz3` | `handlers.smz3` | SMZ3 |
| `twwr` | `handlers.twwr` | Wind Waker Randomizer |
| `z1r` | `handlers.z1r` | Zelda 1 Randomizer |
| `z2r` | `handlers.z2r` | Zelda 2 Randomizer |

Notes:

- `sm` is present in source but commented out in category registration.
- `DEBUG` mode registers a test category flow.

## Core Handler Behavior

Base handler: `SahasrahBotCoreHandler` (`handlers/core.py`).

Shared state and controls:

- `seed_rolled` guards duplicate generation in a room.
- `state['locked']` restricts rolling to monitors.
- tracks race state flags including spoiler/tournament/KONOT-related state.

Lifecycle methods:

- `begin()` posts intro/setup behavior,
- `race_data()` processes state transitions and dispatches status handlers,
- `end()` handles room teardown logging.

Common command surface includes `!cancel`, `!tournamentrace`, `!konot`, `!lock`, `!unlock`, and monitor utility commands.

Spoiler-race helpers coordinate delayed spoiler release and countdown messaging.

## Game Handler Surface (high level)

- `handlers/alttpr.py`: primary rich command surface (`!newrace`, spoiler/mystery variants, tournament flows).
- `handlers/smz3.py`: preset race, spoiler, multiworld flows.
- `handlers/smr.py`: multiple backend generators (total/varia/dash/choozo/multiworld/playoff).
- `handlers/z1r.py`: flags/preset mappings.
- `handlers/z2r.py`: flags and preset shortcuts.
- other handlers include category-specific minimal or passive behavior.

## KONOT Flow

`misc/konot.py` handles King of the North elimination behavior:

1. initialize segment,
2. evaluate finish status,
3. create next room for advancing entrants,
4. terminate when final threshold is reached.

## Race Lifecycle Summary

Standard room flow:

1. detect/open room,
2. present intro/actions,
3. receive command and generate seed,
4. update room state and info,
5. process status transitions (`pending`, `in_progress`, `finished`),
6. run category/tournament follow-up logic,
7. teardown/leave room.

Tournament-linked behavior attaches to `TournamentResults` and tournament handlers for entrant handling and race processing.

## Related Documentation

- [Tournament System](tournament_system_analysis.md)
- [Web API JSON Endpoints](web_api_json_endpoints.md)
- [Web Frontend Route Map](web_frontend_routes.md)
