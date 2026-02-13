# Config Constants Inventory

> Last updated: 2026-02-12

## Scope

This document captures constants expected from root `config.py`, based on import usage across the application.

- Source scan command: `poetry run python /tmp/config_scan.py`
- Scan result summary: 40 files with config constant reads, 36 unique constants
- Coverage: static constant attribute usage discovered in application code

## Expected Constants (Static Reads)

| Constant | References | Consuming files |
|---|---:|---|
| `ALTTPR_BASEURL` | 2 | `alttprbot/alttprgen/generator.py`, `alttprbot_discord/util/alttpr_discord.py` |
| `ALTTPR_PASSWORD` | 1 | `alttprbot_discord/util/alttpr_discord.py` |
| `ALTTPR_USERNAME` | 1 | `alttprbot_discord/util/alttpr_discord.py` |
| `ALTTP_RANDOMIZER_SERVERS` | 2 | `alttprbot_discord/cogs/misc.py`, `alttprbot_discord/cogs/sgdailies.py` |
| `ALTTP_ROM` | 1 | `alttprbot/alttprgen/randomizer/alttprdoor.py` |
| `APP_SECRET_KEY` | 1 | `alttprbot_api/api.py` |
| `APP_URL` | 7 | `alttprbot/tournament/core.py`, `alttprbot/util/rankedchoice.py`, `alttprbot_api/api.py`, `alttprbot_api/blueprints/racetime.py`, `alttprbot_discord/cogs/asynctournament.py`, `alttprbot_discord/cogs/nickname.py`, `alttprbot_discord/cogs/rankedchoice.py` |
| `AUDIT_DISCORD_TOKEN` | 1 | `alttprbot_audit/bot.py` |
| `AWS_SPOILER_BUCKET_NAME` | 1 | `alttprbot/alttprgen/spoilers.py` |
| `BINGO_COLLAB_DISCORD_WEBHOOK` | 1 | `alttprbot/tournament/smbingo.py` |
| `CC_TOURNAMENT_AUDIT_CHANNELS` | 1 | `alttprbot_discord/cogs/tournament.py` |
| `CC_TOURNAMENT_SERVERS` | 1 | `alttprbot_discord/cogs/tournament.py` |
| `DB_HOST` | 4 | `dbtest.py`, `helpers/fix_alttprqual_data.py`, `migrations/tortoise_config.py`, `sahasrahbot.py` |
| `DB_NAME` | 4 | `dbtest.py`, `helpers/fix_alttprqual_data.py`, `migrations/tortoise_config.py`, `sahasrahbot.py` |
| `DB_PASS` | 4 | `dbtest.py`, `helpers/fix_alttprqual_data.py`, `migrations/tortoise_config.py`, `sahasrahbot.py` |
| `DB_PORT` | 4 | `dbtest.py`, `helpers/fix_alttprqual_data.py`, `migrations/tortoise_config.py`, `sahasrahbot.py` |
| `DB_USER` | 4 | `dbtest.py`, `helpers/fix_alttprqual_data.py`, `migrations/tortoise_config.py`, `sahasrahbot.py` |
| `DEBUG` | 13 | `alttprbot/speedgaming.py`, `alttprbot/tournaments.py`, `alttprbot/util/asynctournament.py`, `alttprbot/util/speedgaming.py`, `alttprbot_api/api.py`, `alttprbot_api/blueprints/sglive.py`, `alttprbot_audit/bot.py`, `alttprbot_discord/bot.py`, `alttprbot_discord/cogs/asynctournament.py`, `alttprbot_discord/cogs/inquiry.py`, `alttprbot_discord/cogs/racer_verification.py`, `alttprbot_discord/cogs/tournament.py`, `alttprbot_racetime/config.py` |
| `DISCORD_CLIENT_ID` | 1 | `alttprbot_api/api.py` |
| `DISCORD_CLIENT_SECRET` | 1 | `alttprbot_api/api.py` |
| `DISCORD_TOKEN` | 2 | `alttprbot_api/api.py`, `alttprbot_discord/bot.py` |
| `MAIN_TOURNAMENT_SERVERS` | 1 | `alttprbot_discord/cogs/tournament.py` |
| `MULTIWORLDHOSTBASE` | 2 | `alttprbot_discord/cogs/bontamw.py`, `alttprbot_discord/cogs/doorsmw.py` |
| `OOTR_API_KEY` | 1 | `alttprbot/alttprgen/randomizer/ootr.py` |
| `RACETIME_CLIENT_ID_OAUTH` | 1 | `alttprbot_api/blueprints/racetime.py` |
| `RACETIME_CLIENT_SECRET_OAUTH` | 1 | `alttprbot_api/blueprints/racetime.py` |
| `RACETIME_COMMAND_PREFIX` | 1 | `alttprbot_racetime/core.py` |
| `RACETIME_HOST` | 1 | `alttprbot_racetime/core.py` |
| `RACETIME_PORT` | 1 | `alttprbot_racetime/core.py` |
| `RACETIME_SECURE` | 1 | `alttprbot_racetime/core.py` |
| `RACETIME_URL` | 5 | `alttprbot/models/models.py`, `alttprbot/tournaments.py`, `alttprbot_api/blueprints/racetime.py`, `alttprbot_discord/cogs/asynctournament.py`, `alttprbot_discord/cogs/racer_verification.py` |
| `SAHASRAHBOT_BUCKET` | 1 | `alttprbot/alttprgen/randomizer/alttprdoor.py` |
| `SENTRY_URL` | 3 | `alttprbot_audit/bot.py`, `alttprbot_discord/bot.py`, `sahasrahbot.py` |
| `SG_API_ENDPOINT` | 2 | `alttprbot/speedgaming.py`, `alttprbot/util/speedgaming.py` |
| `SG_DISCORD_WEBHOOK` | 1 | `alttprbot/tournament/dailies/alttprdaily.py` |
| `SPOILERLOGURLBASE` | 1 | `alttprbot/alttprgen/spoilers.py` |

## Dynamic Config Key Pattern (Not fully represented in static table)

RaceTime category handlers dynamically resolve category-specific client credentials in `alttprbot_racetime/config.py`:

- `RACETIME_CLIENT_ID_<CATEGORY_SLUG_UPPER_NO_DASH>`
- `RACETIME_CLIENT_SECRET_<CATEGORY_SLUG_UPPER_NO_DASH>`

This means runtime may expect additional constants beyond the 40 statically discovered keys (for each enabled RaceTime category).

## Coverage Against `config.py.example`

`config.py.example` has been aligned to include placeholders for all 36 statically-read constants in this inventory.

Remaining caveat: dynamic RaceTime category keys are runtime-dependent and must still be provided per enabled category:

- `RACETIME_CLIENT_ID_<CATEGORY_SLUG_UPPER_NO_DASH>`
- `RACETIME_CLIENT_SECRET_<CATEGORY_SLUG_UPPER_NO_DASH>`

## Maintenance

When adding a new `config` constant read in code, update this inventory and `config.py.example` in the same change.

Validate required startup config keys with:

- `poetry run python helpers/validate_runtime_config.py`
