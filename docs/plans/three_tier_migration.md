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

## Status (2026-06-26)

Branch `three-tier-migration`. Each phase below shipped behavior-preserving, with the
bot importing cleanly and the test suite green (started at 232 characterization tests;
now **294 passing**). Every migrated vertical follows the same shape: a Tier-3
repository (pure Tortoise CRUD), a Tier-2 service (validation/orchestration, raising
`ValueError`/`PermissionError` surfaced per surface), thin presentation, plus a service
unit test and a repository round-trip test.

**Done:**
- **Phase 0** — foundation (tier packages, `_notify` queue + gateways, `AuditService`,
  import-linter contracts (warn-only) + CI + pre-commit, `.claude` hook scripts, pytest).
- **Phase 1** — the Great Relocation: the four `alttprbot_*` surfaces folded into
  `alttprbot/presentation/{discord,audit,racetime,api}`, `alttprgen` → `services/seedgen`.
- **Phase 2** — `daily` (DailyRepository/Service).
- **Phase 3** — `discord_servers` (DiscordServerRepository/Service); shared `presets`
  (PresetRepository + PresetNamespaceRepository + PresetService) consumed by the API
  blueprint and the seed generator.
- **Phase 4** — canonical GuildConfigRepository + GuildConfigService (UI-free via a
  resolver callback). The `Guild.config_*` monkey-patch and legacy
  `alttprbot/database/config.py` remain as coexisting shims (same rows).
- **Phase 5** — RaceTime handler data access: SpoilerRace / RaceRoom (unlisted rooms +
  override whitelist) / TournamentResults repositories + services.
- **Phase 6** — seed-generation audit writes routed through `AuditService`.
- **Phase 7a** — tournament data-layer foundation: TournamentGamesRepository +
  TournamentResultsRepository, with the base `tournament/core.py` rewired through them.
- **Phase 8 — all 6 blueprints off direct ORM.** `tournament` (mass-assignment fixed
  via a TournamentGamesService allowlist), `triforcetexts`, `ranked_choice`, `racetime`
  (UserRepository/Service account link+merge, AuthorizationService), and
  **asynctournament** (~710 lines → AsyncTournamentRepository + AsyncTournamentService;
  pydantic serialization + race review/reattempt writes; `checks.is_async_tournament_user`
  authz and `util.get_leaderboard` left in place). **No `api/blueprints/*` imports
  `alttprbot.models` — the blueprint burn-down is complete.**

- **Cog burn-down (all active, non-deprecated cogs)** — nickname, generator, inquiry,
  racetime_tools, tournament, audit, rankedchoice, racer_verification, the api
  app-factory/auth, the shared `checks.is_async_tournament_user` (permission ORM via
  service; discord guild/member resolution stays), the `Guild.config_*` monkey-patch
  (now delegates to GuildConfigService), and `racetime/misc/konot.py` are all off direct
  ORM. Driven by a parallel analysis workflow (one agent per file) and verified by a
  parallel adversarial behavior-preservation review (one fix landed: KONOT.resume must
  re-raise DoesNotExist for the non-KONOT-room control-flow path).

- **asynctournament discord cog (~1289 lines, 8 models, ~60 ops)** — done: new
  AsyncTournamentPermissions/LiveRace repos+services, AsyncTournamentRepository/Service
  extended (channel/thread lookups, create flows, persistence wrappers), all 11 audit
  writes via `AuditService.record_async_event`; UI Views/threads/embeds stay in the cog.
  Driven by a per-model spec workflow + an adversarial review workflow (which caught and
  forced a fix to a scripted-transform regex over-match). **No non-deprecated presentation
  file imports `alttprbot.models` — the active cog burn-down is complete.**

**Remaining (large, incremental-by-design — tackle as focused, reviewed passes):**
- **Deprecated cogs** — `admin` (disabled in bot startup), `smmulti` (multiworld
  retirement), `voicerole` (behind the role-assignment flag): still import models but are
  slated for removal by their own deprecation plans; migrate only if kept.
- **Phase 7 full tournament decomposition** — orchestrator/presenter/gateway + config
  IDs, relocate `tournament/` → `services/tournament/`, migrate the 20+ subclasses one
  per PR. These classes are untested and drive live tournaments; do not rush.
- **Phase 9 util cleanup** — `util/{asynctournament,rankedchoice,triforce_text}.py` mix
  model navigation, STV/scoring computation, and discord embed rendering; split the
  discord rendering into presentation and the computation into services (entangled with
  their cog/blueprint consumers).
- **Phase 10** — retire the guild-config monkey-patch + legacy `database/config.py`
  (after audit/misc/tournament callers migrate), then flip import-linter contracts to
  blocking and set `SAHASRAHBOT_HOOKS_ENFORCE=1`. Blocked until the above land (the
  presentation→models and service→presentation contracts still have open items).
