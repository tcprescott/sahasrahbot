# Plan: Migrate to Official `racetime-bot`

> Status: Implemented (offline) — live parity validation pending  
> Last updated: 2026-07-06  
> Scope: Replace custom fork (`tcprescott/racetime-bot@48afdd4691f0f329eebb5dd33b1cbcf42921e980`) with official upstream (`racetimegg/racetime-bot` 2.3.0) while preserving 1:1 runtime behavior.

## Implementation Outcome (2026-07-06)

The dependency cutover and code reconciliation are done and verified offline (521 tests, import-linter
5/0, dependency guard). The presentation-layer paths below predate the three-tier fold-in; the code now
lives under `alttprbot/presentation/racetime/`, `alttprbot/presentation/api/`, and
`alttprbot/services/tournament/` + `alttprbot/presentation/discord/tournament/`.

- **Dependency:** `poetry.lock` regenerated so `racetime-bot = "^2.3.0"` resolves to the PyPI wheel
  (deps `aiohttp/asgiref/requests/websockets`) instead of the fork URL archive; `websockets` resolves to
  16.0.
- **Bot core** (`alttprbot/presentation/racetime/core.py`): `create_handler` now builds a
  `websockets.connect(...)` connection (upstream `RaceHandler` transport) with the `<14`/`≥14`
  header-kwarg BC branch; shutdown ws-close made API-safe.
- **Handler** (`alttprbot/presentation/racetime/handlers/core.py`): dropped the fork-only `bot=` kwarg
  from the `super().__init__` call; re-added `chat_message` (`ex_*`+`ex2_*`, case-preserving), `edit`,
  and a `handle()` override that keeps concurrent per-message consume.
- **New helper:** `alttprbot/presentation/racetime/util/arg_parser.py` (ported from the fork's dropped
  `racetime_bot.utils`).
- **Unchanged (byte-identical upstream):** `msg_actions`, `monitor_cmd`, `can_monitor`, and the
  `compat.py` handler-registry shim.
- **Reconnect model:** now upstream's recreation-based recovery (connection ends → `refresh_races`
  recreates), rather than the fork's in-place reconnect.

Remaining: live parity validation against racetime.gg (needs per-category OAuth creds) per the
Phase 0 checklist.

## 1. Goal

Move SahasrahBot from the forked `racetime-bot` package to the officially supported upstream package with **no user-visible regression** across:

- Race room discovery and handler attachment
- Chat command handling (including `ex2_*` command forms)
- Tournament room creation and control workflows
- API-injected RaceTime commands
- Unlisted room resume and reconnect behavior

## 2. In Scope

- Dependency cutover in project configuration
- RaceTime bot core reconciliation (`alttprbot_racetime/core.py`)
- Race handler contract reconciliation (`alttprbot_racetime/handlers/*.py`)
- Cross-surface integrations that assume fork internals:
  - `alttprbot_api/blueprints/racetime.py`
  - `alttprbot/tournament/*.py`
  - `alttprbot_racetime/misc/konot.py`

## 3. Out of Scope

- New RaceTime feature additions
- Tournament business-rule changes
- Discord UX/content changes unrelated to migration
- Architecture redesign of startup supervision beyond migration-required compatibility

## 4. Baseline Delta Summary (Fork vs Official)

Critical differences that require reconciliation:

1. **WebSocket model changed**  
   - Fork handler uses `aiohttp` websocket object (`send_json`, reconnect loop).  
   - Official handler uses `websockets` connection context (`self.conn`, `self.ws.send(json.dumps(...))`).

2. **Handler constructor contract changed**  
   - Fork handler created with `bot=self` and keeps `self.bot`.  
   - Official handler no longer carries bot reference by default.

3. **Handler registry/task shape changed**  
   - Current app expects `racetime_bot.handlers.get(...).handler`.  
   - Official bot stores task objects directly.

4. **Command parser behavior changed**  
   - Fork supports `ex2_*` parser (`arg_parser`) and mixed positional/keyword parsing.  
   - Official package is primarily `ex_*` command handling.

5. **Fork-only convenience methods are used by app code**  
   - `startrace(...)`, `get_team(...)`, `join_race_room(...)` flows and response structures are consumed in tournament and KONOT paths.

## 5. Ownership Model (Single-Developer Role Hats)

| Role Hat | Owner | Responsibility |
|---|---|---|
| Delivery | Thomas Prescott | Implement code migration tasks and flags |
| Validation | Thomas Prescott | Execute parity checks and capture evidence |
| Rollback | Thomas Prescott | Trigger/revert cutover based on defined gates |

## 6. Implementation Phases and Estimates

## Phase 0 — Parity Contract Capture (0.5–1 day)

Deliverables:

- Baseline behavior matrix for existing forked runtime:
  - command outcomes
  - room lifecycle transitions
  - tournament room operations
  - API chat-command injection behavior
  - unlisted-room recovery
- Evidence template for side-by-side pre/post migration checks

Exit criteria:

- Baseline checks are documented and reproducible.

## Phase 1 — Compatibility Adapter Layer (1.5–2.5 days)

Deliverables:

- Add a local RaceTime compatibility layer in `alttprbot_racetime` that normalizes:
  - handler/task lookup API
  - command dispatch entry points
  - bot utility operations used by tournaments (`startrace`, `get_team`)
- Introduce migration flag for selecting fork-compatible vs upstream-backed implementation during rollout

Exit criteria:

- Existing internal call sites compile against adapter without behavior change.

## Phase 2 — Core Bot Migration (1–2 days)

Deliverables:

- Reconcile `SahasrahBotRaceTimeBot` to official upstream connection/auth lifecycle
- Preserve existing app policies:
  - category-specific credentials
  - retry and auth-failure handling
  - unlisted room rejoin logic
  - category-level isolation

Exit criteria:

- Bot starts in debug category mode and attaches to rooms without runtime exceptions.

## Phase 3 — Handler Contract Migration (2–3 days)

Deliverables:

- Update `SahasrahBotCoreHandler` and all category handlers to official handler transport/constructor contract
- Preserve:
  - all `ex_*` commands
  - `ex2_newrace` behavior in `handlers/alttpr.py`
  - lock/monitor/tournament gating behavior
  - spoiler countdown and status transitions

Exit criteria:

- Command parity checks pass on debug category.

## Phase 4 — Integration Reconciliation (1–2 days)

Deliverables:

- Update API and tournament integrations that assume fork internals:
  - `alttprbot_api/blueprints/racetime.py` handler resolution/dispatch
  - `alttprbot/tournament/*` calls to `startrace/get_team`
  - `alttprbot_racetime/misc/konot.py` room creation path

Exit criteria:

- API command injection and tournament room operations pass parity checks.

## Phase 5 — Dependency Cutover and Staged Rollout (1–1.5 days)

Deliverables:

- Replace fork dependency in `pyproject.toml` with official package
- Run staged rollout:
  1. debug-only category
  2. one production pilot category
  3. remaining categories in batches

Exit criteria:

- Full category set passes smoke/parity checks.

## Total Estimated Effort

- **7–12 engineering days** (serial execution, single-owner model)

## 7. Reconciliation Matrix (Must Keep 1:1)

| Surface | Current Behavior | Required Migration Outcome |
|---|---|---|
| Handler lookup | API path expects `.handlers.get(name).handler` | Adapter preserves stable lookup shape for app code |
| Chat commands | `ex_*` and `ex2_*` work, including kwarg parsing | Same commands and parsing semantics preserved |
| Tournament controls | `!tournamentrace`, monitor-gated actions, seeded DMs | No changes in permissions, timing, or output |
| Race info updates | `set_bot_raceinfo(...)` used broadly | Same race info content and timing |
| Unlisted room recovery | DB-backed `RTGGUnlistedRooms` resume | Same resume/delete semantics |
| KONOT progression | Room chaining via bot room creation | Same elimination and next-room behavior |
| API injected command | POST endpoint executes synthetic chat message | Same dispatch path and success semantics |

## 8. Gate Checks (Pass/Fail)

## Gate A — Debug Category Parity

- Commands: `!help`, seed roll, lock/unlock, cancel
- Spoiler path and countdown output
- Handler attach/detach across room status transitions

## Gate B — Tournament Parity

- `startrace`-based room creation
- `!tournamentrace` workflow
- monitor and entrant permissions
- direct-message behavior and race info updates

## Gate C — API + Recovery Parity

- `/api/racetime/cmd` executes successfully
- unlisted room persistence/resume behavior works after restart
- KONOT segment progression remains intact

## Gate D — Production Staged Rollout

- Pilot category stable for soak window
- no category-specific regressions in batch enablement

## 9. Rollback Plan

Rollback triggers:

- command handling failures
- handler resolution failures from API/tournament call sites
- room attach/recovery regressions

Rollback actions:

1. Revert dependency to fork commit pin
2. Disable upstream migration flag path
3. Restart RaceTime subsystem and re-run baseline smoke checks
4. Log incident + failed gate evidence before next attempt

## 10. Execution Sequence (Recommended)

1. Implement Phase 0 baseline matrix and evidence template
2. Build adapter layer before touching handler command logic
3. Migrate core bot transport/lifecycle
4. Migrate handlers while preserving command parity
5. Reconcile API/tournament/KONOT call sites
6. Cut dependency and execute staged rollout gates
7. Remove temporary migration shims after stable soak

## 11. Completion Definition

Migration is complete when:

- Official `racetime-bot` is the runtime dependency
- All Gate A–D checks are green
- No active compatibility shim is required for fork-only internals
- Context docs and operational notes reflect final runtime state
