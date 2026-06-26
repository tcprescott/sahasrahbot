# Three-Tier Architecture Migration

> Execution plan for migrating SahasrahBot to a strict three-tier architecture
> inside a single `alttprbot/` package. Canonical layering rules:
> [architecture-layers.md](../architecture-layers.md). Reference model: the
> sibling SGLMan project.

## Goal

A single `alttprbot/` package whose directory structure mirrors the tiers; every
DB access flows through a repository; all business logic lives in services; the
four presentation surfaces are thin adapters; the service/repository tiers never
import `discord`, `racetime_bot`, `quart`, or `alttprbot.presentation`; boundaries
enforced by import-linter and Claude Code hooks. No behavior changes, no schema
changes, single-process model preserved.

## Target layout

```
alttprbot/
  presentation/{discord,audit,racetime,api}/   # Tier 1 (folded-in alttprbot_* surfaces)
  services/                                     # Tier 2 — business; seedgen/ + tournament/ subpackages
    _notify/                                     #   fire-and-forget queue + gateways
    audit_service.py
  repositories/                                 # Tier 3 — pure data access
  models/                                       # Tier 4 — unchanged (Aerich/schema stable)
  util/                                         # shared pure helpers
  database/                                     # legacy raw SQL — deleted in the final phase
config.py            # root
sahasrahbot.py       # entry point (root)
tests/               # pytest + pytest-asyncio
```

## Conventions

- **Repository:** `<name>_repository.py` / `<Name>Repository`; static async Tortoise
  CRUD; returns models; no business logic/UI; exported from `repositories/__init__.py`.
- **Service:** `<name>_service.py` / `<Name>Service`; per-call instance, injects repos
  in `__init__`; validation/authz/orchestration/audit/notify; raises
  `ValueError`/`PermissionError`/`SahasrahBotException`; never imports
  discord/racetime_bot/quart/presentation; exported from `services/__init__.py`.
- **Presentation:** thin; calls services; renders results and catches errors per
  surface; no business logic; no `alttprbot.repositories`/`alttprbot.models` import.
- **Notifications:** `queue.enqueue(discord_gateway.get().send_dm(...))`; gateways
  registered inward by the presentation layer at startup.
- **Audit:** `AuditService` + `AuditActions` (`verb.object`), backed by existing models.

## Enforcement

- **import-linter** — `pyproject.toml` `[tool.importlinter]`; `poetry run lint-imports`;
  CI (`.github/workflows/lint.yml`) + pre-commit. Warn-only during migration
  (CI `continue-on-error`), flipped to blocking in the final phase.
- **Claude Code hooks** — `.claude/scripts/` wired by `.claude/settings.json`:
  `enforce_architecture.py` (PreToolUse), `enforce_no_orm_writes.py` +
  `check_layer_exports.py` (PostToolUse). Notification-only until
  `SAHASRAHBOT_HOOKS_ENFORCE=1` in the final phase.

## Phases

- **Phase 0 — Safety net & tooling.** pytest harness; import-linter (warn-only) + CI +
  pre-commit; Claude Code hook scripts (notification-only); empty `repositories/` +
  `services/` packages; `_notify` queue + gateways wired into `sahasrahbot.py`;
  `AuditService` + backing repos + a reference test; docs.
- **Phase 1 — The Great Relocation.** `git mv` the four surfaces into
  `alttprbot/presentation/` and `alttprgen` → `services/seedgen`; rewrite all imports
  + dynamic string refs + entry point + pyproject/aerich. Behavior-preserving; bot
  boots. Warn-only contracts now surface the real violation burn-down.
- **Phase 2 — Pilot A: `daily`** (`DailyRepository` + `DailyService`, rewire the cog).
- **Phase 3 — Pilot B: `discord_servers` + `presets`** (CRUD; first shared service
  consumed by both the API blueprint and the seedgen generator).
- **Phase 4 — Guild config consolidation** (one repo + one service; retire the
  monkey-patch and legacy `database/config.py`).
- **Phase 5 — RaceTime handler data access** (spoiler/unlisted/results repositories;
  gateways replace bot-singleton imports).
- **Phase 6 — Seed generation cleanup** (extract `AuditGeneratedGames` write + preset
  ORM into repositories; wrap in `SeedGenService`).
- **Phase 7 — Tournament decomposition** (orchestrator/presenter/repository; relocate
  `tournament/` → `services/tournament/`; hardcoded IDs → config; one subclass per PR).
- **Phase 8 — Remaining blueprints** (asynctournament sliced; ranked_choice;
  triforcetexts; tournament games — fix the `filter(**request.args)` mass-assignment).
- **Phase 9 — Util cleanup** (split mixed-concern util modules).
- **Phase 10 — Delete legacy & enforce.** Remove `alttprbot/database/` and the guild
  config monkey-patch; flip import-linter to blocking and set `SAHASRAHBOT_HOOKS_ENFORCE=1`.

## Non-goals & risks

- **Non-goals:** single event loop / single process preserved; no schema/Aerich changes
  in Phases 0–9; no behavior changes; SPA untouched; the config-driven tournament
  registry is extended, not replaced.
- **Risks:** no pre-existing test suite (Phase 0 mitigates); the Great Relocation's
  dynamic string references (extension loaders, blueprint/handler discovery) are the
  hazard — verify by booting in DEBUG and confirming every cog/blueprint/handler loads;
  tournament long tail (one-per-PR); coexistence drift (shared rows, remove old paths
  only after the last caller migrates); gateway registration ordering (enqueue, don't
  call synchronously).
