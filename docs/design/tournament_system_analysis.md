# Tournament System Analysis

> Research-only analysis of the SahasrahBot tournament subsystem, covering architecture, all handlers, SpeedGaming integration, orchestration, data flow, and dailies.

---

## 1. Overview

The tournament system automates the lifecycle of competitive ALTTPR (and related randomizer) races that are scheduled via **SpeedGaming (SG)**. It:

- Polls the SG schedule API for upcoming episodes.
- Automatically opens **RaceTime.gg** (RT.gg) race rooms at a configurable time before the scheduled start.
- Invites players, sends DMs, posts announcements.
- Generates randomizer seeds on demand (via `!tournamentrace` in the RT.gg room).
- Records results to a Google Sheet after race completion.
- Sends audit/commentary/mod embeds to designated Discord channels.

The system is built around a **Template Method / Strategy pattern**: a base class (`TournamentRace`) defines the lifecycle, and each tournament/event provides a concrete subclass that overrides configuration, seed rolling, form handling, and room settings.

**Author intent (verified, 2026-02-11):** long-term, the “which events are enabled” switch and substantial per-event configuration (including stable mappings/rules like title→preset maps and seasonal schedules) should move out of commented Python registries and into a config file (e.g., `config/tournaments.yaml`).

### Key External Dependencies

| System | Role |
|---|---|
| **SpeedGaming API** | Schedule source, episode/match data, player info, restream channels |
| **RaceTime.gg** | Race room creation, entrant management, chat commands, race lifecycle |
| **Discord** | Player DMs, audit channels, commentary channels, scheduled events |
| **Google Sheets** | Results recording |
| **alttpr.com / randomizer APIs** | Seed generation (ALTTPR, SM Varia, DASH, BingoSync, etc.) |

---

## 2. Core Framework (`core.py`)

### `TournamentConfig` (dataclass)

Holds all per-event configuration. Every tournament handler's `configuration()` method returns one of these.

| Field | Purpose |
|---|---|
| `guild` | The Discord server for this tournament |
| `racetime_category` | RT.gg category slug (e.g. `'alttpr'`, `'smr'`, `'smz3'`) |
| `racetime_goal` | RT.gg goal string (e.g. `'Beat the game - Tournament (Solo)'`) |
| `event_slug` | Identifier matching the SG event slug |
| `schedule_type` | Always `"sg"` (SpeedGaming) |
| `audit_channel` | Discord channel for admin/audit messages |
| `commentary_channel` | Discord channel for commentary team info |
| `mod_channel` | Discord channel for mod messages |
| `scheduling_needs_channel` | Discord channel for scheduling needs tracking |
| `create_scheduled_events` | Whether to create Discord Scheduled Events |
| `admin_roles` / `helper_roles` / `commentator_roles` / `mod_roles` | Discord roles for permission gating |
| `stream_delay` | Minutes of delay before results are recorded (to avoid spoilers) |
| `room_open_time` | Minutes before start time to open the RT.gg room (default 35) |
| `auto_record` | Whether to automatically mark races as recorded on RT.gg |
| `gsheet_id` | Google Sheet ID for results |
| `lang` | Language code (e.g. `'en'`, `'de'`, `'fr'`, `'es'`) |
| `coop` | Whether this is a co-op/team race |

### `TournamentPlayer`

Resolves a player from SG data → Discord member → database `Users` record.

- `construct(discord_id, guild)` — lookup by Discord ID.
- `construct_discord_name(discord_name, guild)` — lookup by Discord tag.
- Exposes `rtgg_id` and `name` properties.

### `TournamentRace` (base class)

The central class. Lifecycle is driven by classmethods:

#### Construction Classmethods

| Method | When Used |
|---|---|
| `construct(episodeid, rtgg_handler)` | Attach to an existing RT.gg room (handler already connected) |
| `construct_with_episode_data(episode, rtgg_handler)` | Same but with pre-fetched SG episode data |
| `construct_race_room(episodeid)` | **Full lifecycle**: creates RT.gg room, invites players, sends DMs, fires `on_room_creation` |
| `get_config()` | Just loads configuration (no episode data) |

#### Lifecycle Hook Methods (overridden by subclasses)

| Method | Purpose |
|---|---|
| `configuration()` | **Must override.** Returns `TournamentConfig`. |
| `roll()` | Generate the randomizer seed. |
| `process_tournament_race(args, message)` | Called when `!tournamentrace` is invoked in the RT.gg room. |
| `send_room_welcome()` | Post welcome message/pinned actions in the RT.gg room. |
| `on_room_creation()` | Post-creation hook (e.g. BingoSync setup). |
| `on_room_resume()` | When bot reconnects to an existing room. |
| `on_race_start()` | When the race countdown ends and timing begins. |
| `on_race_pending()` | When race enters pending state. |
| `create_embeds()` | Build Discord embeds for seed info. |
| `process_submission_form(payload, submitted_by)` | Handle web form submissions for race settings. |
| `send_race_submission_form(warning)` | DM players a link to submit settings. |

#### Key Methods

- `update_data()` — Fetches the SG episode, populates `self.players` via `make_tournament_player()`, gets the RT.gg bot and restream team.
- `create_race_room()` — Calls `self.rtgg_bot.startrace(...)` with configurable parameters (invitational, delays, chat settings, team race, etc.).
- `can_gatekeep(rtgg_id)` — Checks if a user is an SG restream volunteer or has a `helper_role`.
- `send_player_room_info()` — DMs each player the RT.gg room link.
- `send_audit_message()` / `send_commentary_message()` / `send_player_message()` — Post to appropriate Discord channels.

#### Key Properties

- `versus` — Player names joined by " vs. " (or ", " for 3+).
- `race_info` — Full race info string for RT.gg room description.
- `broadcast_channels` — Restream Twitch channel names from SG episode data.
- `race_start_time` / `race_start_time_restream` — Parsed from SG `whenCountdown` / `when`.
- `submit_link` — URL to the web-based settings submission form.
- `event_slug` / `event_name` / `friendly_name` — From SG episode data.

---

## 3. Tournament Handlers

### 3.1 `alttpr.py` — Generic ALTTPR Tournament (`ALTTPRTournamentRace`)

**Inherits:** `TournamentRace`

This is the **primary intermediate base class** for all ALTTPR-based tournaments. Most tournament handlers inherit from this rather than directly from `TournamentRace`.

**Key overrides:**
- `roll()` — Abstract/empty (subclasses implement).
- `process_tournament_race()` — Full seed generation workflow: calls `roll()`, `create_embeds()`, sends seed URL to all players via DM and RT.gg, writes `TournamentResults` to DB, sets race info.
- `send_room_welcome()` — Posts welcome message with a pinned "Roll Tournament Seed" action button.
- `create_embeds()` — Builds player and tournament embeds with seed code, RT.gg link, broadcast channels.
- `send_race_submission_form()` — Overrides to skip if `bracket_settings` already exist.
- `seed_code` property — Returns `(code1/code2/code3/code4/code5)` format.

**Also contains:** `ALTTPR2024Race` — a concrete class with hardcoded configuration for the 2024 ALTTPR Main Tournament (guild `334795604918272012`, 10-min stream delay, specific roles, Google Sheet).

---

### 3.2 `alttpr_quals.py` — ALTTPR Qualifier Races (`ALTTPRQualifierRace`)

**Inherits:** `TournamentRace` (directly, NOT `ALTTPRTournamentRace`)

**Purpose:** Live qualifier races for the ALTTPR Main Tournament. These are **open entry** races (not invitational) where multiple players race simultaneously.

**Key differences from standard tournament races:**
- `create_race_room()` — Creates a **non-invitational**, non-auto-start room with pre-race and mid-race chat disabled. `start_delay=30`.
- `player_racetime_ids` returns `[]` — no one is pre-invited; anyone can join.
- `construct_race_room()` — Checks for an `AsyncTournamentLiveRace` record; silently skips if none exists.
- `update_data()` — Does NOT populate `self.players` (no player lookup from SG data).
- `process_tournament_race()` — Complex qualifier workflow:
  1. Validates `AsyncTournamentLiveRace` exists with a pool and no existing permalink.
  2. Requires the invoker to be an admin/mod of the async tournament.
  3. Locks the room (`set_invitational()`).
  4. Generates seed using `triforce_text.generate_with_triforce_text("alttpr2024", preset)`.
  5. Creates `AsyncTournamentPermalink` and writes eligible entrant records.
- `on_race_start()` — Transitions entrant records from `pending` → `in_progress`, deletes non-joiners.
- `send_player_room_info()` — Posts to a public announce channel instead of DMing players.

**Helper functions (module-level):**
- `write_eligible_async_entrants()` — Iterates RT.gg entrants, creates/updates `Users`, checks pool race limits, creates `AsyncTournamentRace` records.
- `process_async_tournament_start()` — Finalizes entrant status on race start.

---

### 3.3 `alttprcd.py` — ALTTPR Crosskeys Drop (`ALTTPRCDTournament`)

**Inherits:** `ALTTPRTournamentRace`

**Event:** German-community Crosskeys Drop tournament.
**Preset:** `'crossedkeydrop'` via `preset.get_preset()`.
**Guild:** `469300113290821632` (German ALTTPR community).
**Lang:** `'de'`
**Overrides:** `roll()`, `configuration()` only.

---

### 3.4 `alttprde.py` — ALTTPR German Tournament (`ALTTPRDETournament`)

**Inherits:** `ALTTPRTournamentRace`

**Event:** German community multi-mode tournament with a title-based preset mapping.
**Guild:** `469300113290821632`
**Lang:** `'de'`
**Stream delay:** 10 min
**Google Sheet:** `'1dWzbwxoErGQyO4K1tZ-EexX1bdnTGuxQhLJDnmfcaR4'`

**Preset selection:** Reads `self.episode['match1']['title']`, strips text before `:`, and maps to a preset:

| Match Title | Preset |
|---|---|
| Open | `open` |
| Standard | `standard` |
| 6/6 Fast Ganon | `open_fast_66` |
| Casual Boots | `casualboots` |
| Big Key Shuffle | `catobat/bkshuffle` |
| Boss Shuffle | `nightcl4w/german_boss_shuffle` |
| All Dungeons | `adboots` |
| Open Hard | `derduden2/german_hard` |
| Enemizer | `enemizer` |
| 6/6 Vanilla Swords | `nightcl4w/6_6_vanilla_swords` |
| All Dungeons Keysanity | `adkeys_boots` |
| Standard Swordless | `nightcl4w/german_swordless2024` |

**Overrides:** `roll()`, `configuration()`

---

### 3.5 `alttpres.py` — ALTTPR Spanish Tournament (`ALTTPRESTournament`)

**Inherits:** `ALTTPRTournamentRace`

**Event:** Spanish community ALTTPR tournament.
**Guild:** `477850508368019486`
**Lang:** `'es'`

**Seed generation:** Uses `bracket_settings` from `TournamentGames.settings` (submitted via a web form). Calls `alttpr_discord.ALTTPRDiscord.generate(settings=...)`. Uses `/api/customizer` endpoint if `'eq'` is in settings, otherwise `/api/randomizer`.

**Submission form:** Dropdown-based preset selection (Ambrosia, Casual Boots, MCS, Open, Standard, etc.). Round of 8 adds AD+Keysanity, Dungeons, Keysanity.

**Overrides:** `roll()`, `configuration()`, `bracket_settings`, `submission_form`, `process_submission_form()`

---

### 3.6 `alttprfr.py` — ALTTPR French Tournament (`ALTTPRFRTournament`)

**Inherits:** `ALTTPRTournamentRace`

**Event:** French community ALTTPR tournament.
**Guild:** `470200169841950741`
**Lang:** `'fr'`

**Seed generation:** Uses `bracket_settings` from submitted form. Generates via `alttpr_discord.ALTTPRDiscord.generate(settings=...)`.

**Submission form:** The most granular of all — 9 individual setting fields:
- Dungeon Item Shuffle (Standard/MC/MCS/Keysanity)
- Goal (Defeat Ganon/Fast Ganon)
- World State (Open/Standard/Inverted/Retro)
- Boss Shuffle (Off/Random)
- Enemy Shuffle (Off/Shuffled)
- Hints (Off/On)
- Swords (Randomized/Assured/Vanilla/Swordless)
- Item Pool (Normal/Hard)
- Item Functionality (Normal/Hard)

**Special logic:** If enemy shuffle is on AND world state is standard AND swords is randomized or swordless → forces swords to `'assured'`.

**Overrides:** `roll()`, `configuration()`, `bracket_settings`, `submission_form`, `process_submission_form()`

---

### 3.7 `alttprhmg.py` — ALTTPR HMG (Hybrid Major Glitches) (`ALTTPRHMGTournament`)

**Inherits:** `ALTTPRTournamentRace`

**Event:** HMG (glitched) ALTTPR tournament.
**Guild:** `535946014037901333`
**Preset:** `'hmg'` with `branch='live'`
**Goal:** `'Beat the game (glitched)'`

**Overrides:** `roll()`, `configuration()` only.

---

### 3.8 `alttprleague.py` — ALTTPR League (`ALTTPRLeague`, `ALTTPROpenLeague`)

**Inherits:** `ALTTPRTournamentRace`

**Event:** ALTTPR League — a season-based league with its own API at `alttprleague.com`.
**Guild:** `543577975032119296`
**Stream delay:** 10 min

**Key feature:** Fetches mode/preset from the **League API** (`https://alttprleague.com/api/episode?id=...`) via `get_league_data()`. The API response contains `mode.preset`, `mode.coop`, and `mode.spoiler` flags.

**Seed generation:**
- If `league_data['spoiler']` is true → generates a spoiler race via `spoilers.generate_spoiler_game()` and schedules spoiler log reveal.
- Otherwise → generates via `ALTTPRPreset(preset).generate(...)`.

**Room creation:** Dynamically sets goal to `Co-op` or `Solo` based on league data. Sets `team_race` and `require_even_teams` per `league_data['coop']`.

**`ALTTPROpenLeague`:** Identical to `ALTTPRLeague` except uses event slug `"alttprleague"` (vs `"invleague"` for the invitational league). Both share the same guild and roles.

**Overrides:** `roll()`, `configuration()`, `update_data()`, `get_league_data()`, `create_race_room()`

---

### 3.9 `alttprmini.py` — ALTTPR Mini Tournament (`ALTTPRMiniTournament`)

**Inherits:** `ALTTPRTournamentRace`

**Event:** German-community mini tournament.
**Guild:** `469300113290821632`
**Lang:** `'de'`
**Google Sheet:** `'1dWzbwxoErGQyO4K1tZ-EexX1bdnTGuxQhLJDnmfcaR4'`

**Preset selection:** Title-based mapping (same pattern as `alttprde`):

| Match Title | Preset |
|---|---|
| Casual Boots | `casualboots` |
| 6/6 Defeat Ganon | `nightcl4w/6_6_defeat_ganon` |
| Boss Shuffle | `nightcl4w/boss_shuffle` |
| Big Key Shuffle | `catobat/bkshuffle` |
| All Dungeons | `adboots` |

**Overrides:** `roll()`, `configuration()`

---

### 3.10 `alttprsglive.py` — ALTTPR SGL (SpeedGaming Live) (`ALTTPRSGLive`)

**Inherits:** `ALTTPRTournamentRace`

**Event:** SpeedGaming Live ALTTPR bracket (e.g. SGL 2024).
**Guild:** `590331405624410116`
**Room open time:** 30 min, **Stream delay:** 15 min

**Key feature:** Handles **both qualifiers and bracket matches** in one class.
- `update_data()` sets `self.qualifier = True` if `friendly_name` starts with "qualifier".
- For **qualifiers**: locks the room, disables streaming requirement, rolls a spoiler race, sends seed publicly.
- For **bracket matches**: delegates to `super().process_tournament_race()` (standard ALTTPRTournamentRace flow).

**Seed generation:** Always a **spoiler race** using `spoilers.generate_spoiler_game('open')` with 900-second (15 min) spoiler log delay.

**Room creation:** Different settings for qualifiers vs bracket (invitational, auto_start, chat permissions).

**Overrides:** `roll()`, `configuration()`, `update_data()`, `process_tournament_race()`, `send_room_welcome()`, `create_race_room()`

---

### 3.11 `boots.py` — ALTTPR Casual Boots Tournament (`ALTTPRCASBootsTournamentRace`)

**Inherits:** `ALTTPRTournamentRace`

**Event:** Casual Boots tournament race.
**Guild:** `973765801528139837`
**Preset:** `'casualboots'`
**Minimal handler** — no audit channel, no helper roles.

**Overrides:** `roll()`, `configuration()` only.

---

### 3.12 `nologic.py` — ALTTPR No Logic (`ALTTPRNoLogicRace`)

**Inherits:** `ALTTPRTournamentRace`

**Event:** No-logic (glitched) ALTTPR tournament.
**Guild:** `535946014037901333`
**Preset:** `'nologic_rods'` with `branch='beeta'`
**Goal:** `'Beat the game (glitched)'`

**Overrides:** `roll()`, `configuration()` only.

---

### 3.13 `smbingo.py` — Super Metroid Bingo (`SMBingoTournament`)

**Inherits:** `TournamentRace` (directly — NOT an ALTTPR handler)

**Event:** Super Metroid Triple Bingo tournament.
**Guild:** `155487315530088448`
**Category:** `'sm'` / Goal: `'Triple Bingo'`

**Unique mechanics:**
- `on_room_creation()` — Creates a **BingoSync room** (game type 4, variant 4, hidden card), stores room ID + password in `TournamentResults`, posts to a Discord webhook (`BINGO_COLLAB_DISCORD_WEBHOOK`).
- `on_race_start()` — Generates a random bingo seed, unveils the card by calling `bingo.new_card(hide_card='off', seed=...)`, and posts the SRL bingo URL.
- `on_room_resume()` — Retrieves existing BingoSync room from DB if reconnecting.
- No `process_tournament_race()` override — seed generation is entirely via BingoSync, not a randomizer.

**Overrides:** `configuration()`, `send_room_welcome()`, `on_room_creation()`, `on_race_start()`, `on_room_resume()`

---

### 3.14 `smrl.py` — Super Metroid Rando League (`SMRandoLeague`)

**Inherits:** `TournamentRace` (directly)

**Event:** SM Randomizer League Season 4, with weekly rotating modes.
**Guild:** `500362417629560881`
**Category:** `'smr'` / Goal: `'Beat the game'`

**Key feature:** A global `WEEK` variable (hardcoded to 7) selects from a `WEEKS` dictionary that defines 7 different weekly race formats:

| Week | Name | Randomizer | Preset | Co-op? |
|---|---|---|---|---|
| 1 | Multiworld Major/Minor Split | `smmulti` | `tournament_split` | Yes |
| 2 | Countdown, Full Area, Vanilla Bosses | `smvaria` | `RLS4W2` | No |
| 3 | Major/Minor, Full Area, Boss Shuffle | `smvaria` | `RLS4W3` | No |
| 4 | Full Item, Vanilla Area, Boss Shuffle | `smvaria` | `RLS4W4` | Yes (co-op) |
| 5 | Chozo, Vanilla Area, Boss Shuffle | `smvaria` | `RLS4W5` | No |
| 6 | DASH Recall | `smdash` | `recall_mm` | No |
| 7 | Full Item, Full Area, Boss Shuffle | `smvaria` | `RLS4W7` | Yes (co-op) |

**Seed generation (per randomizer):**
- `smmulti` — Requires exactly 4 players, generates a multiworld via `smz3multi.generate_multiworld()` with team pairing.
- `smvaria` — Uses `SuperMetroidVariaDiscord.create()` with skills preset `"Season_Races"`.
- `smdash` — Uses `smdash.create_smdash()`.

**Overrides:** `process_tournament_race()`, `send_room_welcome()`, `configuration()`, `create_race_room()`, `send_audit_message()`

---

### 3.15 `smrl_playoff.py` — SM Rando League Playoffs (`SMRLPlayoffs`)

**Inherits:** `TournamentRace` (directly)

**Event:** Playoffs for the SM Rando League, with a fixed 5-game schedule and player-submitted settings for games 4 & 5.
**Guild:** `500362417629560881`
**Category:** `'smr'`

**Game schedule:**
1. Chozo, Vanilla Area, Boss Shuffle → `smvaria` / `RLS4W5`
2. DASH Recall → `smdash` / `recall_mm`
3. Countdown, Full Area, Boss Shuffle → `smvaria` / `RLS4GS`
4.-5. Player's choice from: `RLS4W2`, `RLS4W3`, `RLS4P1`, `classic_mm`, `RLS4P2`

**Submission form:** `"submission_smrl.html"` — players submit game number and preset choice.

**Key logic:** `create_race_room()` checks that settings have been submitted; if not, sends a warning and skips room creation.

**Overrides:** `process_tournament_race()`, `send_room_welcome()`, `configuration()`, `create_race_room()`, `process_submission_form()`, `submission_form`

---

### 3.16 `smwde.py` — Super Mario World German Tournament (`SMWDETournament`)

**Inherits:** `TournamentRace` (directly)

**Event:** German SMW hacks tournament.
**Guild:** `753727862229565612`
**Category:** `'smw-hacks'` / Goal: `'Any%'`
**Lang:** `'de'`
**Google Sheet:** `'1BrkmhNPnpjNUSUx5yGrnm09XbfAFhYDsi-7-fHp62qY'`
**Minimal handler** — only `configuration()` override. No seed rolling (presumably manual setup).

---

### 3.17 `smz3coop.py` — SMZ3 Co-op Tournament (`SMZ3CoopTournament`)

**Inherits:** `ALTTPRTournamentRace`

**Event:** Super Metroid + Zelda 3 combo randomizer co-op tournament.
**Guild:** `460905692857892865`
**Category:** `'smz3'` / Goal: `'Beat the games'`
**Preset:** `'hard'` (SMZ3 randomizer, tournament mode)
**Co-op:** Yes (`team_race=True`)

**Overrides:** `roll()`, `configuration()`, `seed_code`

---

### 3.18 `test.py` — Test Tournament (`TestTournament`)

**Inherits:** `ALTTPR2024Race`

**Purpose:** Development/testing harness. Uses a test guild (`508335685044928540`) and test category (`'test'`). Only registered in `TOURNAMENT_DATA` when `config.DEBUG` is true.

---

## 4. SpeedGaming Integration (`speedgaming.py`)

### Data Model

SpeedGaming data is modeled as frozen `dataclass_json` dataclasses:

| Class | Key Fields |
|---|---|
| `SpeedGamingPlayer` | `id`, `display_name`, `public_stream`, `streaming_from`, `discord_id`, `discord_tag` |
| `SpeedGamingCrew` | `id`, `display_name`, `language`, `discord_id`, `ready`, `partner`, `public_stream`, `approved` |
| `SpeedGamingMatch` | `id`, `note`, `players[]`, `title` |
| `SpeedGamingEvent` | `id`, `bot_channel`, `game`, `name`, `active`, `slug`, `short_name` |
| `SpeedGamingChannel` | `id`, `language`, `initials`, `name`, `slug` |
| `SpeedGamingEpisode` | `id`, `match1`, `match2`, `title`, `approved`, `when`, `when_countdown`, `event`, `channels[]`, `commentators[]`, `broadcasters[]`, `trackers[]`, `helpers[]`, `length`, `external_restream`, `timezone` |

### API Functions

**`get_upcoming_episodes_by_event(event, hours_past=4, hours_future=4)`**
- Calls `GET {SG_API_ENDPOINT}/schedule?event={event}&from={}&to={}`.
- Returns a list of raw episode dicts.
- In DEBUG mode with event `'test'`, returns artificial test data.

**`get_episode(episodeid, complete=False)`**
- Calls `GET {SG_API_ENDPOINT}/episode?id={episodeid}`.
- Returns a fully deserialized `SpeedGamingEpisode` object.
- In DEBUG mode, loads from `test_input/sg_*.json` files.

### What SG Provides to the System

- **Player identity**: `discordId`, `discordTag`, `publicStream`, `streamingFrom` → used by `TournamentRace.update_data()` to resolve `TournamentPlayer` objects.
- **Match metadata**: `match1.title` → used by several handlers (DE, Mini) to select presets.
- **Schedule timing**: `when`, `whenCountdown` → determines room open time and race start time.
- **Restream channels**: `channels[].name` → displayed in race info and embeds.
- **Crew**: `commentators`, `broadcasters`, `trackers`, `helpers` → available but mostly unused in current code.
- **Event metadata**: `event.slug`, `event.shortName` → matches against `TOURNAMENT_DATA` keys.

---

## 5. Tournament Orchestration (`tournaments.py`)

### `TOURNAMENT_DATA` Registry

A dictionary mapping event slug strings to tournament handler classes. In production:

```python
TOURNAMENT_DATA = {
    'alttpr': ALTTPRQualifierRace,      # Main tournament qualifier
    'alttprdaily': AlttprSGDailyRace,   # Daily race series
    'smz3': SMZ3DailyRace,              # SMZ3 weekly race
    'invleague': ALTTPRLeague,          # Invitational League
    'alttprleague': ALTTPROpenLeague,   # Open League
}
```

Many others are commented out (CD, DE, Mini, Boots, NoLogic, SMW DE, FR, HMG, ES, SMZ3 Coop, SM Bingo, SMRL, SGL). These are activated per-season.

In DEBUG mode: only `{'test': TestTournament}`.

### Key Functions

**`fetch_tournament_handler(event, episodeid, rtgg_handler)`**
- Calls `TOURNAMENT_DATA[event].construct(episodeid, rtgg_handler)`.
- Used when an RT.gg handler connects to an existing room.

**`fetch_tournament_handler_v2(event, episode, rtgg_handler)`**
- Same but with pre-fetched episode data.

**`create_tournament_race_room(event, episodeid)`**
- Checks if a room already exists for this episode (via `TournamentResults` DB).
- If it does and isn't cancelled, returns (idempotency guard).
- Otherwise, calls `TOURNAMENT_DATA[event].construct_race_room(episodeid)`.

**`race_recording_task()`**
- Periodic background task.
- Iterates all active events in `TOURNAMENT_DATA`.
- For each event, queries `TournamentResults` where `written_to_gsheet=None`.
- Fetches race data from RT.gg API.
- If finished: extracts winner/runner-up, formats times, appends row to Google Sheet, respects `stream_delay`.
- If cancelled: deletes the DB record.
- If `auto_record` is enabled, calls `racetime_auto_record()`.

**`racetime_auto_record(race_data)`**
- Scrapes the RT.gg race page to get a CSRF token.
- Posts to the race's `/monitor/record` endpoint to officially record the race.

---

## 6. Data Flow — Match Lifecycle

```
┌─────────────────────────┐
│   SpeedGaming Schedule  │
│   (SG API polled by     │
│    a cog/task loop)     │
└───────────┬─────────────┘
            │ get_upcoming_episodes_by_event()
            ▼
┌─────────────────────────┐
│ Is it time to open a    │
│ race room?              │
│ (room_open_time mins    │
│  before whenCountdown)  │
└───────────┬─────────────┘
            │ create_tournament_race_room(event, episodeid)
            ▼
┌─────────────────────────┐
│ TournamentRace          │
│ .construct_race_room()  │
│                         │
│ 1. configuration()      │
│ 2. update_data()        │
│    └─ get_episode()     │
│    └─ resolve players   │
│ 3. create_race_room()   │
│    └─ rtgg_bot.start()  │
│ 4. Write TournamentResults │
│ 5. Invite players       │
│ 6. send_player_room_info│
│ 7. send_room_welcome()  │
│ 8. on_room_creation()   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ RT.gg Room Active       │
│                         │
│ Player types:           │
│ !tournamentrace         │
│                         │
│ → process_tournament_   │
│   race()                │
│   1. roll()  (gen seed) │
│   2. create_embeds()    │
│   3. DM seed to players │
│   4. Post to audit ch   │
│   5. Post to commentary │
│   6. Update DB          │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Race runs and finishes  │
│                         │
│ → on_race_start()       │
│ → RT.gg tracks results  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ race_recording_task()   │
│ (periodic background)   │
│                         │
│ 1. Check stream_delay   │
│ 2. Fetch RT.gg race data│
│ 3. Write to Google Sheet│
│ 4. Mark as RECORDED     │
│ 5. Auto-record on RT.gg │
└─────────────────────────┘
```

---

## 7. Dailies / Weeklies (`dailies/` subdirectory)

The `dailies/` package contains **community race series** that reuse the tournament infrastructure but are **not** competitive tournaments. They are open-entry races announced to a public channel.

### `dailies/core.py` — `SGDailyRaceCore`

**Inherits:** `TournamentRace`

Base class for daily/weekly races. Key differences from tournament races:

- `player_racetime_ids` returns `[]` — races are open to all, no invitations.
- `create_race_room()` — Creates a **non-invitational** room. Dynamically enables `team_race` if the match title contains "co-op".
- `send_player_room_info()` — Posts to a public `announce_channel` instead of DMing individual players.
- `update_data()` — Skips player resolution entirely (no `TournamentPlayer` construction).
- Properties for `announce_message`, `race_info`, `seed_time` (10 min before start).

### `dailies/alttprdaily.py` — `AlttprSGDailyRace`

**Inherits:** `SGDailyRaceCore`

ALTTPR daily race series on the SpeedGaming community server (`307860211333595146`). Category `'alttpr'`, goal `'Beat the game - Casual'`. Room opens 60 min before start.

Also posts announcements via an SG Discord webhook (`SG_DISCORD_WEBHOOK`).

### `dailies/smz3.py` — `SMZ3DailyRace`

**Inherits:** `SGDailyRaceCore`

SMZ3 weekly race on the SMZ3 community server (`445948207638511616`). Category `'smz3'`, goal `'Beat the games'`. Room opens 60 min before start. Overrides `create_race_room()` with identical settings.

### `dailies/__init__.py`

Exports `AlttprSGDailyRace` and `SMZ3DailyRace`.

---

## Summary Table

| File | Class | Inherits | Game | Seed Source | Lang | Has Submission Form |
|---|---|---|---|---|---|---|
| `alttpr.py` | `ALTTPRTournamentRace` | `TournamentRace` | ALTTPR | (abstract) | en | No |
| `alttpr.py` | `ALTTPR2024Race` | `TournamentRace` | ALTTPR | (config only) | en | No |
| `alttpr_quals.py` | `ALTTPRQualifierRace` | `TournamentRace` | ALTTPR | `triforce_text` | en | No |
| `alttprcd.py` | `ALTTPRCDTournament` | `ALTTPRTournamentRace` | ALTTPR | Preset `crossedkeydrop` | de | No |
| `alttprde.py` | `ALTTPRDETournament` | `ALTTPRTournamentRace` | ALTTPR | Title→preset map (12 modes) | de | No |
| `alttpres.py` | `ALTTPRESTournament` | `ALTTPRTournamentRace` | ALTTPR | Form→customizer API | es | Yes |
| `alttprfr.py` | `ALTTPRFRTournament` | `ALTTPRTournamentRace` | ALTTPR | Form→raw settings | fr | Yes (granular) |
| `alttprhmg.py` | `ALTTPRHMGTournament` | `ALTTPRTournamentRace` | ALTTPR (glitched) | Preset `hmg` (live branch) | en | No |
| `alttprleague.py` | `ALTTPRLeague` | `ALTTPRTournamentRace` | ALTTPR | League API→preset | en | No (League API) |
| `alttprleague.py` | `ALTTPROpenLeague` | `ALTTPRLeague` | ALTTPR | League API→preset | en | No |
| `alttprmini.py` | `ALTTPRMiniTournament` | `ALTTPRTournamentRace` | ALTTPR | Title→preset map (5 modes) | de | No |
| `alttprsglive.py` | `ALTTPRSGLive` | `ALTTPRTournamentRace` | ALTTPR | Spoiler race `open` | en | No |
| `boots.py` | `ALTTPRCASBootsTournamentRace` | `ALTTPRTournamentRace` | ALTTPR | Preset `casualboots` | en | No |
| `nologic.py` | `ALTTPRNoLogicRace` | `ALTTPRTournamentRace` | ALTTPR (glitched) | Preset `nologic_rods` (beeta) | en | No |
| `smbingo.py` | `SMBingoTournament` | `TournamentRace` | SM | BingoSync | en | No |
| `smrl.py` | `SMRandoLeague` | `TournamentRace` | SM | SM Varia / DASH / Multi | en | No |
| `smrl_playoff.py` | `SMRLPlayoffs` | `TournamentRace` | SM | SM Varia / DASH | en | Yes (HTML form) |
| `smwde.py` | `SMWDETournament` | `TournamentRace` | SMW | None (manual) | de | No |
| `smz3coop.py` | `SMZ3CoopTournament` | `ALTTPRTournamentRace` | SMZ3 | Preset `hard` | en | No |
| `test.py` | `TestTournament` | `ALTTPR2024Race` | ALTTPR | (inherits) | en | No |
| `dailies/core.py` | `SGDailyRaceCore` | `TournamentRace` | — | — | en | No |
| `dailies/alttprdaily.py` | `AlttprSGDailyRace` | `SGDailyRaceCore` | ALTTPR | (seed via room) | en | No |
| `dailies/smz3.py` | `SMZ3DailyRace` | `SGDailyRaceCore` | SMZ3 | (seed via room) | en | No |
