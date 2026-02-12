# SahasrahBot — Discord Bot Domain Analysis

> **Generated:** 2026-02-11  
> **Scope:** `alttprbot_discord/` (main bot) and `alttprbot_audit/` (audit bot)

---

## 1. Overview

SahasrahBot is a Discord bot ecosystem built with **discord.py 2.x** (with app commands / slash commands) for the **ALTTPR (A Link to the Past Randomizer)**, **Super Metroid**, and **SMZ3 (combo randomizer)** speedrunning communities. It was originally written around 2019 and has been incrementally updated to use modern discord.py features (slash commands, UI views, modals).

The system runs **two separate Discord bot instances** from a single codebase, started concurrently via `sahasrahbot.py`:

1. **Main Bot** (`alttprbot_discord/`) — The primary user-facing bot handling seed generation, tournament management, daily challenges, multiworld coordination, and community tools.
2. **Audit Bot** (`alttprbot_audit/`) — A separate bot focused on message logging, moderation, and anti-phishing. Runs under a different Discord token (`AUDIT_DISCORD_TOKEN`).

Both bots share the same database (MySQL via Tortoise ORM), models, and utility libraries. They are started alongside a RaceTime.gg bot and a Quart API server, all in the same event loop.

### Startup Flow

```
sahasrahbot.py
├── Tortoise ORM init (MySQL)
├── start_discord_bot()          ← main Discord bot
├── start_audit_bot()            ← audit Discord bot
├── start_racetime()             ← RaceTime.gg bot
└── sahasrahbotapi.run()         ← Quart web API
```

---

## 2. Bot Architecture

### 2.1 Main Bot (`alttprbot_discord/bot.py`)

| Property | Value |
|---|---|
| **Framework** | `discord.py 2.x` with `commands.Bot` |
| **Command Prefix** | `$` (or `@mention`) |
| **Intents** | Default + Members |
| **Allowed Mentions** | Users only (no @everyone, no @role) |
| **Error Reporting** | Sentry (via `discord_sentry_reporting`) |
| **Debug Extension** | `jishaku` (loaded for REPL/debug) |

**Events:**
- `on_command` — Adds ⌚ reaction to indicate processing.
- `on_command_completion` — Adds ✅ reaction, removes ⌚.
- `on_ready` — Syncs the app command tree globally and per-guild.

**Extension Loading Order:**
1. `errors` — Global error handler (loaded first)
2. `daily` — Daily challenge announcer
3. `discord_servers` — Server list management
4. `misc` — General-purpose commands
5. `nickname` (renamed `racetime_tools` internally) — RaceTime.gg admin tools
6. `racetime_tools` — Racetime watcher/notifications
7. `role` — Reaction role system
8. `sgdailies` — SpeedGaming daily schedule
9. `tournament` — Tournament race management
10. `voicerole` — Voice channel auto-roles
11. `smmulti` — SM/SMZ3 multiworld sessions
12. `generator` — Seed generation (ALTTPR, SM, SMZ3, Varia, Dash, CT:JoT, Z2R)
13. `inquiry` — Private inquiry threads
14. `rankedchoice` — Ranked-choice voting
15. `asynctournament` — Async qualifier tournaments
16. `doorsmw` — ALTTP Door Randomizer multiworld
17. `racer_verification` — Racer eligibility verification
18. `test` — Debug-only empty cog (loaded when `config.DEBUG`)

**Disabled cogs** (commented out): `bontamw` (legacy multiworld), `admin` (display name fixer).

### 2.2 Audit Bot (`alttprbot_audit/bot.py`)

| Property | Value |
|---|---|
| **Token** | `AUDIT_DISCORD_TOKEN` (different from main bot) |
| **Prefix** | Dynamic per-guild (via `guild.config_get("CommandPrefix", "$")`) |
| **Intents** | `discord.Intents.all()` (requires privileged intents for message content) |

**Extensions:**
1. `audit` — Message logging, edit/delete tracking, member join/leave/ban
2. `moderation` — Anti-phishing, ROM detection, new-user link restriction

### 2.3 Shared Infrastructure

Both bots use:
- **Guild Config** (`util/guild_config.py`) — Monkey-patches `discord.Guild` with `config_get`, `config_set`, `config_delete`, and `config_list` methods backed by the `Config` model with in-memory caching via `aiocache`.
- **Tortoise ORM models** (`alttprbot.models`) — Shared data layer.
- **Sentry** — Error tracking (both bots report to the same DSN if configured).

---

## 3. Cogs Inventory — Main Bot

### 3.1 `errors` (Errors)

**Type:** Cog (no user commands)  
**Purpose:** Centralized error handler for all command types.

**Listeners:**
| Listener | Description |
|---|---|
| `on_error` | Catches unexpected internal errors |
| `on_command_error` | Handles prefix command errors with a comprehensive error hierarchy |
| `on_app_command_error` | Handles slash command errors |
| `on_view_error` | Handles UI View errors |
| `on_modal_error` | Handles Modal errors |

Uses the custom emoji `RIPLink` :RIPLink: as an error indicator. Provides user-friendly error messages for each discord.py exception type (missing permissions, bad arguments, cooldowns, etc.).

**Dependencies:** None external.

---

### 3.2 `daily` (Daily)

**Type:** Cog  
**Purpose:** Announces the daily ALTTPR challenge from alttpr.com.

**Commands:**
| Command | Type | Description |
|---|---|---|
| `/dailygame` | Slash | Returns the current daily challenge seed with an embed |

**Background Tasks:**
| Task | Interval | Description |
|---|---|---|
| `announce_daily` | 5 min | Checks for new daily hash; if new, posts embed to all configured `DailyAnnouncerChannel` channels and creates a thread |

**Dependencies:** `alttpr.com` API, `ALTTPRDiscord` (pyz3r wrapper), `aiocache`, `aiohttp`, Tortoise ORM (`Daily`, `Config` models).

---

### 3.3 `discord_servers` (DiscordServers)

**Type:** GroupCog (`/discordservers`)  
**Purpose:** Manages categorized lists of Discord server invites posted to channels.

**Commands (all admin-only, guild-only):**
| Command | Description |
|---|---|
| `/discordservers add_category` | Add a new category to a channel |
| `/discordservers list_category` | List all categories |
| `/discordservers remove_category` | Remove a category by ID |
| `/discordservers update_category` | Update a category |
| `/discordservers add_server` | Add a server invite to a category |
| `/discordservers list_servers` | List servers in a category |
| `/discordservers remove_server` | Remove a server by ID |
| `/discordservers update_server` | Update a server invite |
| `/discordservers refresh` | Purge and re-post all server lists |

**Dependencies:** Tortoise ORM (`DiscordServerCategories`, `DiscordServerLists` models).

---

### 3.4 `misc` (Misc)

**Type:** Cog  
**Purpose:** General-purpose community commands.

**Commands:**
| Command | Type | Guilds | Description |
|---|---|---|---|
| `/welcome` | Slash | ALTTP Randomizer servers only | Posts a welcome message in French, Spanish, German, or Portuguese |
| `/rom` | Slash | ALTTP Randomizer servers only | Posts ROM verification instructions |
| `/holyimage` | Slash | Global | Retrieves a "holy image" from alttp.mymm1.com (with autocomplete for game and slug) |
| `/datetime` | Slash | Global | Converts a date/time to all Discord timestamp markdown formats |

**Listeners:**
| Listener | Description |
|---|---|
| `on_message` | When the bot is @mentioned, reacts with the `SahasrahBot` custom emoji after a random delay |

**Dependencies:** `HolyImage` utility, `aiohttp` (holy images JSON), `pytz` (timezone conversion).

---

### 3.5 `nickname` (RtggAdmin)

**Type:** GroupCog (`/rtggadmin`)  
**Purpose:** RaceTime.gg account linkage admin tools.

**Commands:**
| Command | Description |
|---|---|
| `/rtggadmin blast` | DMs all members of a role who haven't linked their RT.gg account, urging them to verify |
| `/rtggadmin report` | Lists members of a role who haven't linked their RT.gg account |

**Dependencies:** `Users` model, `APP_URL` config.

---

### 3.6 `racetime_tools` (RacetimeTools)

**Type:** Cog (no user commands)  
**Purpose:** Monitors RaceTime.gg races via custom events dispatched by the racetime bot and sends notifications to Discord.

**Listeners:**
| Listener | Description |
|---|---|
| `on_racetime_open` | (no-op) |
| `on_racetime_invitational` | (no-op) |
| `on_racetime_in_progress` | Checks for watchlisted and new players |
| `on_racetime_cancelled` | (no-op) |
| `on_racetime_finished` | (no-op) |

**Features:**
- **Watchlisted Players** — If a watchlisted player enters a race, posts an alert embed to a configured channel.
- **New Players** — If a racer with 0 previous races enters, posts a welcome embed.

**Dependencies:** `RTGGWatcherPlayer`, `RTGGWatcher` models, `aiohttp` (RaceTime.gg user data API).

---

### 3.7 `role` (Role)

**Type:** Cog  
**Purpose:** Full reaction-role system: users react to messages to self-assign roles.

**Commands (prefix-based, requires `manage_roles`):**
| Command | Aliases | Description |
|---|---|---|
| `$reactionrole create` | `$rr c` | Create a role mapping (emoji → role) within a group |
| `$reactionrole update` | `$rr u` | Update a role mapping |
| `$reactionrole delete` | `$rr del` | Delete a role mapping |
| `$reactionrole list` | `$rr l` | List roles in a group |
| `$reactiongroup create` | `$rg c` | Create a reaction group (a message the bot manages) |
| `$reactiongroup update` | `$rg u` | Update a group's name/description |
| `$reactiongroup refresh` | `$rg r` | Refresh the bot's embed on the group message |
| `$reactiongroup delete` | `$rg d` | Delete a group |
| `$reactiongroup list` | `$rg l` | List groups |
| `$importroles` | — | Bulk import role assignments from a CSV attachment |

**Listeners:**
| Listener | Description |
|---|---|
| `on_raw_reaction_add` | Assigns the mapped role when a user reacts |
| `on_raw_reaction_remove` | Removes the mapped role when a user unreacts |

**Dependencies:** `alttprbot.database.role` (raw SQL module), `embed_formatter` utility.

---

### 3.8 `sgdailies` (SgDaily)

**Type:** Cog  
**Purpose:** Retrieves SpeedGaming daily race schedule.

**Commands:**
| Command | Guilds | Description |
|---|---|---|
| `/sgdaily` | ALTTP Randomizer servers only | Shows upcoming SG daily races (1-8 days out) with times, modes, and broadcast channels |

**Dependencies:** `alttprbot.util.speedgaming` (SpeedGaming API wrapper).

---

### 3.9 `tournament` (Tournament)

**Type:** Cog  
**Purpose:** The core tournament management system. Automates race room creation, race recording, scheduling, and seed generation for ALTTPR/community tournaments.

**Background Tasks:**
| Task | Interval | Description |
|---|---|---|
| `create_races` | 5 min | Scans SpeedGaming schedule; creates RT.gg race rooms for upcoming tournament episodes |
| `record_races` | 15 min | Records finished tournament race results |
| `week_races` | 15 min | Sends submission forms, creates/updates Discord Scheduled Events, updates scheduling needs |
| `find_races_with_bad_discord` | 4 hours | Reports players whose Discord ID cannot be resolved in the guild |

**Commands:**
| Command | Guilds | Description |
|---|---|---|
| `/cc2023` | CC Tournament servers | Generate a seed for the 2023 Challenge Cup with deck-based mode selection |
| `/tournament_deck` | CC + Main Tournament servers | Generate a hypothetical deck for a matchup (no seed, no history write) |

**UI Views:**
- `ChallengeCupDeleteHistoryView` — Persistent view with a "Delete from Tournament History" button (admin-only).

**Key Features:**
- Integrates with SpeedGaming API for episode scheduling.
- Creates Discord Scheduled Events automatically for upcoming matches.
- Posts "scheduling needs" (commentators, trackers, broadcasters needed) to a configured channel.
- Validates player Discord IDs against SpeedGaming data.

**Dependencies:** `alttprbot.tournaments` (tournament handler registry), `alttprbot.tournament.core` (tournament config), `alttprbot.tournament.alttpr` (seed rolling with deck system), `speedgaming` utility, `TournamentPresetHistory`, `ScheduledEvents`, `TournamentGames` models.

---

### 3.10 `voicerole` (VoiceRole)

**Type:** Cog  
**Purpose:** Automatically assigns/removes a Discord role when a member joins/leaves a voice channel.

**Listeners:**
| Listener | Description |
|---|---|
| `on_voice_state_update` | Checks configured voice channel→role mappings; adds/removes roles accordingly |

**Commands:** None currently active (slash command stubs are commented out).

**Dependencies:** `alttprbot.database.voicerole` (raw SQL module).

---

### 3.11 `smmulti` (SMMulti)

**Type:** Cog  
**Purpose:** Interactive multiworld game session management for SM and SMZ3 randomizers.

**Commands:**
| Command | Description |
|---|---|
| `/multiworld` | Stub redirecting to `/smmulti` |
| `/smmulti` | Creates an interactive multiworld signup embed with UI components |

**UI Views (Persistent):**
- `MultiworldSignupView` — Full interactive view with:
  - **Randomizer dropdown** (smz3/sm) — Owner only
  - **Preset dropdown** — Owner only, populated based on randomizer choice
  - **Join button** — Any user
  - **Leave button** — Any user
  - **Start button** — Owner only; generates the multiworld game and DMs all players the game room URL
  - **Cancel button** — Owner only

**Dependencies:** `alttprbot.alttprgen.smz3multi.generate_multiworld`, `slugify`, `Multiworld` and `MultiworldEntrant` models.

---

### 3.12 `generator` (Generator / AlttprGenerator / AlttprUtils / Z2RGenerator)

**Type:** Multiple GroupCogs registered from one file  
**Purpose:** The primary seed generation engine. Supports multiple randomizers.

This file registers **4 cog classes:**

#### AlttprGenerator (`/alttpr`)
| Command | Description |
|---|---|
| `/alttpr preset` | Generate an ALTTPR seed from a named preset (with autocomplete) |
| `/alttpr custompreset` | Generate from a user-uploaded YAML file; saves as a personal preset |
| `/alttpr spoiler` | Generate a spoiler race seed from a preset |
| `/alttpr customspoiler` | Generate a spoiler race from a user-uploaded YAML |
| `/alttpr mystery` | Generate a mystery game from a named weightset |
| `/alttpr custommystery` | Generate a mystery game from a user-uploaded YAML |
| `/alttpr kisspriest` | Generate a batch of "Kiss Priest" games (series of 1-10 seeds) |

#### AlttprUtils (`/alttprutils`)
| Command | Description |
|---|---|
| `/alttprutils convertcustomizer` | Convert an ALTTPR customizer JSON save to a SahasrahBot YAML preset |
| `/alttprutils savepreset` | Save a preset YAML to the user's personal namespace |
| `/alttprutils verifygame` | Verify a game hash was generated by SahasrahBot (checks audit log) |

#### Generator (top-level commands)
| Command | Description |
|---|---|
| `/sm` | Generate a Super Metroid Randomizer seed (sm.samus.link) |
| `/smz3` | Generate an SM+ALTTP Combo Randomizer seed (samus.link) |
| `/smvaria` | Generate a Super Metroid Varia Randomizer seed (varia.run) |
| `/smdash` | Generate a Super Metroid Dash Randomizer seed (dashrando.net) |
| `/ctjets` | Generate a Chrono Trigger: Jets of Time seed (ctjot.com) |

#### Z2RGenerator (`/z2r`)
| Command | Description |
|---|---|
| `/z2r preset` | Generate a Zelda 2 Randomizer seed from a preset |
| `/z2r mrb` | Generate a random flag from MRB's pool of 11 flags |

**Dependencies:** `pyz3r` (ALTTPR Python library), `alttprbot.alttprgen.generator` (preset system), `alttprbot.alttprgen.smvaria`, `alttprbot.alttprgen.randomizer.smdash`, `alttprbot.alttprgen.randomizer.z2r`, `alttprbot.alttprgen.spoilers`, `AuditGeneratedGames` model, `ALTTPRDiscord` wrapper.

---

### 3.13 `inquiry` (Inquiry)

**Type:** Cog  
**Purpose:** Creates an inquiry system where users can open private threads with a designated staff role.

**Commands:**
| Command | Description |
|---|---|
| `/inquiry` | Posts a message with a 📬 button. Requires manage_threads permission. Validates channel permissions. |

**UI Views (Persistent):**
- `ConfirmInquiryThread` — Button that opens a confirmation flow.
- `OpenInquiryThread` — Confirmation "Yes!" button.
- `OpenInquiryModal` — Modal asking for a brief summary. Creates a private thread, adds the user and all role members, posts the summary.

**Dependencies:** `InquiryMessageConfig` model.

---

### 3.14 `rankedchoice` (RankedChoice)

**Type:** GroupCog (`/rankedchoice`)  
**Purpose:** Ranked-choice voting system for community elections.

**Commands:**
| Command | Description |
|---|---|
| `/rankedchoice create` | Create a new election with title, candidates (comma-separated), seats, optional voter role restriction |

**UI Views (Persistent):**
- `RankedChoiceMessageView` — "End Election" button (owner-only). Calculates results using ranked-choice algorithm and updates the post.

**Dependencies:** `alttprbot.util.rankedchoice` (election logic, result calculation), `RankedChoiceElection`, `RankedChoiceCandidate`, `RankedChoiceVote` models, `APP_URL` config.

---

### 3.15 `asynctournament` (AsyncTournament)

**Type:** GroupCog (`/async`)  
**Purpose:** Full async (asynchronous) tournament qualifier system. The most complex cog (~1289 lines). Players play seeds on their own schedule; times are recorded and scored.

**Commands:**
| Command | Description |
|---|---|
| `/async create` | Create a new async tournament (owner-only). Seeds are auto-generated from presets. |
| `/async addseed` | Add seeds to an existing pool (owner-only) |
| `/async done` | Finish the current in-progress race |
| `/async close` | Close a tournament permanently |
| `/async repost` | Repost the tournament embed |
| `/async extendtimeout` | Extend the start timeout for a pending run (admin/mod) |
| `/async permissions` | Grant admin/mod permissions to a role or user |
| `/async live_race_record` | Record results of a live qualifier race from RaceTime.gg |
| `/async calculate_scores` | Recalculate scores (admin-only) |
| `/async update_run` | Administratively fix a run's status, time, or VOD |
| `/async test` | (DEBUG only) Populate test data |

**Background Tasks:**
| Task | Interval | Description |
|---|---|---|
| `timeout_warning_task` | 60s | Warns runners 10 min before forfeit; auto-forfeits if timeout exceeded |
| `timeout_in_progress_races_task` | 60s | Auto-forfeits races running longer than 12 hours |
| `score_calculation_task` | 1 hour | Recalculates scores for all active tournaments |

**UI Views (Persistent):**
- `AsyncTournamentView` — "Start new async run" button. Validates account age, RT.gg linkage, pool eligibility.
- `AsyncTournamentRaceViewReady` — "Ready" button that starts a 10-second countdown.
- `AsyncTournamentRaceViewInProgress` — "Finish", "Forfeit", and "Get timer" buttons.
- `AsyncTournamentPostRaceView` — "Submit Run Information" button (opens VOD/notes modal or IGT/collection rate modal depending on tournament customization).

**Modals:**
- `SubmitVODModal` — VOD link + runner notes.
- `SubmitCollectIGTModal` — Collection rate + IGT (for GMPMT2023 customization).

**Dependencies:** `alttprbot.util.asynctournament` (scoring, test data), `alttprbot.util.triforce_text`, `alttprbot_api.util.checks`, `alttprbot.alttprgen.generator`, `aiohttp` (RaceTime.gg data API), `isodate`, `pytz`, `slugify`, extensive model usage (`AsyncTournament`, `AsyncTournamentRace`, `AsyncTournamentPermalinkPool`, `AsyncTournamentPermalink`, `AsyncTournamentLiveRace`, `AsyncTournamentAuditLog`, `AsyncTournamentPermissions`, `Users`).

---

### 3.16 `doorsmw` (DoorsMultiworld)

**Type:** GroupCog (`/doorsmw`)  
**Purpose:** ALTTP Door Randomizer multiworld hosting via a local HTTP server (port 5002).

**Commands:**
| Command | Description |
|---|---|
| `/doorsmw host` | Create a new multiworld host from an uploaded multidata file |
| `/doorsmw resume` | Resume a previously closed game by token |
| `/doorsmw kick` | Kick a player (with autocomplete) |
| `/doorsmw close` | Close a game |
| `/doorsmw forfeit` | Forfeit a player (with autocomplete) |
| `/doorsmw send` | Send an item to a player (with autocomplete for player and item) |
| `/doorsmw password` | Set a game password |
| `/doorsmw msg` | Send a message to the multiworld server |

**Dependencies:** `aiohttp` (local multiworld service at `localhost:5002`), `MULTIWORLDHOSTBASE` config.

---

### 3.17 `racer_verification` (RacerVerification)

**Type:** GroupCog (`/racerverification`)  
**Purpose:** Automated racer verification system. Checks a player's race history on RaceTime.gg and/or ALTTPR Ladder to determine eligibility for a role.

**Commands:**
| Command | Description |
|---|---|
| `/racerverification create_or_update` | Create or update a verification rule (admin-only). Configures: role, RT.gg categories, ladder inclusion, minimum races, time period, reverification period, revoke behavior. |
| `/racerverification reverify` | Manually trigger reverification for all verified racers (admin-only) |

**UI Views (Persistent):**
- `RacerVerificationView` — "Verify your status" button. Checks RT.gg link, counts races, assigns role if eligible.

**Background Tasks:**
| Task | Interval | Description |
|---|---|---|
| `reverify_racer` | 24 hours | Re-checks all verified racers; revokes role if no longer eligible (currently disabled via comment) |

**Dependencies:** `aiohttp` (RaceTime.gg API, ALTTPR Ladder API, Ladder Archive API), `RacerVerification`, `VerifiedRacer`, `Users` models, `isodate`, `pytz`.

---

### 3.18 `test` (Test)

**Type:** Cog (empty)  
**Purpose:** Debug-only placeholder cog. Loaded only when `config.DEBUG` is true.

---

### 3.19 Disabled Cogs

#### `admin` (Admin) — Commented out in bot.py
**Commands:** `/admin fixnames` — Updates display names in the Users table for records missing them. Owner-only.

#### `bontamw` (BontaMultiworld) — Commented out in bot.py
**Purpose:** Legacy multiworld hosting via Bonta's implementation (port 5000). Predecessor to `doorsmw`.  
**Commands:** `$mwhost` (host), `$mwmsg` (send command), `$mwresume` (resume game). All prefix-based.

---

## 4. Audit Bot

The audit bot runs as a **separate Discord bot instance** under `AUDIT_DISCORD_TOKEN` with full intents (including message content). It has two cogs:

### 4.1 `audit` (Audit)

**Purpose:** Comprehensive message and member event logging.

**Commands (prefix-based, requires `manage_messages`):**
| Command | Description |
|---|---|
| `$messagehistory <member> [limit]` | Export a member's message history as CSV (last 30 days) |
| `$deletedhistory <member> [limit]` | Export a member's deleted message history as CSV |

**Listeners:**
| Listener | Description |
|---|---|
| `on_message` | Records every non-bot message to the database |
| `on_raw_message_delete` | Posts a deletion embed to the audit channel; marks message as deleted in DB |
| `on_raw_bulk_message_delete` | Same as above but for bulk deletions |
| `on_raw_message_edit` | Compares old vs new content; posts an edit embed to the audit channel; records new version |
| `on_member_join` | Posts a "Member Joined" embed to the audit channel |
| `on_member_remove` | Posts a "Member Left" embed to the audit channel |
| `on_member_ban` | Posts a "Member Banned" embed to the audit channel |

**Background Tasks:**
| Task | Interval | Description |
|---|---|---|
| `clean_history` | 24 hours | Deletes message records older than 30 days |

**Configuration:** Uses `AuditLogging` and `AuditLogChannel` guild config parameters.

**Dependencies:** `AuditMessages` model.

### 4.2 `moderation` (Moderation)

**Purpose:** Automated content moderation.

**Features (all via `on_message` listener):**
| Feature | Description |
|---|---|
| **New user link restriction** | Members who joined < 24 hours ago cannot post Discord invite links |
| **Executable file blocking** | Blocks uploads of `.bat`, `.exe`, `.sh`, `.py` from new users |
| **Phishing link detection** | Hashes URLs against Discord's bad-domains list; deletes message and times out user for 30 minutes |
| **ROM detection** | Deletes `.sfc`/`.smc` files and ZIP archives containing them |

Exempt users: bots, administrators, moderators, and users with `manage_guild` permission.

**Dependencies:** `aiohttp` (Discord bad-domains hash list), `urlextract`, `zipfile`, `aiocache` (1-hour TTL on phishing hashes).

---

## 5. Key Dependencies

### External Services

| Service | Used By | Purpose |
|---|---|---|
| **alttpr.com API** | `daily`, `generator` | Daily challenges, seed generation |
| **SpeedGaming API** (`speedgaming.org/api`) | `sgdailies`, `tournament` | Tournament episode schedules |
| **RaceTime.gg** (`racetime.gg`) | `racetime_tools`, `racer_verification`, `asynctournament` | Race data, player stats, race room creation |
| **ALTTPR Ladder** (`alttprladder.com`) | `racer_verification` | Ladder race history |
| **sm.samus.link / samus.link** | `generator` | SM/SMZ3 seed generation |
| **varia.run** | `generator` | SM Varia seed generation |
| **dashrando.net** | `generator` | SM Dash seed generation |
| **ctjot.com** | `generator` | Chrono Trigger: Jets of Time seed generation |
| **alttp.mymm1.com** | `misc` | Holy images |
| **Discord CDN** | `moderation` | Bad-domains hash list |
| **Google Sheets API** | Config-level (service account) | Tournament results |
| **AWS S3** | Config-level | Spoiler log storage |
| **Sentry** | Both bots | Error tracking |

### Local Services

| Service | Port | Used By | Purpose |
|---|---|---|---|
| Multiworld Host (Doors) | 5002 | `doorsmw` | Door randomizer multiworld game server |
| Multiworld Host (Bonta) | 5000 | `bontamw` (disabled) | Legacy multiworld game server |
| SahasrahBot API | 5001 | Various (auth, web UI) | Web API for RT.gg verification, elections, async tournament management |

### Python Libraries

| Library | Purpose |
|---|---|
| `discord.py` 2.x | Discord bot framework |
| `pyz3r` | ALTTPR seed generation and customizer tools |
| `tortoise-orm` | Async MySQL ORM |
| `aiohttp` | HTTP client for API calls |
| `aiocache` | In-memory caching |
| `html2markdown` | Converting HTML notes to markdown |
| `pytz` / `isodate` / `dateutil` | Date/time handling |
| `python-slugify` | Slug generation for thread names, player names |
| `urlextract` | URL extraction from messages |
| `jishaku` | Debug/REPL extension for discord.py |
| `discord_sentry_reporting` | Sentry integration for discord.py |
| `sentry_sdk` | Sentry error tracking |
| `pyyaml` | YAML preset file parsing |

---

## 6. Configuration

All configuration is in `config.py` (loaded at module level, not via environment variables in the checked-in file).

### Discord-Specific Config Values

| Parameter | Description |
|---|---|
| `DISCORD_TOKEN` | Main bot token |
| `AUDIT_DISCORD_TOKEN` | Audit bot token |
| `DISCORD_CLIENT_ID` | OAuth client ID |
| `DISCORD_CLIENT_SECRET` | OAuth client secret |
| `ALTTP_RANDOMIZER_SERVERS` | Comma-separated guild IDs where ALTTPR-specific commands are available |
| `MAIN_TOURNAMENT_SERVERS` | Guild IDs for main tournament commands |
| `CC_TOURNAMENT_SERVERS` | Guild IDs for Challenge Cup commands |
| `CC_TOURNAMENT_AUDIT_CHANNELS` | Channel ID for CC audit logging |

### External Service Config

| Parameter | Description |
|---|---|
| `ALTTPR_BASEURL` | Base URL for ALTTPR API |
| `ALTTPR_USERNAME` / `ALTTPR_PASSWORD` | Optional auth for ALTTPR API |
| `SG_API_ENDPOINT` | SpeedGaming API endpoint |
| `RACETIME_*` | RaceTime.gg host, port, tokens, OAuth credentials |
| `OOTR_API_KEY` | OoT Randomizer API key |
| `GSHEET_API_OAUTH` | Google service account credentials |

### Storage & Infrastructure

| Parameter | Description |
|---|---|
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASS` | MySQL database connection |
| `APP_URL` | Base URL for the web API |
| `SPOILERLOGURLBASE` / `AWS_SPOILER_BUCKET_NAME` | S3 spoiler log storage |
| `SAHASRAHBOT_BUCKET` | General S3 bucket |
| `MULTIWORLDHOSTBASE` | Hostname for multiworld connections |
| `SENTRY_URL` | Sentry DSN (null to disable) |
| `ALTTP_ROM` / `SM_ROM` | ROM file paths for local generation |
| `ENEMIZER_HOME` / `DOOR_RANDO_HOME` | Tool installation paths |
| `DEBUG` | Enables debug mode (test guild sync, test cog, fast task loops) |

### Per-Guild Config (Dynamic, via `guild.config_get`)

| Parameter | Description |
|---|---|
| `CommandPrefix` | Custom prefix for the audit bot |
| `DailyAnnouncerChannel` | Channel(s) to announce daily challenges |
| `AuditLogging` | Enable/disable audit logging (`true`/`false`) |
| `AuditLogChannel` | Channel ID for audit log embeds |
| `TournamentEnabled` | Enable tournament commands for a guild |
| `HolyImageDefaultGame` | Default game for `/holyimage` |

---

## 7. Utility Modules (`alttprbot_discord/util/`)

| Module | Purpose |
|---|---|
| `guild_config.py` | Monkey-patches `discord.Guild` with config CRUD methods backed by DB + aiocache |
| `checks.py` | Command check decorators: restrict to channels by config, restrict globally, channel ID/name checks |
| `embed_formatter.py` | Helpers to build embeds for config display, reaction role menus, and reaction group listings |
| `alttpr_discord.py` | `ALTTPRDiscord` — Subclass of `pyz3r.ALTTPR` that adds `embed()` method with Discord emoji file-select codes and rich metadata |
| `sm_discord.py` | `SMDiscord` / `SMZ3Discord` — Subclasses of `pyz3r.sm.smClass` with `embed()` methods |
| `smvaria_discord.py` | `SuperMetroidVariaDiscord` — Subclass of `pyz3r.smvaria.SuperMetroidVaria` with `embed()` |
| `alttprdoors_discord.py` | `AlttprDoorDiscord` — Subclass of `AlttprDoor` with `embed()` and `tournament_embed()` methods |
| `avianart_discord.py` | `AVIANARTDiscord` — Subclass of `AVIANART` with `embed()` and `tournament_embed()` methods |

Each Discord wrapper class maps item/code names to custom emoji names (e.g., `'Bow' → 'Bow'`, `'Boots' → 'GoFast'`) to render file select codes as emoji in embeds.
