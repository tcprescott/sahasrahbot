# Tournament Module (Non-Async) Runbook

> Last updated: 2026-02-12  
> Scope: Operations and developer workflow for non-async tournament automation

## Audience

- Maintainers operating SG/RT.gg tournament automation
- Developers adding or modifying handlers under `alttprbot/tournament/`

## Preconditions

- Discord bot online and connected to target guilds.
- RaceTime category bot initialized for target `racetime_category`.
- Event slug present in `alttprbot/tournaments.py` `TOURNAMENT_DATA`.
- Target guild/channel/role IDs in handler `configuration()` are valid.
- If results recording is expected, `gsheet_id` is valid and worksheet access is authorized.

## Daily Operations Checklist

1. Confirm background loops are running in `alttprbot_discord/cogs/tournament.py`:
   - `create_races`
   - `week_races`
   - `record_races`
   - `find_races_with_bad_discord`
2. Watch audit channels for room-creation failure messages.
3. Verify near-term episodes get RT.gg rooms inside the configured open window (`stream_delay + room_open_time`).
4. Verify `TournamentResults` rows are written and later marked `written_to_gsheet=1` after finish + delay.

## Event Enable/Disable Procedure (Current State)

Current implementation uses static code registry entries in `TOURNAMENT_DATA`.

- Enable event: add slug-to-class mapping.
- Disable event: remove or comment mapping.
- Validate by restarting bot and confirming event appears in loop scan logs.

Operational caution:

- Treat registry edits as release-controlled changes; verify no accidental slug drift.

## Adding a New Tournament Handler

1. Create handler class in `alttprbot/tournament/`.
2. Inherit from:
   - `TournamentRace` for fully custom workflows, or
   - `ALTTPRTournamentRace` for standard ALTTPR seed/embed/DM flow.
3. Implement `configuration()` returning complete `TournamentConfig`.
4. Implement `roll()` and/or `process_tournament_race()` as needed.
5. Override `create_race_room()` only when non-default RT.gg room flags are required.
6. Register event slug in `alttprbot/tournaments.py` `TOURNAMENT_DATA`.
7. Confirm SG event slug, RT.gg category, channel IDs, and helper roles resolve at runtime.

## Troubleshooting Matrix

| Symptom | Likely location | First checks |
|---|---|---|
| Room not created | `tournaments.create_tournament_race_room` | Event active in registry, SG episode exists in open window, prior room not active |
| Seed command fails | Handler `process_tournament_race` | Guard conditions (settings/pool/auth), category bot availability |
| Players not DM’d | `TournamentRace.send_player_message` | SG player identity quality, member exists in guild, DMs allowed |
| Scheduling needs stale | `Tournament.update_scheduling_needs` | `scheduling_needs_channel` set and bot can edit prior bot message |
| GSheet not updating | `tournaments.race_recording_task` | `gsheet_id`, worksheet existence/creation, race finished state, stream delay window |
| Qualifier entrant mismatch | `alttpr_quals.py` helpers | Live race record exists, entrants joined before start transition |

## High-Risk Areas to Recheck During Changes

- `TournamentRace.update_data()` player resolution paths.
- `TournamentRace.can_gatekeep()` role-based authorization.
- Any override of `create_race_room()` chat/invitational flags.
- `tournaments.race_recording_task()` status parsing and append logic.
- `ALTTPRQualifierRace` integration with async-model tables.

## Safe Change Workflow

1. Make one handler change at a time.
2. Validate config resolution for guild/channels/roles before deploy.
3. Validate at least one room creation path and one seed roll path in controlled environment.
4. Validate one completed-race recording path for affected event.
5. Roll forward only after audit-channel noise is clean.

## Known Operational Debt

- Registry-level feature toggles are code-comment driven.
- Non-async module includes qualifier logic coupled to async tournament models.
- Broad exception handling in loops can mask repeated transient failures.

## Recommended Near-Term Controls

- Add boot-time self-check command that verifies all enabled handler configuration dependencies.
- Add event-scoped health summary message to audit channels for schedule scan and recording outcomes.
- Move event enable/disable and per-event metadata to config-backed declarations.
