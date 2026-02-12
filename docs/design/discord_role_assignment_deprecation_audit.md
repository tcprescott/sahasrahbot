# SahasrahBot — Role Assignment Components Deprecation Audit

> Last updated: 2026-02-12
> Scope: `alttprbot_discord/cogs/role.py`, `alttprbot_discord/cogs/voicerole.py`, `alttprbot/database/role.py`, `alttprbot/database/voicerole.py`, `alttprbot/models/models.py` (`ReactionGroup`, `ReactionRole`, `VoiceRole`)

Execution sequencing for this deprecation is tracked in [Discord Role Assignment Deprecation & Removal Plan](../plans/discord_role_assignment_deprecation_removal_plan.md).

## 1. Component Boundary

This audit covers the Discord role assignment features that automatically add/remove roles based on:

- Message reactions (reaction-role menus)
- Voice channel join/leave events (voice-role mapping)

In-scope runtime surfaces:

- Cog listeners and admin commands in `alttprbot_discord/cogs/role.py`
- Voice state listener in `alttprbot_discord/cogs/voicerole.py`
- Raw-SQL CRUD modules in `alttprbot/database/role.py` and `alttprbot/database/voicerole.py`
- Tortoise model definitions in `alttprbot/models/models.py`
- Extension loading in `alttprbot_discord/bot.py`
- Reaction-role embeds in `alttprbot_discord/util/embed_formatter.py`

Out-of-scope:

- Non-role Discord systems (generation, tournament, daily, inquiry, etc.)
- Audit bot moderation policies

## 2. Verified Intent (Owner-Confirmed)

The following decisions were confirmed for this deprecation effort:

- Deprecation scope includes both reaction roles and voice roles.
- Rollout target is soft deprecation now, with full removal in the next release.
- Existing data should be archived/exported before table removal.
- Replacement path should point guild admins to native Discord role/onboarding tools.

## 3. Fact vs Intent Split

### Code-observed behavior (facts)

- `Role` cog listens to `on_raw_reaction_add` and `on_raw_reaction_remove` and directly assigns/removes Discord roles when emoji mappings match database rows.
- `Role` cog exposes admin command groups `reactionrole` and `reactiongroup` with create/update/delete/list/refresh operations.
- `refresh_bot_message(...)` mutates the configured message by adding reactions and, for bot-managed groups, editing the embed body.
- `VoiceRole` cog listens to `on_voice_state_update` and adds/removes roles based on `voice_role` mappings.
- Both features use legacy raw SQL helpers instead of ORM-first patterns.
- Both cogs are loaded at startup in `alttprbot_discord/bot.py`.

### Author-confirmed rationale (intent)

- These two automated role assignment systems are planned for deprecation/removal rather than refactor retention.
- Migration messaging should steer communities toward Discord-native mechanisms.
- Data lifecycle should preserve historical mappings via export/archive before dropping tables.

## 4. Current Workflow (As Implemented)

### 4.1 Reaction-role workflow

1. Admin creates a reaction group that binds a guild/channel/message tuple.
2. Admin creates one or more emoji-to-role rows under that group.
3. Bot optionally edits the target message embed and adds emoji reactions.
4. Member adds/removes emoji reaction.
5. Listener fetches matching rows and adds/removes roles on the member.

Operational notes:

- Uses message, channel, guild, and emoji matching in SQL lookup.
- Group max is constrained to 20 roles in command layer.
- Missing roles are skipped silently at assignment time.

### 4.2 Voice-role workflow

1. Guild has persisted voice-channel-to-role mappings.
2. Member voice state changes.
3. Listener loads all guild mappings and compares `before.channel`/`after.channel`.
4. Bot applies roles when joining a mapped channel and removes when leaving one.

Operational notes:

- Configuration commands are currently commented out in the cog, but listener logic remains active.
- Mapping CRUD still exists in `alttprbot/database/voicerole.py`.

## 5. Data & Dependency Surface

Primary tables:

- `reaction_group`
- `reaction_role`
- `voice_role`

Related model classes:

- `ReactionGroup`
- `ReactionRole`
- `VoiceRole`

Cross-component dependencies:

- Runtime event listeners in Discord cogs
- Embed generation helper used by role command output
- Aerich migrations history contains schema evolution for these tables

## 6. Deprecation Risks

- Silent break risk if listeners are disabled before admin communication.
- Orphaned reaction-role menu messages may remain in guild channels after disablement.
- Stale data risk if tables are retained too long without active feature ownership.
- Permission/error visibility is limited; listener failures are not explicitly surfaced to guild admins.

## 7. Deprecation & Removal Plan

### Phase A — Soft Deprecation (current release)

- Mark both systems as deprecated in operator/developer docs.
- Add clear admin-facing command responses indicating deprecation and native Discord alternatives.
- Stop encouraging new configuration creation.

### Phase B — Functional Disablement (before next release cut)

- Disable runtime listeners for reaction and voice auto-role assignment.
- Keep explicit transitional messaging where commands still exist.
- Remove extension loading for deprecated cogs once communication window closes.

### Phase C — Data Archive + Removal (next release)

- Export `reaction_group`, `reaction_role`, and `voice_role` data for archival.
- Apply migration to remove now-unused tables and model bindings.
- Remove legacy DB helper modules and embed formatter sections that only serve deprecated role components.

## 8. Concrete Removal Checklist

- Confirm migration window and guild communication period.
- Export/archive role-assignment table contents.
- Remove `alttprbot_discord.cogs.role` extension load entry.
- Remove `alttprbot_discord.cogs.voicerole` extension load entry.
- Remove deprecated cog modules and database helper modules.
- Remove `ReactionGroup`, `ReactionRole`, and `VoiceRole` model classes once migration lands.
- Validate startup and command sync without role-assignment cogs.

## 9. Migration Target (Replacement Guidance)

For guild administrators, replacement guidance should reference Discord-native functionality:

- Server onboarding and role prompts
- Channel or server role settings managed directly in Discord
- Any existing Discord-native role assignment UX already available in the guild

This keeps SahasrahBot focused on seed/tournament/community workflows while reducing maintenance of legacy role automation code.
