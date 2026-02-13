# GuildConfigService Migration Notes

> **Status:** In Progress (Pilot Phase)
> **Last updated:** 2026-02-12
> **Related:** [discord_refactor.md](discord_refactor.md)

## Overview

This document tracks the migration from the monkey-patched `Guild.config_*` methods to the new `GuildConfigService` abstraction layer.

## Migration Status

### ✅ Completed
- **GuildConfigService implementation** (`alttprbot_discord/util/guild_config_service.py`)
  - Core service class with `get()`, `set()`, `delete()`, `list()` methods
  - Backward-compatible cache behavior
  - Helper method `get_channel_ids()` for channel name→ID migration
  
- **Daily Cog Migration** (`alttprbot_discord/cogs/daily.py`)
  - Pilot consumer using GuildConfigService
  - Enhanced error handling for missing channels/permissions
  - Backward compatibility for name-based channel config
  - Improved resilience with null checks

### 🔄 In Progress
- None

### ⏳ Pending
- Migration of remaining cogs:
  - `alttprbot_discord/cogs/tournament.py` (uses `TournamentEnabled`)
  - `alttprbot_discord/cogs/misc.py` (uses `HolyImageDefaultGame`)
  - `alttprbot_audit/cogs/audit.py` (uses `AuditLogChannel`, `AuditLogging`)
- Removal of monkey-patch initialization in `alttprbot_discord/bot.py`
- Channel name→ID data migration script
- Validation tooling for channel ID configs

## API Migration Guide

### For Cog Developers

#### Before (Monkey-patched)
```python
class MyCog(commands.Cog):
    async def some_command(self, ctx):
        value = await ctx.guild.config_get("ParameterName", "default")
        await ctx.guild.config_set("ParameterName", "new_value")
        await ctx.guild.config_delete("ParameterName")
        all_configs = await ctx.guild.config_list()
```

#### After (GuildConfigService)
```python
from alttprbot_discord.util.guild_config_service import GuildConfigService

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_service = GuildConfigService()
    
    async def some_command(self, ctx):
        value = await self.config_service.get(ctx.guild.id, "ParameterName", "default")
        await self.config_service.set(ctx.guild.id, "ParameterName", "new_value")
        await self.config_service.delete(ctx.guild.id, "ParameterName")
        all_configs = await self.config_service.list(ctx.guild.id)
```

### Channel Configuration Migration

For channel-based configuration parameters, use the `get_channel_ids()` helper:

#### Before (Name-based lookup)
```python
channel_names = config_value.split(",")
for name in channel_names:
    channel = discord.utils.get(guild.text_channels, name=name)
    await channel.send("message")
```

#### After (ID-based with backward compatibility)
```python
channel_ids = await self.config_service.get_channel_ids(
    guild.id,
    "ConfigParameter",
    guild
)
for channel_id in channel_ids:
    channel = guild.get_channel(channel_id)
    if channel and isinstance(channel, discord.TextChannel):
        await channel.send("message")
```

## Backward Compatibility

The monkey-patched methods on `discord.Guild` objects remain functional during the migration period. Both APIs can coexist:

- Old code continues to use `guild.config_get()` / `guild.config_set()`
- New code uses `GuildConfigService().get()` / `GuildConfigService().set()`
- Both access the same database and cache backend

**Important:** Do not remove the monkey-patch initialization (`guild_config.init()` in `alttprbot_discord/bot.py`) until all cogs are migrated.

## Channel Name→ID Migration Strategy

### Non-Destructive Groundwork
1. **Dual-format support**: The `get_channel_ids()` helper accepts both:
   - Legacy format: `"channel-name,other-channel"`
   - Modern format: `"123456789012345678,987654321098765432"`

2. **Automatic detection**: Uses `str.isdigit()` to distinguish IDs from names

3. **Fallback resolution**: If a name is detected, resolves it to ID using `discord.utils.get()`

### Future Migration Script (Phase 2)
When ready to migrate data:

1. **Audit Phase**:
   - Scan all `Config` records for parameters ending in `Channel`
   - Identify which values contain names vs. IDs
   - Generate migration report

2. **Migration Phase**:
   - For each name-based config:
     - Fetch the guild from Discord
     - Resolve channel names to IDs
     - Update database with ID values
     - Log all changes

3. **Validation Phase**:
   - Verify all channel configs are numeric
   - Test that channels are still accessible
   - Add validation to config setters

## Testing Checklist

- [ ] Daily announcements continue to work with existing name-based configs
- [ ] Daily announcements work with new ID-based configs
- [ ] Error handling gracefully handles missing channels
- [ ] Error handling gracefully handles permission issues
- [ ] Cache invalidation works correctly
- [ ] Multiple channels per guild work correctly
- [ ] Guild lookup failures don't crash the task

## Rollback Plan

If issues arise during migration:

1. **Isolated Failure**: If only the new service has issues, revert the migrated cog to use monkey-patched methods
2. **Service-wide Failure**: The monkey-patch path remains untouched, so non-migrated functionality is unaffected
3. **Data Corruption**: No data migration occurs in this phase, so rollback is code-only

## Next Steps

1. Monitor daily announcements in production for 1-2 weeks
2. Gather feedback on service API ergonomics
3. Migrate next cog (recommend: `misc.py` for lower stakes)
4. Continue incremental migration until all consumers are converted
5. Develop and test channel name→ID migration script
6. Execute data migration in maintenance window
7. Remove monkey-patch initialization
8. Add validation to prevent storing channel names

## References

- [discord_refactor.md](discord_refactor.md) - Parent refactor plan
- [system_patterns.md](../context/system_patterns.md) - Architecture patterns
- [coding_standards.md](../context/coding_standards.md) - Coding conventions
