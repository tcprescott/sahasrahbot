# Active State

> Last updated: 2026-02-11

## Current Focus

- **Documentation Sprint**: Generating comprehensive developer documentation from codebase analysis.
- No active feature development at this time.

## Known Issues

- `config.py` contains hardcoded secrets (dev credentials) rather than using environment variables or a secrets manager.
- Legacy database layer (`alttprbot/database/`) coexists with Tortoise ORM models — dual-pattern creates confusion.
- Cross-layer dependency: `alttprbot/database/config.py` imports `CACHE` from `alttprbot_discord.util.guild_config`.
- Many tournament handlers in `TOURNAMENT_DATA` registry are commented out between seasons.
- The `reverify_racer` background task in the `racer_verification` cog is currently disabled via comment.
- The `schedule` and `user` blueprints in the web API are DEBUG-only stubs.
- Several deprecated racetime commands remain (e.g., `!race`, `!noqsrace` in the ALTTPR handler).

## Recent Completions

- Codebase analysis and documentation generation (2026-02-11).
- Existing end-user docs relocated from `docs/` root to `docs/user-guide/`.

## Upcoming Work

- Review and refine generated documentation.
- Consider migrating `config.py` secrets to environment variables.
- Consider consolidating legacy database modules to Tortoise ORM.
- Evaluate removing deprecated racetime commands.
