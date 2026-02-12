# Tournament Module (Non-Async) Audit

> Last updated: 2026-02-12  
> Scope: `alttprbot/tournament/` and non-async orchestration paths (`alttprbot/tournaments.py`, `alttprbot_discord/cogs/tournament.py`)  
> Excludes: `alttprbot_discord/cogs/asynctournament.py` and async Discord UI workflow

## Purpose

This document audits the non-async tournament module behavior, extension model, and operational risks as currently implemented.

## Component Boundary

Included modules:

- `alttprbot/tournament/core.py`
- `alttprbot/tournament/alttpr.py`
- All concrete handlers in `alttprbot/tournament/*.py`
- Daily/weekly handlers in `alttprbot/tournament/dailies/`
- Registry/orchestration glue in `alttprbot/tournaments.py`
- Discord scheduling/automation cog `alttprbot_discord/cogs/tournament.py`

Out-of-scope components:

- Async tournament Discord UX and views in `alttprbot_discord/cogs/asynctournament.py`

Boundary note:

- `alttprbot/tournament/alttpr_quals.py` is inside this module and operationally non-async from a room-management perspective, but it writes/reads async tournament models (`AsyncTournamentLiveRace`, `AsyncTournamentRace`, `AsyncTournamentPermalink`). This is a coupling point, not a scope violation.

## Architecture Pattern

Primary pattern is Template Method:

- `TournamentRace` in `core.py` defines shared lifecycle and hooks.
- `ALTTPRTournamentRace` in `alttpr.py` provides ALTTPR-specific seed/embed/DM defaults.
- Event handlers override `configuration()` plus optional hooks such as `roll()`, `create_race_room()`, `process_submission_form()`, `on_room_creation()`, and `on_race_start()`.

Registry pattern:

- `alttprbot/tournaments.py` exposes `TOURNAMENT_DATA` mapping event slug to class.
- In production mode, many handlers exist in code but are disabled through commented registry entries.

## End-to-End Runtime Flow

1. Discord cog loop `Tournament.create_races` scans SG episodes per active event in `TOURNAMENT_DATA`.
2. For each eligible episode, `tournaments.create_tournament_race_room(event_slug, episode_id)` is called.
3. `TournamentRace.construct_race_room` creates RT.gg room, writes `TournamentResults`, invites players (if applicable), DMs room info, posts room welcome, runs `on_room_creation`.
4. On `!tournamentrace`, handler `process_tournament_race()` rolls/assigns seed and updates RT.gg race info and DB record.
5. `tournaments.race_recording_task()` polls RT.gg completion and writes results to event worksheet in the configured Google Sheet.
6. Weekly/maintenance loops update scheduling-needs messages, Discord scheduled events, and invalid Discord identity reports.

## Core Contracts

### `TournamentConfig`

Operational contract fields with high impact:

- `racetime_category`, `racetime_goal`, `event_slug`
- `room_open_time`, `stream_delay`, `auto_record`
- `audit_channel`, `commentary_channel`, `scheduling_needs_channel`
- `helper_roles` (used by `can_gatekeep`)
- `create_scheduled_events`, `scheduling_needs_tracker`
- `gsheet_id`, `lang`, `coop`

### Base Lifecycle Hooks (`TournamentRace`)

- Required override in practice: `configuration()`
- Common optional overrides: `roll()`, `process_tournament_race()`, `create_race_room()`, `send_room_welcome()`, `on_room_creation()`, `on_race_start()`, `process_submission_form()`
- Shared helper behavior: player lookup fallback (Discord ID then Discord tag), RT.gg team helper gatekeeping, audit/commentary/player messaging

## Handler Inventory

### Active by default in production (`TOURNAMENT_DATA`)

| Event slug | Class | Category | Notes |
|---|---|---|---|
| `alttpr` | `ALTTPRQualifierRace` | `alttpr` | Open-entry qualifier flow; cross-writes async tournament models |
| `alttprdaily` | `AlttprSGDailyRace` | `alttpr` | Daily race automation and announcement webhook |
| `smz3` | `SMZ3DailyRace` | `smz3` | Weekly SMZ3 flow with category-specific announce behavior |
| `invleague` | `ALTTPRLeague` | `alttpr` | League API-driven mode/preset and coop/spoiler switches |
| `alttprleague` | `ALTTPROpenLeague` | `alttpr` | Open league variant of same logic |

### Implemented but currently disabled in registry

`ALTTPRCDTournament`, `ALTTPRDETournament`, `ALTTPRMiniTournament`, `ALTTPRCASBootsTournamentRace`, `ALTTPRNoLogicRace`, `SMWDETournament`, `ALTTPRFRTournament`, `ALTTPRHMGTournament`, `ALTTPRESTournament`, `SMZ3CoopTournament`, `SMBingoTournament`, `SMRLPlayoffs`, `ALTTPRSGLive`.

## Notable Divergences Across Handlers

- Room access model: invitational-only vs open-entry (`ALTTPRQualifierRace` and dailies diverge).
- Seed source model: static preset, title-map lookup, remote league API lookup, form-submitted settings, or non-seed game setup (Bingo).
- Notification model: direct player DMs, public announce channel posts, or external Discord webhook relays.
- Persistence model: all handlers update `TournamentResults`, but only some rely on `TournamentGames.settings` form submissions.

## Reliability Findings (Priority: Reliability/Operations First)

1. Registry toggling by comments is high-risk operational control.
   - Risk: accidental season activation/deactivation in deploy diff.
   - Impact: race room creation behavior changes without explicit runtime config trace.

2. Handler lifecycle contracts are implicit rather than validated.
   - Risk: missing override fails late (room creation or command-time failure).
   - Impact: failures surface during live race setup windows.

3. `ALTTPRQualifierRace` couples non-async tournament flow to async tournament tables.
   - Risk: model/schema changes in async domain can break qualifier flow.
   - Impact: critical seed lock-and-roll path failure for live qualifiers.

4. Player identity dependency is SG-data quality sensitive.
   - Risk: stale/invalid `discordId` + `discordTag` breaks player DM and role checks.
   - Existing mitigation: periodic `find_races_with_bad_discord` reporting.

5. Recording pipeline is best-effort with broad exception handling.
   - Risk: silently delayed or skipped worksheet writes if RT.gg/API parsing fails.
   - Impact: operational reporting drift between RT.gg and sheets.

## Operational Guardrails Already Present

- Duplicate room prevention: existing `TournamentResults` lookup and cancelled-room cleanup before creation.
- Time-buffered spoilers: `stream_delay` in recording task prevents immediate write on finish.
- Fallback user resolution: SG Discord ID first, then Discord tag lookup.
- Controlled seed commands: gatekeeping via RT.gg volunteer team membership or helper roles for guarded handlers.

## Suggested Stabilization Backlog

Reliability-first suggestions, scoped to this module:

1. Externalize `TOURNAMENT_DATA` enable/disable to config-backed flags (no commented registry edits).
2. Add startup validation that every enabled handler can build config and resolve required channels/roles.
3. Add explicit protocol checks for required methods per handler type at registration time.
4. Isolate async-model coupling in `alttpr_quals.py` behind a small adapter/service boundary.
5. Add structured retry and categorized error logging around SG fetch, RT.gg fetch, and worksheet append.

## Intent Status

User-confirmed intent preference for this audit cycle:

- Prioritize reliability and operations over seasonal flexibility.

Unconfirmed historical intent (left as open):

- Why seasonal enablement is currently managed through commented registry entries instead of explicit runtime configuration.
- Whether qualifier/async-model coupling is temporary migration scaffolding or long-term design.
