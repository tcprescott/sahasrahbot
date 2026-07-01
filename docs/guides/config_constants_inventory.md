# Config Constants Inventory

> Last updated: 2026-07-01

## Scope

This document captures constants expected from root `config.py`, based on import usage across the application.

- Source scan command: `poetry run python helpers/scan_config_constants.py`
- Scan result summary: 32 files with config constant reads, 34 unique constants
- Coverage: static constant attribute usage discovered in application code

## Expected Constants (Static Reads)

| Constant | References | Consuming files |
|---|---:|---|
| `ALTTPR_BASEURL` | 2 | `alttprbot/services/seedgen/generator.py`, `alttprbot/services/seedgen/seedclasses.py` |
| `ALTTPR_PASSWORD` | 1 | `alttprbot/services/seedgen/seedclasses.py` |
| `ALTTPR_USERNAME` | 1 | `alttprbot/services/seedgen/seedclasses.py` |
| `ALTTP_RANDOMIZER_SERVERS` | 2 | `alttprbot/presentation/discord/cogs/misc.py`, `alttprbot/presentation/discord/cogs/sgdailies.py` |
| `ALTTP_ROM` | 1 | `alttprbot/services/seedgen/randomizer/alttprdoor.py` |
| `APP_SECRET_KEY` | 1 | `alttprbot/presentation/web/web.py` |
| `APP_URL` | 7 | `alttprbot/presentation/discord/cogs/asynctournament.py`, `alttprbot/presentation/discord/cogs/nickname.py`, `alttprbot/presentation/discord/cogs/rankedchoice.py`, `alttprbot/presentation/discord/util/ranked_choice.py`, `alttprbot/presentation/web/blueprints/racetime.py`, `alttprbot/presentation/web/web.py`, `alttprbot/services/tournament/core.py` |
| `AUDIT_DISCORD_TOKEN` | 1 | `alttprbot/presentation/audit/bot.py` |
| `AWS_SPOILER_BUCKET_NAME` | 1 | `alttprbot/services/seedgen/spoilers.py` |
| `CC_TOURNAMENT_AUDIT_CHANNELS` | 1 | `alttprbot/presentation/discord/cogs/tournament.py` |
| `CC_TOURNAMENT_SERVERS` | 1 | `alttprbot/presentation/discord/cogs/tournament.py` |
| `DB_HOST` | 4 | `helpers/dbtest.py`, `helpers/fix_alttprqual_data.py`, `migrations/tortoise_config.py`, `sahasrahbot.py` |
| `DB_NAME` | 4 | `helpers/dbtest.py`, `helpers/fix_alttprqual_data.py`, `migrations/tortoise_config.py`, `sahasrahbot.py` |
| `DB_PASS` | 4 | `helpers/dbtest.py`, `helpers/fix_alttprqual_data.py`, `migrations/tortoise_config.py`, `sahasrahbot.py` |
| `DB_PORT` | 4 | `helpers/dbtest.py`, `helpers/fix_alttprqual_data.py`, `migrations/tortoise_config.py`, `sahasrahbot.py` |
| `DB_USER` | 4 | `helpers/dbtest.py`, `helpers/fix_alttprqual_data.py`, `migrations/tortoise_config.py`, `sahasrahbot.py` |
| `DEBUG` | 12 | `alttprbot/presentation/audit/bot.py`, `alttprbot/presentation/discord/bot.py`, `alttprbot/presentation/discord/cogs/asynctournament.py`, `alttprbot/presentation/discord/cogs/inquiry.py`, `alttprbot/presentation/discord/cogs/racer_verification.py`, `alttprbot/presentation/discord/cogs/tournament.py`, `alttprbot/presentation/racetime/config.py`, `alttprbot/presentation/web/web.py`, `alttprbot/services/async_tournament_scoring_service.py`, `alttprbot/services/tournament/registry.py`, `alttprbot/util/speedgaming.py`, `helpers/seed_test_fixtures.py` |
| `DISCORD_CLIENT_ID` | 1 | `alttprbot/presentation/web/web.py` |
| `DISCORD_CLIENT_SECRET` | 1 | `alttprbot/presentation/web/web.py` |
| `DISCORD_TOKEN` | 2 | `alttprbot/presentation/discord/bot.py`, `alttprbot/presentation/web/web.py` |
| `MAIN_TOURNAMENT_SERVERS` | 1 | `alttprbot/presentation/discord/cogs/tournament.py` |
| `OOTR_API_KEY` | 1 | `alttprbot/services/seedgen/randomizer/ootr.py` |
| `RACETIME_CLIENT_ID_OAUTH` | 1 | `alttprbot/presentation/web/blueprints/racetime.py` |
| `RACETIME_CLIENT_SECRET_OAUTH` | 1 | `alttprbot/presentation/web/blueprints/racetime.py` |
| `RACETIME_COMMAND_PREFIX` | 1 | `alttprbot/presentation/racetime/core.py` |
| `RACETIME_HOST` | 1 | `alttprbot/presentation/racetime/core.py` |
| `RACETIME_PORT` | 1 | `alttprbot/presentation/racetime/core.py` |
| `RACETIME_SECURE` | 1 | `alttprbot/presentation/racetime/core.py` |
| `RACETIME_URL` | 5 | `alttprbot/models/async_tournament.py`, `alttprbot/models/users.py`, `alttprbot/presentation/discord/cogs/asynctournament.py`, `alttprbot/presentation/discord/cogs/racer_verification.py`, `alttprbot/presentation/web/blueprints/racetime.py` |
| `SAHASRAHBOT_BUCKET` | 1 | `alttprbot/services/seedgen/randomizer/alttprdoor.py` |
| `SENTRY_URL` | 3 | `alttprbot/presentation/audit/bot.py`, `alttprbot/presentation/discord/bot.py`, `sahasrahbot.py` |
| `SG_API_ENDPOINT` | 1 | `alttprbot/util/speedgaming.py` |
| `SG_DISCORD_WEBHOOK` | 1 | `alttprbot/services/tournament/dailies.py` |
| `SPOILERLOGURLBASE` | 1 | `alttprbot/services/seedgen/spoilers.py` |

## Dynamic Config Key Pattern (Not fully represented in static table)

RaceTime category handlers dynamically resolve category-specific client credentials in `alttprbot/presentation/racetime/config.py`:

- `RACETIME_CLIENT_ID_<CATEGORY_SLUG_UPPER_NO_DASH>`
- `RACETIME_CLIENT_SECRET_<CATEGORY_SLUG_UPPER_NO_DASH>`

This means runtime may expect additional constants beyond the statically discovered keys (for each enabled RaceTime category).

## Coverage Against `.env.example`

`.env.example` has been aligned to include placeholders for the statically-read constants in this inventory.

Remaining caveat: dynamic RaceTime category keys are runtime-dependent and must still be provided per enabled category:

- `RACETIME_CLIENT_ID_<CATEGORY_SLUG_UPPER_NO_DASH>`
- `RACETIME_CLIENT_SECRET_<CATEGORY_SLUG_UPPER_NO_DASH>`

## Maintenance

When adding a new `config` constant read in code, update this inventory (via the scan command above) and `.env.example` in the same change.

Validate required startup config keys with:

- `poetry run python helpers/validate_runtime_config.py`
