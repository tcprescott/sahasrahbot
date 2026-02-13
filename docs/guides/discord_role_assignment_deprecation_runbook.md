# Discord Role Assignment Deprecation Runbook

> **Status:** Phase A/B Complete (Soft Deprecation + Functional Disablement Path)  
> **Last Updated:** 2026-02-12  
> **Single Owner:** Maintainer

## Overview

This runbook covers the deprecation and removal of Discord role-assignment automation features (reaction-roles and voice-roles) from SahasrahBot.

## Feature Flags

### `DISCORD_ROLE_ASSIGNMENT_ENABLED`

**Type:** Boolean  
**Default:** `True` (backward compatible during Phase A/B)  
**Purpose:** Controls runtime behavior of role-assignment features

**Behavior:**
- `True` (default): Role assignment features work normally with deprecation warnings
- `False`: Disables all role-assignment automation (listeners inactive, commands show disabled message)

**Configuration:**
```python
# In config.py (or environment variables)
DISCORD_ROLE_ASSIGNMENT_ENABLED = True   # Features enabled with deprecation warnings (default)
DISCORD_ROLE_ASSIGNMENT_ENABLED = False  # Features disabled, extensions not loaded
```

## Current Phase Status

### Phase A - Soft Deprecation ✅ COMPLETE

**Implementation:**
- Deprecation banners added to all reaction-role command responses
- Deprecation banners added to voice-role listener (commands are commented)
- User-facing messaging directs admins to Discord-native role tools
- Commands remain functional with warnings

**What Admins See:**
```
⚠️ DEPRECATION NOTICE ⚠️

The reaction-role feature is deprecated and will be removed in a future release.

Recommended Migration: Use Discord's native role assignment features:
• Server Settings → Onboarding (for new member roles)
• Channel/Server role settings
• Discord's built-in role management tools

All existing reaction-role configurations will be archived before removal.
```

### Phase B - Functional Disablement Path ✅ COMPLETE

**Implementation:**
- Runtime disablement flag added: `DISCORD_ROLE_ASSIGNMENT_ENABLED`
- Event listeners check flag before processing events
- Conditional extension loading in `alttprbot_discord/bot.py`
- Commands check flag and return disabled message when `False`
- List commands work even when disabled (read-only access)

**Affected Surfaces:**
- `on_raw_reaction_add` listener
- `on_raw_reaction_remove` listener
- `on_voice_state_update` listener
- All `reactionrole` command group operations (create/update/delete/refresh)
- All `reactiongroup` command group operations (create/update/delete/refresh)

**Preserved Behavior:**
- `reactionrole list` - works even when disabled (read-only)
- `reactiongroup list` - works even when disabled (read-only)
- `importroles` - utility command, works independently of reaction-role automation

### Phase C - Data Archive & Removal ⏸️ PENDING

**Not implemented in this PR.** Scheduled for next release after communication window.

## Rollback Procedures

### Quick Rollback (Enable Features)

If role-assignment features need to be re-enabled immediately:

1. **Set flag to True** (if it was disabled):
   ```python
   # In config.py or environment
   DISCORD_ROLE_ASSIGNMENT_ENABLED = True
   ```

2. **Restart bot:**
   ```bash
   # Restart the bot service
   systemctl restart sahasrahbot  # or your deployment mechanism
   ```

3. **Verify extensions loaded:**
   - Check bot startup logs for "alttprbot_discord.cogs.role" loaded
   - Check bot startup logs for "alttprbot_discord.cogs.voicerole" loaded

### Code Rollback (Revert Changes)

If the implementation needs to be reverted:

1. **Revert to previous commit:**
   ```bash
   git revert <commit-hash>
   # or
   git checkout <previous-branch>
   ```

2. **Redeploy:**
   ```bash
   # Follow your normal deployment process
   ```

3. **Validate:**
   - Bot starts successfully
   - Commands register properly
   - Role-assignment works without warnings

## Compatibility Validation

### Bot Startup Flow ✅

**Test:** Bot starts with extensions enabled (default)
```bash
poetry run python sahasrahbot.py
# Check logs for:
# - "Loaded extension alttprbot_discord.cogs.role"
# - "Loaded extension alttprbot_discord.cogs.voicerole"
# - No errors during extension loading
```

**Test:** Bot starts with extensions disabled
```bash
# Set DISCORD_ROLE_ASSIGNMENT_ENABLED = False in config
poetry run python sahasrahbot.py
# Check logs for:
# - Extensions NOT loaded (no error, just skipped)
# - Other cogs load normally
# - Bot becomes ready
```

### Command Registration ✅

**Test:** Verify commands are registered properly
```bash
# In Discord, check that:
# - Non-role commands work normally (/generator, /tournament, etc.)
# - Role commands show deprecation warnings when used
# - No command registration errors in logs
```

### Non-Role Command Groups ✅

**Test:** Verify unaffected features work normally
- Tournament commands (`/tournament`)
- Generator commands (`/generate`, `/preset`)
- Daily challenge commands
- Racetime integration
- Async tournament workflows

**Expected Result:** All non-role features work without regression.

## Migration Guidance for Admins

### Replacement Path

SahasrahBot role-assignment automation is being retired. Guild admins should migrate to Discord's native features:

**For New Member Onboarding:**
- Use **Server Settings → Onboarding** to create role prompts
- Configure default roles for new members
- Create onboarding questions that assign roles

**For Self-Service Role Assignment:**
- Use Discord's native channel/server role settings
- Set up role-based channel access
- Use Community server features for role menus

**For Voice Channel Roles:**
- Use channel permissions and role overrides directly
- Consider Discord's Stage Channel features for speakers
- Manually assign roles as needed (fewer automation dependencies)

### Data Preservation

Before Phase C (table drops):
1. All `reaction_group` data will be exported to archive
2. All `reaction_role` data will be exported to archive
3. All `voice_role` data will be exported to archive
4. Archives stored in secure backup location
5. Archived data retained per data retention policy

Guild admins do NOT need to export data manually - this will be handled automatically.

## Communication Timeline

### Phase A (Current)
- ✅ Deprecation messaging live in commands
- ✅ Admin-facing migration guidance available
- ⏸️ Communication window open for 8 weeks (per modernization policy)

### Phase B → Phase C Transition
- ⏸️ Set `DISCORD_ROLE_ASSIGNMENT_ENABLED = False` after 8-week window
- ⏸️ Monitor for support requests
- ⏸️ Proceed to Phase C only after data gate validation

### Phase C (Future Release)
- ⏸️ Export/archive all role-assignment tables
- ⏸️ Apply migration to drop tables
- ⏸️ Remove cog files and database helper modules
- ⏸️ Remove model classes from `alttprbot/models/models.py`

## Troubleshooting

### Extensions Don't Load

**Symptom:** Bot starts but role/voicerole extensions missing  
**Cause:** Flag set to `False` or config issue  
**Resolution:** Verify `DISCORD_ROLE_ASSIGNMENT_ENABLED = True` in config

### Commands Return "Disabled" Message

**Symptom:** Commands execute but show disabled message  
**Cause:** Flag is `False` at runtime  
**Resolution:** Set flag to `True` and restart bot

### Deprecation Warnings Not Showing

**Symptom:** Commands work but no deprecation banner  
**Cause:** Code not deployed or old version running  
**Resolution:** Verify deployment, check git commit hash

## References

- [Discord Role Assignment Deprecation Plan](../plans/discord_role_assignment_deprecation_removal_plan.md)
- [Discord Role Assignment Deprecation Audit](../design/discord_role_assignment_deprecation_audit.md)
- [Application Modernization Vision 2026-2027](../plans/application_modernization_vision_2026_2027.md)
