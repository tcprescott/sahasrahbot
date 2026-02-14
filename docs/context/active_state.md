# Active State

> Last updated: 2026-02-13

## Current Focus

- **Modernization Program Bootstrap (Phase 0)**: Executing program bootstrap per [docs/plans/modernization_meta_execution_plan_ai_accelerated.md](../plans/modernization_meta_execution_plan_ai_accelerated.md) — tracker structure, evidence templates, and flag inventory complete. Next: confirm single-owner role mapping (delivery/validation/rollback hats) and run first compatibility evidence cycle.
- **Discord Bot Refactor**: Implementing the modernization plan defined in [docs/plans/discord_refactor.md](../plans/discord_refactor.md).
- **Documentation Sprint**: Generating comprehensive developer documentation from codebase analysis.
- **Single-Developer Workflow Mode**: Plan and execute workstreams serially with explicit priority ordering, minimal parallel WIP, and evidence-first gates to reduce context-switch overhead.

## Known Issues

- Secrets historically lived in `config.py`; configuration is environment-driven via `config.py` constants sourced from environment variables, but any previously exposed tokens/keys should be considered compromised and rotated.
- Cross-layer dependency: `alttprbot/database/config.py` imports `CACHE` from `alttprbot_discord.util.guild_config`.
- Many tournament handlers in `TOURNAMENT_DATA` registry are commented out between seasons.
- The `reverify_racer` background task in the `racer_verification` cog is currently disabled via comment.
- The `schedule` and `user` blueprints in the web API are DEBUG-only stubs.
- **Architecture Debt**: `guild_config` monkey-patching and name-based channel config need removal.
- **Operational Validation Pending**: Daily challenge retry/thread-failure hardening shipped, but production compatibility evidence capture is still pending.
- **Runtime Security Debt**: `APP_SECRET_KEY` defaults to empty string.
- **Startup Reliability Follow-up**: coordinated graceful shutdown is now implemented, but subsystem-level startup policies (strict fail-fast vs degraded mode) still need explicit owner-confirmed criteria.
- **RaceTime Config Fragility**: per-category OAuth client keys are dynamically resolved from attribute names, making failures import/runtime-coupled.
- **Auth Stack Follow-up**: Authlib is now the only API Discord OAuth path; post-cutover hardening and compatibility evidence collection remain open. Behavior contract documented in `docs/design/discord_oauth_behavior_contract.md`.
- **Docs Tooling Drift**: `update_docs.py` writes legacy docs targets under `docs/` root instead of `docs/user-guide/`.

## Recent Completions

- Audit of Discord bot domain completed; technical debt identified.
- Codebase analysis and documentation generation (2026-02-11).
- Existing end-user docs relocated from `docs/` root to `docs/user-guide/`.
- Removed accidental interim configuration abstraction layer and retained env-driven `config.py` settings (2026-02-12).
- API and web frontend operation documentation completed with separate JSON endpoint and frontend route maps (2026-02-12).
- Granular parallel codebase audit completed to identify context documentation drift and unresolved intent assumptions (2026-02-12).
- Reconciled legacy overlapping RaceTime/Web API design doc to RaceTime-only scope with canonical links to split API/frontend docs (2026-02-12).
- Added async tournament Discord workflow design documentation with owner-verified intent for eligibility, timeout, permissions, and reattempt policy (2026-02-12).
- Added reusable Component Interrogation Agent mode assets (GitHub mode prompt, checklist, and example runbook) for component-scoped intent-first analysis (2026-02-12).
- Wired Component Interrogation Mode into `.github/copilot-instructions.md` with trigger phrases and mandatory interrogation rules (2026-02-12).
- Added focused Discord daily challenge component audit documentation (`docs/design/discord_daily_challenge_audit.md`) with owner-confirmed polling/channel/thread policy intent and resilience findings (2026-02-12).
- Completed non-async tournament module audit and published reliability-first architecture/reporting docs (`design/tournament_module_non_async_audit.md`, `guides/tournament_module_runbook.md`) (2026-02-12).
- Drafted concrete config-driven seasonal tournament registry migration design (`design/tournament_registry_config_design.md`) to replace code-comment toggles with validated runtime config (2026-02-12).
- Completed cross-surface seed generation component audit (`design/seed_generation_component_audit.md`) covering Discord, RaceTime, and API generation paths with owner-confirmed policy intent for spoiler control and standardized provider retries/timeouts (2026-02-12).
- Drafted concrete shared seed-provider reliability contract (`design/seed_provider_reliability_contract.md`) with owner-confirmed defaults (60s timeout, 3-attempt exponential retry, mandatory audit parity, direct provider error messaging) (2026-02-12).
- Completed role-assignment component deprecation audit (`design/discord_role_assignment_deprecation_audit.md`) with owner-confirmed scope/timeline/data policy (reaction + voice roles, soft deprecate now, remove next release, archive then drop) (2026-02-12).
- Completed multiworld Discord component deprecation audit (`design/discord_multiworld_deprecation_audit.md`) with owner-confirmed policy (soft deprecate now, remove next release, drop multiworld tables without archival, no replacement path) (2026-02-12).
- Drafted anonymous telemetry and feature-usage rollout plan (`plans/anonymous_telemetry_user_stats_plan.md`) covering privacy policy, event taxonomy, storage model, and phased implementation (2026-02-12).
- Drafted overarching 2026–2027 modernization vision (`plans/application_modernization_vision_2026_2027.md`) to align security, observability, velocity, and risk-first migration sequencing across existing refactor plans (2026-02-12).
- Reclassified plan-like execution content from design docs into dedicated plan docs for deprecation and migration rollouts (`plans/discord_role_assignment_deprecation_removal_plan.md`, `plans/discord_multiworld_deprecation_removal_plan.md`, `plans/seed_provider_reliability_implementation_plan.md`, `plans/tournament_registry_config_rollout_plan.md`) (2026-02-12).
- Scrutinized and strengthened the umbrella modernization roadmap (`plans/application_modernization_vision_2026_2027.md`) with explicit non-goals, workstream dependency mapping, phase exit criteria, gate-evidence requirements, top-risk mitigations, and owner-confirmation decision questions (2026-02-12).
- Captured owner confirmation decisions for modernization defaults in the umbrella roadmap (degraded startup allowance, 60-day telemetry retention baseline, 8-week deprecation communication window, initial compatibility gate workflows) (2026-02-12).
- Expanded and wired the concrete modernization compatibility workflow baseline (8 workflows) from umbrella roadmap into dependent rollout plans (seed provider reliability, tournament registry config rollout, role deprecation/removal, multiworld deprecation/removal) (2026-02-12).
- Added executable compatibility gate validation runbook (`plans/modernization_compatibility_gate_validation_runbook.md`) with per-workflow tasks, evidence packet template, and rollback verification checklist for bi-weekly gate reviews (2026-02-12).
- Reconciled direct runtime dependency declarations in `pyproject.toml` (added missing direct imports, removed unused `twitchapi`) and added dependency declaration guard script (`helpers/check_dependency_declarations.py`) (2026-02-12).
- Added phased OAuth modernization plan (`plans/authlib_discord_oauth_migration_plan.md`) and linked it into the umbrella modernization roadmap (2026-02-12).
- Added AI-accelerated modernization meta execution plan (`plans/modernization_meta_execution_plan_ai_accelerated.md`) to sequence subordinate modernization plans into phased delivery, validation, and governance lanes (2026-02-12).
- **WS3: GuildConfigService Pilot Migration** — Created `GuildConfigService` abstraction and migrated `daily.py` cog with backward-compatible channel name→ID resolution helper. Monkey-patch path remains intact for non-migrated cogs. Migration notes in `docs/plans/guild_config_service_migration_notes.md` (2026-02-12).
- **Completed Phase 1 of seed provider reliability contract implementation**: implemented shared provider execution wrapper with 60s timeout and 3-attempt retry policy, normalized exception taxonomy, canonical provider response object, and representative SMDash adapter with validation (2026-02-12).
- **Completed Phase 0/1 of tournament registry config rollout** (`plans/tournament_registry_config_rollout_plan.md`): Added `AVAILABLE_TOURNAMENT_HANDLERS` catalog, `config/tournaments.yaml` schema, `registry_loader.py` with validation, dual-path runtime switch with `TOURNAMENT_CONFIG_ENABLED` flag, startup logging, and validation tooling (`helpers/validate_tournament_config.py`, `docs/guides/tournament_registry_config_guide.md`) (2026-02-12).
- **Implemented MVP anonymous telemetry pipeline** with privacy-preserving storage, no-op/DB-backed services, bounded queue, fail-open behavior, retention purge helper, usage report helper, and initial Discord generator instrumentation (2026-02-12).
- **WS4 Phase A/B: Discord Multiworld Deprecation** — Completed soft deprecation messaging and functional removal for multiworld commands. Phase A added deprecation notices to `smmulti` and `doorsmw` commands. Phase B commented out extension loads in `bot.py` to prevent command registration. Commands no longer callable; non-multiworld flows unaffected (2026-02-12).
- **Implemented Phase A/B of Discord role-assignment deprecation (WS4):** Added deprecation messaging to all reaction-role and voice-role command surfaces, implemented runtime disablement flag `DISCORD_ROLE_ASSIGNMENT_ENABLED` (default True for backward compatibility), added conditional extension loading, preserved startup and non-role command behavior. Rollback procedure and compatibility validation documented in `docs/guides/discord_role_assignment_deprecation_runbook.md` (2026-02-12).
- **Phase 0 Bootstrap (Week 0–1) completed:** Created modernization execution tracker (`plans/modernization_execution_tracker.md`) mapping WS1–WS5 workstreams to gate milestones with 30/60/90-day targets; added compatibility evidence packet template (`guides/compatibility_evidence_packet_template.md`) aligned to validation runbook; added feature-flag inventory (`guides/feature_flag_inventory.md`) with single-owner + sunset enforcement; updated MASTER_INDEX.md and active_state.md (2026-02-12).
- Aligned modernization tracker and umbrella roadmap workflow language to a single-developer operating model (single-owner role hats, serial high-risk execution, explicit WIP limits) (2026-02-12).
- **Completed Discord OAuth Authlib cutover (WS1):** removed Quart-Discord runtime usage and dual-path selector, migrated all API blueprints/decorators to Authlib helper imports, and removed legacy OAuth dependencies from `pyproject.toml` (2026-02-12).
- Documented import-backed root config contract in `docs/guides/config_constants_inventory.md`, including 40 statically-read constants and dynamic RaceTime credential key pattern; aligned `config.py.example` placeholders to match static runtime usage (2026-02-12).
- Added fail-fast startup config contract validation via `alttprbot/util/config_contract.py`, wired in `sahasrahbot.py` before RaceTime bot import, plus standalone checker `helpers/validate_runtime_config.py` for local/CI preflight (2026-02-12).
- Migrated root runtime configuration provider to `pydantic-settings` in `config.py` while preserving module-level `config.<KEY>` compatibility, dynamic uppercase env passthrough, and existing validation helper flow (2026-02-12).
- Added legacy-config conversion helper `helpers/convert_legacy_config_to_env.py` to transform historical Python constant config files into dotenv format for `pydantic-settings` adoption (2026-02-12).
- Removed Google Sheets integration from tournament runtime flow (race recording task, sheet credential utility, and Google dependencies/config keys) and retained database-only result tracking (2026-02-12).
- Drafted implementation-ready migration plan for replacing the forked RaceTime SDK dependency with official upstream package while preserving 1:1 behavior across RaceTime handlers, tournament integrations, API-injected commands, and unlisted-room recovery (`plans/racetime_bot_official_migration_plan.md`) (2026-02-12).
- Started execution of RaceTime SDK migration: added Phase 0 parity checklist artifact, introduced RaceTime handler compatibility helper, refactored RaceTime bot core toward official-sdk-compatible transport/handler tracking contract, updated API command handler lookup to compatibility helper, and switched `pyproject.toml` dependency to official `racetime-bot` package (2026-02-12).
- Implemented centralized signal-aware graceful shutdown for bot runtime: entrypoint now coordinates SIGINT/SIGTERM shutdown, explicitly stops Discord/Audit/RaceTime subsystems, cancels service tasks safely, and closes database connections to reduce termination-time exception noise (2026-02-13).
- Fixed Discord daily challenge reliability bugs in `alttprbot_discord/cogs/daily.py`: corrected dedupe DB check, added bounded retries for daily hash/seed retrieval, isolated thread creation from send failures, and added safer hash/thread-name handling (2026-02-13).
- Hardened Discord/Audit background task loops against crash-stop behavior: added guarded exception boundaries and loop-level restart handlers in `alttprbot_discord/cogs/tournament.py`, `alttprbot_discord/cogs/daily.py`, `alttprbot_discord/cogs/racer_verification.py`, and `alttprbot_audit/cogs/audit.py` so transient/unhandled exceptions no longer require bot restart (2026-02-13).
- Completed web frontend analysis and published SPA redesign architecture document (`docs/design/web_frontend_spa_redesign.md`) covering React 18 + Tailwind CSS clean-break replacement, full API contract for 40+ endpoints, SPA route map, component tree, responsive design strategy, and backend integration pattern (2026-02-13).
- Eliminated legacy raw-SQL helper usage from application database access modules by migrating `alttprbot/database/*.py` queries/writes to Tortoise model operations with equivalent dict-shaped outputs for existing call sites, and removed obsolete `alttprbot/util/orm.py` (2026-02-13).

## Upcoming Work

1. Record single-developer role mapping (same owner across delivery, validation, and rollback) per workstream in `plans/modernization_execution_tracker.md`.
2. Execute first full compatibility gate evidence cycle using `plans/modernization_compatibility_gate_validation_runbook.md` and publish baseline pass/fail matrix for the current single-owner model.
3. Monitor `GuildConfigService` pilot in `daily.py` and verify announcement reliability in production traffic.
4. Continue incremental cog migration to `GuildConfigService` (`tournament.py`, `misc.py`, `audit.py`).
5. Implement channel name→ID data migration script and rollout plan (Phase 3 of guild config modernization).
6. Integrate dependency declaration guard (`poetry run python helpers/check_dependency_declarations.py`) into CI when workflow scaffolding is enabled.
7. Define and document explicit startup supervision/failure strategy for multi-subsystem boot.
8. Complete Tournament Registry Config Rollout Phase 2: enable config-backed registry in production and validate over a full seasonal cycle.
9. Sequence remaining modernization backlog against `plans/application_modernization_vision_2026_2027.md` and enforce phase gate checks.
10. Start next bounded Phase 1 slices: telemetry service/table operationalization across surfaces and startup security validation checks.
11. Rotate/revoke any previously committed secrets and finish operational `.env` hardening.
12. Review and refine generated documentation, including `update_docs.py` target alignment with `docs/user-guide/`.
13. Create reusable AI task templates for audits, migrations, and compatibility evidence packets.
14. Validate production `.env`/environment completeness against the new `pydantic-settings` config surface before next deployment restart.
15. Validate RaceTime migration runtime by installing updated dependencies and running targeted startup/smoke checks for RaceTime bot initialization, API command lookup path, and tournament `startrace/get_team` call chains.

## Open Why Questions

- Why should insecure OAuth transport be enabled outside local development?
- Why is an empty `APP_SECRET_KEY` acceptable in any non-test environment?
- Why is startup task supervision intentionally best-effort instead of fail-fast on subsystem startup errors?
- Why is config cache ownership split across legacy database and Discord utility layers?
- Why are seasonal tournament/racetime toggles controlled through commented registries rather than explicit configuration?
