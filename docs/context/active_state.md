# Active State

> Last updated: 2026-02-12

## Current Focus

- **Discord Bot Refactor**: Implementing the modernization plan defined in [docs/plans/discord_refactor.md](../plans/discord_refactor.md).
- **Documentation Sprint**: Generating comprehensive developer documentation from codebase analysis.

## Known Issues

- Secrets historically lived in `config.py`; configuration is environment-driven via `config.py` constants sourced from environment variables, but any previously exposed tokens/keys should be considered compromised and rotated.
- Legacy database layer (`alttprbot/database/`) coexists with Tortoise ORM models — dual-pattern creates confusion.
- Cross-layer dependency: `alttprbot/database/config.py` imports `CACHE` from `alttprbot_discord.util.guild_config`.
- Many tournament handlers in `TOURNAMENT_DATA` registry are commented out between seasons.
- The `reverify_racer` background task in the `racer_verification` cog is currently disabled via comment.
- The `schedule` and `user` blueprints in the web API are DEBUG-only stubs.
- **Architecture Debt**: `guild_config` monkey-patching and name-based channel config need removal.
- **Resilience**: `daily` task lacks retries for API failures.
- **Runtime Security Debt**: `OAUTHLIB_INSECURE_TRANSPORT` is forced on in API startup and `APP_SECRET_KEY` defaults to empty string.
- **Startup Reliability Debt**: entrypoint startup uses unsupervised `create_task(...)` calls and `run_forever()` without centralized task failure handling.
- **RaceTime Config Fragility**: per-category OAuth client keys are dynamically resolved from attribute names, making failures import/runtime-coupled.
- **Dependency Drift**: runtime imports include `tenacity`, `python-dateutil` (`dateutil`), and `pytz`, but these are not declared in Poetry dependencies.
- **Auth Stack Modernization Pending**: `Quart-Discord` remains active runtime auth path while phased `Authlib` migration is planned.
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

## Upcoming Work

1. **Refactor `daily.py`**: Add `tenacity` retries and error handling (Phase 1).
2. **Create `GuildConfigService`**: Replace monkey-patching pattern (Phase 2).
3. **Channel ID Migration**: Convert config string names to IDs (Phase 3).
4. Review and refine generated documentation.
5. Rotate/revoke any previously committed secrets; operationalize `.env`-based configuration.
6. Integrate dependency declaration guard execution (`poetry run python helpers/check_dependency_declarations.py`) into CI when workflow scaffolding is enabled.
7. Define and document explicit startup failure/supervision strategy for multi-subsystem boot.
8. Implement tournament registry loader and `config/tournaments.yaml` rollout per `plans/tournament_registry_config_rollout_plan.md`.
9. Implement shared seed-provider reliability execution wrapper and adapter migration per `plans/seed_provider_reliability_implementation_plan.md`.
10. Implement role-assignment deprecation rollout per `plans/discord_role_assignment_deprecation_removal_plan.md`.
11. Implement multiworld Discord deprecation rollout per `plans/discord_multiworld_deprecation_removal_plan.md`.
12. Implement MVP anonymous telemetry pipeline per `plans/anonymous_telemetry_user_stats_plan.md` (ORM model, buffered telemetry service, Discord/RaceTime/API instrumentation, retention purge).
13. Sequence modernization backlog against the new umbrella roadmap in `plans/application_modernization_vision_2026_2027.md` and apply decision-gate checks per phase.
14. Execute first full compatibility gate evidence cycle using `plans/modernization_compatibility_gate_validation_runbook.md` and publish baseline pass/fail matrix with owners.

## Open Why Questions

- Why should insecure OAuth transport be enabled outside local development?
- Why is an empty `APP_SECRET_KEY` acceptable in any non-test environment?
- Why is startup task supervision intentionally best-effort instead of fail-fast on subsystem startup errors?
- Why is config cache ownership split across legacy database and Discord utility layers?
- Why are seasonal tournament/racetime toggles controlled through commented registries rather than explicit configuration?
