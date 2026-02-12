# Discord Daily Challenge Audit

> Last updated: 2026-02-12

## Scope

This audit covers only the Discord daily challenge component in `alttprbot_discord/cogs/daily.py`.

Explicitly out of scope:

- RaceTime daily-race/tournament flows.
- Tournament subsystem components under `alttprbot/tournament/*`.
- SpeedGaming schedule command in `alttprbot_discord/cogs/sgdailies.py`.

## Component Boundary

Primary implementation surfaces:

- `alttprbot_discord/cogs/daily.py` (slash command + scheduled announcer loop)
- `alttprbot/models/models.py` (`Daily` and `Config` storage)
- `alttprbot_discord/util/alttpr_discord.py` (seed retrieval object used by cached helper)
- `alttprbot_discord/bot.py` (extension loading)

## Verified Intent (Owner-Confirmed)

The following intent was confirmed directly and is not inferred from code:

- The 5-minute polling loop is intended as a rate-limit/safety balance against the ALTTPR daily API.
- Channel identifiers may be migrated from name-based `DailyAnnouncerChannel` values to channel IDs.
- Thread creation on announce should be best-effort; seed announcement should still post when thread creation fails.

## Observed Behavior (Code Facts)

### User command path

- Slash command `/dailygame` fetches the latest daily hash from `https://alttpr.com/api/daily`.
- The command resolves the seed via `get_daily_seed(hash_id)` and posts an embed response.
- Command notes direct users to `https://alttpr.com/daily`.

### Scheduled announcement path

- `announce_daily` runs every 5 minutes via `discord.ext.tasks.loop`.
- For each iteration, it fetches current daily hash, checks dedupe state in table `daily`, and only announces on a new hash.
- On new hash, it builds an embed and queries config rows where `parameter='DailyAnnouncerChannel'`.
- Each config row can contain comma-separated channel names; each resolved channel receives the embed.
- After posting in a channel, the bot attempts to create a thread named from seed spoiler metadata.

### Caching and dedupe

- `find_daily_hash()` is cached for 60 seconds in `aiocache.SimpleMemoryCache`.
- `get_daily_seed(hash_id)` is cached for 24 hours in `aiocache.SimpleMemoryCache`.
- Dedupe persistence is DB-backed via `Daily(hash)` entries.

## Risk & Debt Findings

- API failure handling: the announcer loop has no explicit retry/backoff or local exception containment around ALTTPR API calls.
- Channel resolution fragility: name-based channel lookup can fail on channel rename or duplicate names.
- Null-safety gaps: code path assumes `guild` and `channel` resolve; missing entities can raise runtime errors.
- Thread-create hard dependency in implementation: current code does not isolate thread creation failures from message posting.
- Config value width: `Config.value` max length is 45 chars, constraining comma-separated multi-channel configuration.

## Policy/Contract Notes

- `DailyAnnouncerChannel` currently behaves as a comma-separated list of channel names.
- Migration target should be channel IDs for durability and unambiguous lookup.
- Best-effort thread policy implies announce send and thread create should be independently guarded.

## Suggested Refactor Sequence

1. Add local try/except boundaries in the loop to prevent task death on transient API or Discord errors.
2. Introduce retries/backoff for `find_daily_hash()` and seed retrieval.
3. Migrate config storage contract from channel names to IDs with backward-compatible read logic.
4. Split message posting from thread creation and treat thread creation as non-fatal.
5. Add structured logging fields (`guild_id`, `channel`, `hash_id`) for observability.

## Open Questions

- Should announcement failures be retried immediately per channel or deferred until the next 5-minute tick?
- Should historical dedupe table `daily` keep all hashes indefinitely or enforce retention?
