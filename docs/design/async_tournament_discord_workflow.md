# Async Tournament Discord Workflow

> Last updated: 2026-02-12

## Scope

This document covers the async tournament workflow driven by the Discord module and related shared components.

Primary implementation surfaces:

- `alttprbot_discord/cogs/asynctournament.py` (Discord commands, views, race lifecycle)
- `alttprbot/util/asynctournament.py` (seed allocation + scoring + leaderboard)
- `alttprbot/models/models.py` (async tournament data model)
- `alttprbot_api/util/checks.py` (role/permission checks)
- `alttprbot_api/blueprints/asynctournament.py` (web review, queue, leaderboard, reattempt)

This is intentionally separate from the normal tournament framework in `alttprbot/tournament/*`.

## Verified Intent (Author-Confirmed)

The following policy intent is explicitly confirmed by the repository owner and is not inferred from code:

- Account-age + whitelist gate exists as defense in depth against seed-pool reconnaissance via throwaway/multiple Discord accounts.
- Timeout policy aims to force near-immediate commitment after seed assignment while leaving setup buffer.
- 12-hour in-progress timeout exists to close abandoned runs and avoid indefinitely outstanding races.
- Owner-only admin commands (`/async create`, `/async addseed`, `/async repost`, `/async permissions`) are a temporary safeguard, not a permanent governance model.
- Reattempt flow is currently canonical in the web routes (Discord reattempt UI is commented out).

## Actors

- Runner: tournament participant executing runs from Discord private threads.
- Tournament owner: privileged Discord user who creates/configures tournaments.
- Tournament admin/mod: users/roles granted via `AsyncTournamentPermissions` and used for moderation/review tasks.
- System automation: scheduled loops for timeout enforcement and score recalculation.

## Data Model Overview

Core entities and relationships:

- `AsyncTournament`: top-level tournament container bound to one Discord channel (`channel_id` is unique).
- `AsyncTournamentPermalinkPool`: logical pool of seeds (preset-backed).
- `AsyncTournamentPermalink`: individual seed URL (+ optional notes, par-time metadata).
- `AsyncTournamentRace`: one run attempt (Discord thread-backed async run or live-race-linked record).
- `AsyncTournamentPermissions`: per-user/per-role admin/mod grants.
- `AsyncTournamentWhitelist`: explicit exceptions to account-age gate.
- `AsyncTournamentLiveRace`: RT.gg live race mapping for qualifier episodes.
- `AsyncTournamentAuditLog`: immutable action log for key events.

## Discord Workflow (End-to-End)

### 1) Tournament creation

1. Owner executes `/async create` in a target channel.
2. Bot creates `AsyncTournament` with owner/guild/channel binding.
3. Bot parses `permalinks` argument (`pool,preset,count` rows separated by `;`).
4. For each row, bot creates pool and generates seed permalinks through ALTTPR preset generator.
5. Bot posts tournament embed with persistent `AsyncTournamentView` buttons.

### 2) Runner starts a new run

1. Runner clicks “Start new async run”.
2. Validation gates:
   - Channel must map to active `AsyncTournament`.
   - Discord account age must be older than tournament-created minus 7 days, unless user is in whitelist.
   - Runner must have linked RT.gg account (`Users.rtgg_id`).
   - Runner must still have eligible pool slots (`runs_per_pool`).
3. Bot shows confirmation view with pool selector and explicit point-of-no-return prompt.
4. On confirm:
   - Race uniqueness checks prevent multiple active races per runner.
   - Private Discord thread is created.
   - Eligible permalink is selected from chosen pool via balancing logic.
   - `AsyncTournamentRace` is inserted with `status=pending`, `thread_open_time`, and chosen permalink.
   - Audit log entry is written.
   - Runner is added to thread and receives ready/start instructions.

### 3) Pending run to active run

1. Runner clicks “Ready (start countdown)” in race thread.
2. Validation:
   - Caller must be race owner.
   - Race must be in `pending` state.
3. Bot transitions race to `in_progress`, logs audit events, sends 10-second countdown, posts GO message, records `start_time`.

### 4) Run completion / forfeit

Completion path:

1. Runner clicks “Finish” or uses `/async done`.
2. Validation requires race owner and `status=in_progress`.
3. Bot sets `end_time`, marks `status=finished`, logs audit event.
4. Bot prompts for post-run submission:
   - Default customization: VOD URL + optional runner notes.
   - `gmpmt2023` customization: collection rate + IGT modal.

Forfeit path:

1. Runner clicks forfeit button and confirms in modal view.
2. Validation requires race owner and race status in `pending|in_progress`.
3. Bot sets `status=forfeit`, writes audit event, disables controls.

### 5) Background enforcement

Two 60-second loops enforce race hygiene:

- Pending timeout loop:
  - If no custom timeout exists, initializes `thread_timeout_time = thread_open_time + 20 minutes`.
  - Warns at T-10 minutes.
  - Auto-forfeits at timeout and logs `timeout_forfeit`.

- In-progress timeout loop:
  - Auto-forfeits races exceeding 12 hours from `start_time`.
  - Logs `timeout_forfeit`.

### 6) Scoring + leaderboard

Hourly loop for active tournaments:

1. `calculate_async_tournament(...)` iterates pools/permalinks.
2. `calculate_permalink_par(...)` computes par as average of up to top 5 finished times.
3. Score formula is bounded percentage-of-par:
   - `max(0, min(105, (2 - elapsed/par) * 100))`
4. Finished runs get computed scores; forfeits/disqualifications score 0.
5. Leaderboard cache key is invalidated.
6. `get_leaderboard(...)` rebuilds per-user pool-aligned race matrix and sorts by average score descending.

## Permission Model

- Owner-only commands (temporary safeguard): create, addseed, repost, permissions.
- Tournament admin/mod checks are resolved by:
  - Explicit `AsyncTournamentPermissions` user entries, then
  - Discord member role IDs mapped to permission rows.
- Admin/mod-gated operations include timeout extension, score recalc, live race recording, and web review queue actions.

## Web-Coupled Workflow (Scattered Module Surface)

Although race execution is Discord-first, review/operations are split with API/web routes:

- Review queue and individual race review pages.
- Review claim/writeback (`reviewed_by`, `review_status`, `reviewer_notes`, `reviewed_at`).
- Leaderboard and player/pool/permalink views with access controls.
- Reattempt flow is web route based (`/races/<id>/reattempt` + POST submit).
- JSON endpoints expose tournaments/races/pools/permalinks/leaderboard.

## State Transitions

`AsyncTournamentRace.status` transitions used by Discord flow:

- `pending` → `in_progress` (runner starts)
- `in_progress` → `finished` (runner finishes)
- `pending|in_progress` → `forfeit` (runner/system timeout)
- Live-race recording path may set `finished|forfeit|disqualified`

Related review state (`review_status`) is managed in web review flow and is independent from core run-status transitions.

## Operational Notes

- Persistent views are re-registered in cog `on_ready` to survive bot reconnects/restarts.
- Audit logging is broad and event-oriented (thread creation, ready, countdown, start, finish, timeout, extension, forfeit).
- Several reattempt-related Discord UI blocks are intentionally commented; current canonical reattempt interaction is web-based.
- There is a TODO in pool lookup noting desired stronger uniqueness/selection guarantees.
