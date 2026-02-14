# SahasrahBot Core Library & Data Layer Analysis

> Last updated: 2026-02-12
> Scope: Core randomizer library, data models, database access patterns, and utility layer

This document describes current core-library and data-layer behavior from code analysis.

---

## 1. Randomizer Generation

### Architecture Overview

The randomizer generation system lives in `alttprbot/alttprgen/` and follows a **preset-driven class hierarchy**. The central class is `SahasrahBotPresetCore` in `generator.py`, which provides a base for all randomizer types. Each supported game has a concrete subclass:

| Class | `randomizer` slug | Game |
|---|---|---|
| `ALTTPRPreset` | `alttpr` | A Link to the Past Randomizer |
| `ALTTPRMystery` | `alttprmystery` | ALTTPR with randomized settings (mystery) |
| `SMPreset` | `sm` | Super Metroid Randomizer |
| `SMZ3Preset` | `smz3` | SM + ALTTPR combo randomizer |
| `CTJetsPreset` | `ctjets` | Chrono Trigger: Jets of Time |

These are registered in `PRESET_CLASS_MAPPING` at the bottom of `generator.py`.

### Seed Generation Flow

1. **Preset loading**: `SahasrahBotPresetCore` accepts a preset string (e.g., `"open"` or `"namespace/mypreset"`). Global presets are YAML files on disk under `presets/<randomizer>/`. Namespaced presets are stored in the database (`Presets` model).
2. **Fetching**: `fetch()` reads the YAML, populates `self.preset_data`.
3. **Generation**: Each subclass implements `generate()`, which:
   - Reads `settings` from preset data
   - Calls the appropriate external API or local tool
   - Logs the generation to `AuditGeneratedGames`
   - Returns a seed object

### ALTTPR Generation (`ALTTPRPreset.generate()`)

Three code paths based on preset flags:
- **`doors: true`** → Calls `AlttprDoorDiscord.create()` (local door randomizer subprocess)
- **`avianart: true`** → Calls `AVIANARTDiscord.create()` (avianart.games API)
- **Default** → Calls `ALTTPRDiscord.generate()` via the `pyz3r` library to the alttpr.com API
  - Supports customizer endpoint (`/api/customizer`) with forced item locations
  - Branch selection: `live` (alttpr.com), `beeta` (beeta.alttpr.com), `tournament` (tournament.alttpr.com)

### Mystery Generation (`ALTTPRMystery`)

Mystery weights are YAML files where each setting has probability weights. The flow:
1. `mystery_generate()` checks if a `preset` key exists in weights → may delegate to a known preset
2. Otherwise calls `generate_doors_mystery()` in `mysterydoors.py`
3. That function resolves sub-weights recursively, randomly picks settings from weighted distributions using `pyz3r.mystery.get_random_option()`
4. Returns an `AlttprMystery` dataclass containing the rolled settings
5. Retries up to 5 times on API errors (via `tenacity`)

### SM / SMZ3 Generation (`SMPreset`, `SMZ3Preset`)

- Use `SMDiscord` / `SMZ3Discord` classes (wrappers around samus.link API)
- Support spoiler keys for controlled spoiler access
- Base URL varies by `release` field in preset (e.g., `https://{release}.samus.link`)

### SM Varia (`smvaria.py`)

Separate module for the Super Metroid Varia Randomizer (randommetroidsolver.pythonanywhere.com):
- `generate_preset()` → Direct preset-based generation via `SuperMetroidVariaDiscord`
- `generate_choozo()` → Custom "Chozo" style generation with validated parameters
- `generate_league_playoff()` → Specific settings for SM league playoffs

### Chrono Trigger: Jets of Time (`ctjets.py`)

Uses web scraping of `ctjot.com`:
- Fetches CSRF token, submits form data with settings
- Uploads a base ROM from `/opt/data/chronotrigger.sfc`
- Extracts seed share link from response HTML

### Spoiler Log System (`spoilers.py`)

- `generate_spoiler_game()` → Generates an ALTTPR seed with `spoilers="generate"`, then extracts the spoiler log
- `write_json_to_disk()` → Compresses the spoiler JSON with gzip, uploads to S3 (`AWS_SPOILER_BUCKET_NAME`)
- Supports two spoiler types:
  - `spoiler` → Full formatted spoiler via `seed.get_formatted_spoiler()`
  - `progression` → Filtered to progression items only (defined in `ext/progression_spoiler.py`)
- Returns a URL like `{SPOILERLOGURLBASE}/{filename}`

### Progression Spoiler (`ext/progression_spoiler.py`)

Filters the full spoiler log to show only **progression items** (swords, bottles, medallions, boots, mirror, etc.) organized by **region** (Hyrule Castle, Eastern Palace, Light World, Dark World, etc.). Uses `pyz3r.spoiler.mw_filter()` internally.

### Door Randomizer (`randomizer/alttprdoor.py`)

A fully local generation pipeline:
1. Writes settings to a JSON file in a temp directory
2. Runs `DungeonRandomizer.py` as a subprocess from `utils/ALttPDoorRandomizer/`
3. Creates a BPS patch using `flips` binary
4. Uploads patch + spoiler to S3 (`SAHASRAHBOT_BUCKET`)
5. Supports `stable` and `volatile`/`unstable` branches

### Other Randomizers (`randomizer/` directory)

| Module | Game | Method |
|---|---|---|
| `aosr.py` | Aria of Sorrow Randomizer | Client-side URL generation |
| `bingosync.py` | BingoSync rooms | Web scraping + private API |
| `ffr.py` | Final Fantasy Randomizer | URL seed parameter injection |
| `ootr.py` | Ocarina of Time Randomizer | REST API (ootrandomizer.com) |
| `smb3r.py` | Super Mario Bros 3 Randomizer | Random seed number + flags |
| `smdash.py` | DASH Super Metroid Randomizer | REST API (dashrando.net) |
| `z1r.py` | Zelda 1 Randomizer | Random seed number + flags |
| `z2r.py` | Zelda 2 Randomizer | Preset flag strings + random seed |
| `avianart.py` | AVIANART ALTTPR fork | REST API (avianart.games) |

---

## 2. Data Models (Tortoise ORM)

All models are defined in `alttprbot/models/models.py` and `alttprbot/models/schedule.py`, re-exported via `alttprbot/models/__init__.py`.

### Core Game Models

| Model | Table | Purpose |
|---|---|---|
| `AuditGeneratedGames` | `audit_generated_games` | Logs every generated randomizer seed (randomizer type, hash, permalink, settings, type/option, customizer/doors flags) |
| `Daily` | `daily` | Stores daily challenge seed hashes |
| `PatchDistribution` | `patch_distribution` | Tracks patch distribution for games (patch_id, game, used flag) |

### Discord Integration

| Model | Table | Purpose |
|---|---|---|
| `AuditMessages` | `audit_messages` | Message audit log (guild, channel, user, content, attachments, deleted flag) |
| `Config` | `config` | Per-guild configuration key-value pairs |
| `DiscordServerCategories` | `discord_server_categories` | Categories for server list feature (guild_id, channel_id, title, description, order) |
| `DiscordServerLists` | `discord_server_lists` | Individual server entries with invite IDs, linked to categories via FK |
| `InquiryMessageConfig` | — | Maps message IDs to role IDs for inquiry-based role assignment |
| `ReactionGroup` | `reaction_group` | Reaction role groups bound to specific messages |
| `ReactionRole` | `reaction_role` | Individual emoji→role mappings within a reaction group |
| `VoiceRole` | `voice_role` | Auto-assign roles when users join voice channels |
| `SpeedGamingDailies` | `sgdailies` | SpeedGaming daily schedule configuration per guild |
| `ScheduledEvents` | — | Maps Discord scheduled event IDs to SpeedGaming episode IDs |

### User & Identity

| Model | Table | Purpose |
|---|---|---|
| `SRLNick` | `srlnick` | Legacy: Maps Discord user IDs to Twitch names and racetime.gg IDs |
| `NickVerification` | `nick_verification` | Verification keys for nick linking |
| `Users` | — | Modern user model: discord_user_id, twitch_name, rtgg_id, rtgg_access_token, display_name. Has reverse relations to all async tournament models |
| `RacerVerification` | — | Configuration for race count verification (category, minimum races, time period, reverify settings) |
| `VerifiedRacer` | — | Records of verified racers linked to Users and RacerVerification |

### Presets

| Model | Table | Purpose |
|---|---|---|
| `PresetNamespaces` | — | User-owned preset namespaces (name + discord_user_id, both unique) |
| `PresetNamespaceCollaborators` | — | Additional users who can edit a namespace's presets |
| `Presets` | — | Stored preset YAML content, scoped by (randomizer, preset_name, namespace) |

### Tournament System

| Model | Table | Purpose |
|---|---|---|
| `TournamentGames` | `tournament_games` | Tournament episode tracking (episode_id PK, event, game_number, settings, preset, notes) |
| `TournamentPresetHistory` | — | Audit log of which presets were used for which episodes |
| `TournamentResults` | `tournament_results` | Race results (SRL/RT ID, episode, permalink, bingosync, spoiler URL, event, status, results JSON, Google Sheet sync flag) |
| `SpoilerRaces` | `spoiler_races` | Spoiler race tracking (SRL ID, spoiler URL, study time, started timestamp) |
| `SrlRaces` | `srl_races` | SRL race tracking (SRL ID, goal, message) |

### Racetime.gg Integration

| Model | Table | Purpose |
|---|---|---|
| `RTGGUnlistedRooms` | — | Tracks unlisted racetime rooms |
| `RTGGWatcher` | — | Race watcher config per guild/channel/category |
| `RTGGWatcherPlayer` | — | Specific players to watch in a category |
| `RTGGAnnouncers` | — | Channel announcement config for racetime categories |
| `RTGGAnnouncerMessages` | — | Tracks announcement messages per room |
| `RTGGOverrideWhitelist` | — | Whitelist for racetime overrides with expiry |
| `RacetimeKONOTGame` | — | King of Not Tournament game tracking |
| `RaceTimeKONOTSegment` | — | Individual segments within KONOT games |

### Multiworld

| Model | Table | Purpose |
|---|---|---|
| `SMZ3Multiworld` | `smz3_multiworld` | Legacy multiworld tracking (message_id PK, owner, randomizer, preset, status) |
| `Multiworld` | — | Modern multiworld tracking (same structure) |
| `MultiworldEntrant` | — | Entrants in a multiworld session, FK to Multiworld |

### Async Tournament System

A large subsystem for asynchronous tournaments:

| Model | Purpose |
|---|---|
| `AsyncTournament` | Tournament definition (name, guild, channel, owner, active flag, reattempt policy, runs_per_pool, customization) |
| `AsyncTournamentWhitelist` | Whitelisted participants |
| `AsyncTournamentPermissions` | Role-based permissions (user or Discord role) |
| `AsyncTournamentPermalinkPool` | Named groups of permalinks within a tournament |
| `AsyncTournamentPermalink` | Individual seed URLs with par time tracking |
| `AsyncTournamentRace` | Individual race runs with full lifecycle (pending→in_progress→finished/forfeit/disqualified), scoring, review status, VOD URLs, IGT, collection rate |
| `AsyncTournamentLiveRace` | Live race tracking with racetime.gg integration |
| `AsyncTournamentReviewNotes` | Review notes attached to race runs |
| `AsyncTournamentAuditLog` | Audit trail for tournament actions |

### Ranked Choice Voting

| Model | Table | Purpose |
|---|---|---|
| `RankedChoiceElection` | `ranked_choice_election` | Election definition (title, seats, active/private flags, voter role) |
| `RankedChoiceAuthorizedVoters` | `ranked_choice_authorized_voters` | Authorized voter list |
| `RankedChoiceCandidate` | `ranked_choice_candidate` | Candidates with winner flag |
| `RankedChoiceVotes` | `ranked_choice_votes` | Individual ranked votes |

### Triforce Texts

| Model | Purpose |
|---|---|
| `TriforceTexts` | User-submitted end-game texts (pool, text, author, approved/broadcasted flags) |
| `TriforceTextsConfig` | Configuration key-value pairs per text pool |

### SGL 2023

| Model | Purpose |
|---|---|
| `SGL2023OnsiteHistory` | Tracks onsite access history (tournament, URL, IP address) |

### Authorization

| Model | Purpose |
|---|---|
| `AuthorizationKeys` | API keys for external access |
| `AuthorizationKeyPermissions` | Permissions per key (type + subtype) |

### Schedule System (`models/schedule.py`)

A full event scheduling system:

| Model | Purpose |
|---|---|
| `ScheduleEvent` | Event definition with signup toggles (open_player_signup, etc.) and max crew counts |
| `ScheduleRole` | Named roles within an event (admin, mod, player...) |
| `ScheduleRoleMember` | User→role assignments |
| `ScheduleEpisode` | Individual scheduled episodes with countdown time, approval workflow, broadcast channel |
| `ScheduleEpisodePlayer` | Players in an episode |
| `ScheduleEpisodeCommentator` | Commentators with approval workflow and preferred partner |
| `ScheduleEpisodeCommentatorPreferredPartner` | Preferred commentator pairings |
| `ScheduleEpisodeTracker` | Trackers with approval workflow |
| `ScheduleEpisodeRestreamer` | Restreamers with approval workflow |
| `ScheduleBroadcastChannels` | Twitch channels for broadcasting |
| `ScheduleAudit` | Audit trail for schedule changes |

---

## 3. Database Layer

### Database Access Pattern

Application database access now uses Tortoise ORM model operations directly (including `alttprbot/database/` helper modules):

```python
await models.AuditGeneratedGames.create(...)
await models.Presets.get_or_none(...)
await models.AsyncTournamentRace.filter(...)
```

Helper modules that previously used raw SQL now call model filters/updates and return dictionary-shaped values where existing call sites expect dict access. Caching behavior remains manual via `aiocache.SimpleMemoryCache` invalidation.

### Legacy Database Modules

| Module | Purpose | Tables Accessed |
|---|---|---|
| `config.py` | Guild configuration CRUD | `config` |
| `discord_server_lists.py` | Server list + category management | `discord_server_lists`, `discord_server_categories` |
| `role.py` | Reaction role group/emoji management | `reaction_group`, `reaction_role` |
| `smz3_multiworld.py` | SMZ3 multiworld session tracking | `smz3_multiworld` |
| `spoiler_races.py` | Spoiler race lifecycle (insert→start→query) | `spoiler_races` |
| `tournament_results.py` | Tournament result recording and Google Sheets sync | `tournament_results` |
| `voicerole.py` | Voice channel role assignment config | `voice_role` |

### Key Observations

- **`config.py`** imports `CACHE` from `alttprbot_discord.util.guild_config`, creating a cross-layer dependency
- **`role.py`** has extensive CRUD for reaction-based role assignment with its own cache namespace `"role"`
- **`tournament_results.py`** tracks races through a lifecycle: `NULL status` → `STARTED` → `RECORDED` → written_to_gsheet
- **`spoiler_races.py`** preserves the study-time validity window using ORM reads/updates and Python time-window checks

---

## 4. Utilities

### `alttprbot/util/` Modules

| Module | Purpose |
|---|---|
| `__init__.py` | Empty — package marker |
| `helpers.py` | `generate_random_string(length)` — alphanumeric random string generator |
| `console.py` | Logging wrappers (`debug`, `info`, `warning`, `error`, `critical`) that auto-detect caller module name |
| `http.py` | Generic async HTTP utilities: `request_generic()`, `request_json_post()`, `request_json_put()` — all use `aiohttp`, support text/json/binary/yaml response types |
| `gsheet.py` | Google Sheets API client setup using `oauth2client` service account credentials from config |
| `holyimage.py` | Fetches "holy images" from `alttp.mymm1.com` — community images with Discord embed support |
| `rom.py` | SNES address conversion utilities: `snes_to_pc_lorom()`, `pc_to_snes_lorom()` |
| `triforce_text.py` | End-game triforce text system: balanced/random selection from pools, generation with text injection into preset settings |
| `asynctournament.py` | Async tournament scoring engine: par time calculation (avg of top 5), qualifier scoring (percentage of par), leaderboard computation with caching, test data population |
| `rankedchoice.py` | Ranked choice voting: uses `pyrankvote` for Single Transferable Vote, Discord embed creation, election post refresh |
| `speedgaming.py` | SpeedGaming API client: fetches upcoming episodes by event, individual episode details. Supports local test fixtures from `test_input/` |

### Notable Implementation Details

- **`asynctournament.py`** is the most complex utility (~260 lines). It uses `asyncio.Lock` for thread-safe score calculation, `aiocache` for leaderboard caching, and a `LeaderboardEntry` dataclass with `@cached_property` for lazy computation.
- **`speedgaming.py`** has a DEBUG mode that loads test data from JSON files instead of hitting the API.
- **`holyimage.py`** constructs Discord embeds with thumbnails, credit attribution, and source links.
- **`triforce_text.py`** implements a "balanced" selection algorithm that first picks a random user, then a random text from that user, ensuring fair representation across contributors.

---

## 5. Preset System

### Structure

Presets are YAML files stored under `presets/<randomizer>/`:

```
presets/
├── alttpr/          (~115 presets)
├── alttprmystery/   (~44 weightsets)
├── ctjets/          (5 presets)
├── sm/              (4 presets)
├── smz3/            (~30 presets)
└── README.md
```

### ALTTPR Preset Format

Standard presets contain a `settings` dictionary matching the ALTTPR API parameters:

```yaml
goal_name: "descriptive name"
customizer: false
description: "Human-readable description"
settings:
  goal: ganon
  mode: open
  weapons: randomized
  crystals: { ganon: "7", tower: "7" }
  enemizer: { boss_shuffle: none, ... }
  glitches: none
  entrances: none
  dungeon_items: standard
  item_placement: advanced
  # ... etc
```

Special flags:
- `doors: true` → Uses the local door randomizer instead of alttpr.com API
- `avianart: true` → Uses the avianart.games API
- `customizer: true` → Uses `/api/customizer` endpoint with `forced_locations` support
- `branch: live|beeta|tournament` → Selects API server

### Door Preset Format

Door presets have the same outer structure but with door-specific settings like `door_shuffle`, `intensity`, `mixed_travel`, and a `customitemarray` for fine-grained item pool control.

### Mystery Weightset Format

Mystery presets use a **weighted probability** format:

```yaml
glitches_required:
  none: 100
  overworld_glitches: 0
weapons:
  randomized: 40
  assured: 40
  swordless: 5
```

Each setting maps options to probability weights. The `pyz3r.mystery.get_random_option()` function selects from these weighted distributions.

### SM/SMZ3 Preset Format

```yaml
randomizer: "smz3"     # or "sm"
settings:
  smlogic: normal
  goal: defeatboth
  swordlocation: randomized
  morphlocation: randomized
  keyshuffle: none
  race: "true"
  gamemode: normal
```

### CT Jets Preset Format

```yaml
randomizer: ctjets
version: 3.1.0
settings:
  difficulty: normal
  tech_rando: Fully Random
  # ... ctjot.com form fields
```

### Namespaced Presets

Users can create personal presets stored in the database under a namespace (derived from their Discord username). Namespaced presets are addressed as `namespace/preset_name`. Collaborators can be added to a namespace.

---

## 6. Migration System

### Aerich Configuration

```ini
[aerich]
tortoise_orm = migrations.tortoise_config.TORTOISE_ORM
location = ./migrations
```

### Tortoise ORM Config (`migrations/tortoise_config.py`)

```python
TORTOISE_ORM = {
    "connections": {
        "default": f'mysql://...'  # MySQL connection string from config
    },
    "apps": {
        "models": {
        "models": ["alttprbot.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
```

### Migration History

The `migrations/models/` directory contains **97 migration files** spanning from May 2021 to September 2024:

- **Migrations 1–34** (2021–2022): Plain `.sql` files — initial schema, foreign keys, table renames, field additions
- **Migrations 35+** (late 2022–2024): Python `.py` files — Aerich's native format for more complex migrations

This shows the project transitioned from raw SQL migrations to Aerich-managed Python migrations around late 2022. The database backend is **MySQL**.

### Key Migration Milestones (inferred from dates)

- **2021-05**: Initial schema creation
- **2021-05 to 2021-10**: Foreign keys, reaction roles, table renames
- **2022-01 to 2022-03**: Additional features
- **2022-11 to 2023-01**: Transition to Python migrations
- **2023-02 to 2023-04**: Async tournament system (bulk of ~30 migrations)
- **2023-08 to 2024-09**: Racer verification, schedule system, misc updates

---

## 7. External APIs

### Primary Randomizer APIs

| API | Library/Method | Base URL | Used For |
|---|---|---|---|
| **ALTTPR** | `pyz3r` → `ALTTPRDiscord` | `alttpr.com`, `beeta.alttpr.com`, `tournament.alttpr.com` | Main ALTTPR seed generation (standard + customizer endpoints) |
| **SM Randomizer** | `SMDiscord` | `sm.samus.link` (+ release variants) | Super Metroid seed generation |
| **SMZ3 Randomizer** | `SMZ3Discord` | `samus.link` (+ release variants) | SM+ALTTPR combo seeds |
| **SM Varia** | `SuperMetroidVariaDiscord` | randommetroidsolver.pythonanywhere.com (inferred) | Super Metroid Varia Randomizer (Chozo, League, preset-based) |
| **AVIANART** | `AVIANARTDiscord` / `AVIANART` | `avianart.games` | ALTTPR fork with alternative generation |
| **OoTR** | `ootr.roll_ootr()` | `ootrandomizer.com` | Ocarina of Time Randomizer (API key authenticated) |
| **CT Jets** | `ctjets.roll_ctjets()` | `ctjot.com` | Chrono Trigger: Jets of Time (web scraping) |
| **DASH SM** | `smdash.create_smdash()` | `dashrando.net` | DASH Super Metroid Randomizer |

### Client-Side Generators (no API call)

| Generator | Method |
|---|---|
| AoSR | URL construction with seed parameter |
| FFR | URL mutation with random seed |
| SMB3R | Random seed + flag passthrough |
| Z1R | Random seed + flag passthrough |
| Z2R | Preset flag lookup + random seed |

### Infrastructure APIs

| Service | Purpose |
|---|---|
| **AWS S3** (via `aioboto3`) | Spoiler log storage, door rando patch/spoiler storage |
| **SpeedGaming** (`speedgaming.org/api`) | Tournament schedule retrieval (episodes, events) |
| **BingoSync** (`bingosync.com`) | Bingo room creation/management (web scraping, private API) |
| **Google Sheets** (via `googleapiclient`) | Tournament results export |
| **racetime.gg** | Race room management (configured via multiple `RACETIME_*` config values) |

### Key Libraries

| Library | Purpose |
|---|---|
| `pyz3r` | ALTTPR Python library — seed generation, mystery weights, spoiler parsing |
| `tortoise-orm` | Async ORM for MySQL |
| `aerich` | Database migration tool for Tortoise ORM |
| `discord.py` / `py-cord` | Discord bot framework |
| `aiohttp` | Async HTTP client/server |
| `aioboto3` | Async AWS SDK |
| `aiocache` | Async caching (SimpleMemoryCache) |
| `pyrankvote` | Single Transferable Vote counting |
| `tenacity` | Retry logic for flaky API calls |
| `html2markdown` / `BeautifulSoup` | HTML parsing for web scraping |
| `pytz` | Timezone handling |
