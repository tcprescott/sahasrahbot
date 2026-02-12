# Plan: Discord Bot Modernization & Refactor

> **Status:** Draft
> **Last updated:** 2026-02-12
> **Target:** `alttprbot_discord` subsystems

## 1. Executive Summary
This plan addresses technical debt identified during the February 2026 audit. The goal is to move away from legacy architectural patterns (monkey-patching, name-based config) toward robust, type-safe, and resilient patterns standard in modern Python/Discord.py development.

## 2. Identified Issues & Solutions

### 2.1 Kill `Guild` Monkey-Patching
**Current State:**
`alttprbot_discord/util/guild_config.py` injects methods (`config_get`, etc.) directly onto `discord.Guild` at runtime.
**Issues:**
- Anti-pattern; obscures type hints.
- Confusing for new developers (where does `.config_get()` come from?).
- Risk of name collision with future library updates.

**Solution:**
Implement a **Configuration Service Pattern**.
- Create `class GuildConfigService`.
- Dependency Injection: Pass the service to Cogs or instantiate as a singleton helper.
- **Migration:**
  - Old: `ctx.guild.config_get("Key")`
  - New: `await config_service.get(ctx.guild.id, "Key")`

### 2.2 Migrate Config to Channel IDs
**Current State:**
Configuration keys like `DailyAnnouncerChannel` store comma-separated list of channel **names** (e.g., "daily-race").
**Issues:**
- Brittle: Renaming a channel breaks the bot silently.
- Performance: Requires iterating `guild.text_channels` to match names string-wise.

**Solution:**
- **Database Migration:** Create a script to iterate all existing configs, resolve names to IDs, and update the DB value.
- **Code Update:** Update consumers to fetch channels by ID (`guild.get_channel(id)`).
- **Validation:** Update the setters to ensure only IDs are stored.

### 2.3 Optimize Cache Invalidation
**Current State:**
Writing any config key allows invalidates the *entire* text-blob cache for that guild (`{id}_guildconfig`).
**Issues:**
- Coarse invalidation leads to unnecessary DB hits.
- Potential race conditions under high concurrency.

**Solution:**
- Adopt a structured caching key strategy.
- Only invalidate specific changed keys.
- Consider using an LRU strategy for the `config_list` equivalents if needed, or remove the need for bulk-fetching entirely.

### 2.4 Harden `daily.py` Resilience
**Current State:**
The `announce_daily` loop makes a single HTTP GET to alttpr.com. If it fails, the task likely crashes or hangs until restart.
**Issues:**
- Zero tolerance for API blips.
- No error reporting for stale dailies.

**Solution:**
- Implement the **Circuit Breaker** or **Retry** pattern (using `tenacity`).
- Add comprehensive error logging (Sentry) for recurring failures.
- Add "stale data" checks (don't re-announce old hashes if API returns cached/old data).

### 2.5 Decouple Tournament Logic from Discord (Decoupling)
**Current State:**
Tournament classes (`TournamentRace`) import `discord` directly and construct `Embed` objects within their logic.
**Issues:**
- High Coupling: Cannot run tournament logic without Discord (e.g., for testing or CLI).
- Violation of Single Responsibility Principle.

**Solution:**
- **Full Abstraction:** Create `INotificationService` interface.
- Implement `DiscordNotificationAdapter`.
- Tournament logic calls `notify_race_start(...)` instead of building embeds.

### 2.6 Extract Hardcoded Tournament Configs
**Current State:**
Classes like `ALTTPRTournamentRace` contain hardcoded `TournamentConfig` methods returning direct IDs.
**Issues:**
- Requires code deploy to change a channel ID.
- Config is buried in Python class definitions.

**Solution:**
- **Static Config Migration:** Move tournament definitions to `config/tournaments.yaml` (or JSON). This should cover not only IDs (guild/channel/role) but also stable per-event mappings/rules currently embedded in code (e.g., title→preset maps, week schedules) where appropriate.
- Load at runtime via a `TournamentConfigLoader`.

### 2.7 Generic Event Schema
**Current State:**
Database tables `ReactionRole` and `VoiceRole` capture Discord-specific concepts tightly.
**Issues:**
- inflexible; hard to add "Message Edit" or "Member Join" triggers without new tables.

**Solution:**
- **Generic Events:** Refactor to `EventTrigger` (Type: Reaction, Voice, etc.) and `EventAction` (Assign Role, Send Message) tables.

## 3. Implementation Phases

### Phase 1: Foundation (Safety & Services)
- [ ] **Resilience:** Refactor `daily.py` with `tenacity` retries.
- [ ] **Config Service:** Create `GuildConfigService` to replace monkey-patching.
- [ ] **Pilot:** Migrate `daily.py` to use `GuildConfigService`.
- [ ] **Cleanup:** Remove `guild_config.py` patching once all Cogs are migrated.

### Phase 2: Data Normalization
- [ ] **Channel IDs:** Write migration script to convert Channel Names -> IDs in DB.
- [ ] **External Config:** Create `config/tournaments.yaml` schema.
- [ ] **Migration:** Extract hardcoded IDs and stable per-event mappings/rules from `alttprbot/tournament/*.py` into YAML.
- [ ] **Loader:** Implement `TournamentConfigLoader` to read YAML at startup.

### Phase 3: Core Abstraction (The Adapter)
- [ ] **Interface:** Define `INotificationService` protocol/ABC (methods: `send_dm`, `announce_race`, `update_bracket`).
- [ ] **Adapter:** Implement `DiscordNotificationService` using `discord.py` (relocating logic from `TournamentRace`).
- [ ] **Refactor:** Update `TournamentRace` to use `INotificationService` instead of `discord` directly.
- [ ] **Test:** Create a `MockNotificationService` for CLI/Test runs.

### Phase 4: Generic Events (DB Refactor)
- [ ] **Design:** Draft schema for `EventTrigger` and `EventAction`.
- [ ] **Migration:** Write script to migrate `ReactionRole` and `VoiceRole` data to new tables.
- [ ] **Implementation:** specialized Managers for handling Generic Events in Discord.
- [ ] **Deprecation:** Drop old tables.

## 4. Verification
- **Tests:** Unit tests for `GuildConfigService` and `TournamentConfigLoader`.
- **Integration:** Verify `MockNotificationService` allows running a "race" without a Discord token.
- **Manual:** Verify `daily` announcements continue during API maintenance windows.

