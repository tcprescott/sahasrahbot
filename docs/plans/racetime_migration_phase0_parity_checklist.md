# RaceTime Migration Phase 0: Baseline Parity Checklist

> Status: Active  
> Last updated: 2026-02-12  
> Parent plan: [RaceTime Bot Official Migration Plan](racetime_bot_official_migration_plan.md)

## Purpose

Capture pre-migration behavior evidence so post-migration validation can assert 1:1 functionality.

## Evidence Packet Metadata

- Environment: local / staging / production-like
- Runtime mode: DEBUG true/false
- Category slug under test
- Date/time window
- Operator (delivery hat)
- Validator (validation hat)

## A. Room Lifecycle Baseline

- [ ] Bot starts without category initialization errors
- [ ] Room discovered and handler attached for open race
- [ ] `status_pending` transition behavior recorded
- [ ] `status_in_progress` transition behavior recorded
- [ ] `status_finished` transition behavior recorded
- [ ] Handler cleanly detaches at terminal state

Evidence:

- startup log excerpt
- handler attach/detach log lines
- room status timestamps

## B. Command Surface Baseline

## Core commands

- [ ] `!help`
- [ ] `!lock`
- [ ] `!unlock`
- [ ] `!cancel`
- [ ] `!tournamentrace` permission checks

## ALTTPR commands

- [ ] `!newrace` preset path
- [ ] `!newrace --spoiler_race --countdown=...`
- [ ] `ex2_newrace` keyword parsing parity (e.g. `--quickswap`, `--branch`)

## Category-specific representative commands

- [ ] `smr`: `!dash ...`
- [ ] `smz3`: `!multiworld ...`
- [ ] one additional active category command

Evidence:

- full command transcript (input + bot response)
- race info field values after each command

## C. API Command Injection Baseline

Endpoint: `POST /api/racetime/cmd`

- [ ] Valid auth key executes command in room
- [ ] Invalid auth key denied with 403
- [ ] Nonexistent category fails safely

Evidence:

- request/response samples
- room chat output showing injected command and execution

## D. Tournament Workflow Baseline

- [ ] `startrace(...)` room creation succeeds
- [ ] Tournament room welcome flow behaves as expected
- [ ] RaceTime DM/send flow remains intact
- [ ] `get_team('sg-volunteers')` gatekeeping data consumed correctly

Evidence:

- room creation logs
- tournament workflow transcript

## E. Unlisted Room Recovery Baseline

- [ ] Unlisted room persistence row exists in `RTGGUnlistedRooms`
- [ ] Process restart rejoins unlisted room
- [ ] Completed/publicized rooms are removed from persistence

Evidence:

- DB row snapshots before/after
- rejoin log lines

## F. Pass/Fail Decision

- [ ] All mandatory checks pass
- [ ] Any deviations documented with impact
- [ ] Go/No-Go recommendation captured

## Deviation Template

- Check ID:
- Expected behavior:
- Observed behavior:
- Impact severity: low / medium / high
- Temporary mitigation:
- Follow-up owner/date:
