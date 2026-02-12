# Active State

> Last updated: 2026-02-12

## Current Focus

- **Discord Bot Refactor**: Implementing the modernization plan defined in [docs/plans/discord_refactor.md](../plans/discord_refactor.md).
- **Documentation Sprint**: Generating comprehensive developer documentation from codebase analysis.

## Known Issues

- Secrets historically lived in `config.py`; any previously exposed tokens/keys should be considered compromised and rotated.
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
- **Dependency Drift**: runtime imports include `tenacity` (and additional utility/runtime modules), but declarations should stay reconciled with actual usage.
- **Docs Tooling Drift**: `update_docs.py` writes legacy docs targets under `docs/` root instead of `docs/user-guide/`.

## Recent Completions

- Audit of Discord bot domain completed; technical debt identified.
- Codebase analysis and documentation generation (2026-02-11).
- Existing end-user docs relocated from `docs/` root to `docs/user-guide/`.
- Removed checked-in secrets from active configuration paths (2026-02-11).
- API and web frontend operation documentation completed with separate JSON endpoint and frontend route maps (2026-02-12).
- Granular parallel codebase audit completed to identify context documentation drift and unresolved intent assumptions (2026-02-12).
- Reconciled legacy overlapping RaceTime/Web API design doc to RaceTime-only scope with canonical links to split API/frontend docs (2026-02-12).

## Upcoming Work

1. **Refactor `daily.py`**: Add `tenacity` retries and error handling (Phase 1).
2. **Create `GuildConfigService`**: Replace monkey-patching pattern (Phase 2).
3. **Channel ID Migration**: Convert config string names to IDs (Phase 3).
4. Review and refine generated documentation.
5. Rotate/revoke any previously committed secrets; operationalize `.env`-based configuration.
6. Reconcile declared dependencies in `pyproject.toml` with actual runtime imports.
7. Define and document explicit startup failure/supervision strategy for multi-subsystem boot.

## Open Why Questions

- Why should insecure OAuth transport be enabled outside local development?
- Why is an empty `APP_SECRET_KEY` acceptable in any non-test environment?
- Why is startup task supervision intentionally best-effort instead of fail-fast on subsystem startup errors?
- Why is config cache ownership split across legacy database and Discord utility layers?
- Why are seasonal tournament/racetime toggles controlled through commented registries rather than explicit configuration?
