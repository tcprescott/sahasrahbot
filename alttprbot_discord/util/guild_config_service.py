"""
GuildConfigService - Configuration Service Pattern Implementation

This service replaces the guild monkey-patching pattern with a proper
abstraction layer for guild configuration management.

Migration Path:
    Old: await ctx.guild.config_get("Key")
    New: await config_service.get(ctx.guild.id, "Key")

Usage:
    # Initialize as a singleton or inject into cogs
    service = GuildConfigService()
    
    # Get configuration value
    value = await service.get(guild_id, "DailyAnnouncerChannel", default="")
    
    # Set configuration value
    await service.set(guild_id, "DailyAnnouncerChannel", "daily-race")
    
    # Delete configuration value
    await service.delete(guild_id, "DailyAnnouncerChannel")
    
    # List all configuration for a guild
    configs = await service.list(guild_id)

Note: This implementation maintains backward compatibility with the
existing cache strategy and database schema. The monkey-patched methods
on Guild objects remain functional for non-migrated cogs.
"""

import aiocache
import tortoise.exceptions
from typing import Any, Optional, List, Dict

from alttprbot import models


class GuildConfigService:
    """
    Service for managing guild-specific configuration.
    
    This service provides a clean abstraction over guild configuration
    storage, backed by database (via Tortoise ORM) and in-memory cache
    (via aiocache).
    """
    
    def __init__(self, cache: Optional[aiocache.Cache] = None):
        """
        Initialize the GuildConfigService.
        
        Args:
            cache: Optional aiocache.Cache instance. If not provided,
                   uses a shared SimpleMemoryCache instance.
        """
        self.cache = cache or aiocache.Cache(aiocache.SimpleMemoryCache)
    
    async def get(self, guild_id: int, parameter: str, default: Any = None) -> Any:
        """
        Get a configuration value for a guild.
        
        Args:
            guild_id: Discord guild ID
            parameter: Configuration parameter name (e.g., "DailyAnnouncerChannel")
            default: Default value to return if parameter doesn't exist
            
        Returns:
            Configuration value or default if not found
        """
        cache_key = f'{parameter}_{guild_id}_config'
        
        if await self.cache.exists(cache_key):
            return await self.cache.get(cache_key)
        
        try:
            result = await models.Config.get(guild_id=guild_id, parameter=parameter)
            await self.cache.set(cache_key, result.value)
            return result.value
        except tortoise.exceptions.DoesNotExist:
            await self.cache.set(cache_key, default)
            return default
    
    async def set(self, guild_id: int, parameter: str, value: str) -> None:
        """
        Set a configuration value for a guild.
        
        Args:
            guild_id: Discord guild ID
            parameter: Configuration parameter name
            value: Configuration value to set
        """
        await models.Config.update_or_create(
            guild_id=guild_id,
            parameter=parameter,
            defaults={'value': value}
        )
        await self.cache.delete(f'{parameter}_{guild_id}_config')
        await self.cache.delete(f'{guild_id}_guildconfig')
    
    async def delete(self, guild_id: int, parameter: str) -> None:
        """
        Delete a configuration value for a guild.
        
        Args:
            guild_id: Discord guild ID
            parameter: Configuration parameter name to delete
        """
        await models.Config.filter(guild_id=guild_id, parameter=parameter).delete()
        await self.cache.delete(f'{parameter}_{guild_id}_config')
        await self.cache.delete(f'{guild_id}_guildconfig')
    
    async def list(self, guild_id: int) -> List[Dict[str, Any]]:
        """
        List all configuration values for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            List of configuration dictionaries with keys: id, guild_id, parameter, value
        """
        cache_key = f'{guild_id}_guildconfig'
        
        if await self.cache.exists(cache_key):
            return await self.cache.get(cache_key)
        
        values = await models.Config.filter(guild_id=guild_id).values()
        await self.cache.set(cache_key, values)
        return values
    
    async def get_all_guilds_with_parameter(self, parameter: str) -> List[Dict[str, Any]]:
        """
        Get all guilds that have a specific configuration parameter.
        
        This is useful for broadcast operations like daily announcements
        where you need to notify all guilds that have opted into a feature.
        
        Args:
            parameter: Configuration parameter name to search for
            
        Returns:
            List of Config model dictionaries containing guild_id, parameter, and value
        """
        return await models.Config.filter(parameter=parameter).values()
    
    async def get_channel_ids(
        self,
        guild_id: int,
        parameter: str,
        guild: Any,
        default: str = ""
    ) -> List[int]:
        """
        Get channel IDs from configuration with backward compatibility.
        
        This helper method handles the migration from channel names to channel IDs.
        It supports both formats:
        - Legacy: comma-separated channel names (e.g., "daily-race,other-channel")
        - Modern: comma-separated channel IDs (e.g., "123456789,987654321")
        
        Args:
            guild_id: Discord guild ID
            parameter: Configuration parameter name
            guild: discord.Guild object for name->ID resolution
            default: Default value if parameter doesn't exist
            
        Returns:
            List of channel IDs (integers)
        """
        value = await self.get(guild_id, parameter, default)
        if not value:
            return []
        
        channel_ids = []
        for item in value.split(","):
            item = item.strip()
            if not item:
                continue
            
            # Try to parse as ID first
            if item.isdigit():
                channel_ids.append(int(item))
            else:
                # Fallback: resolve channel name to ID
                channel = None
                if guild and hasattr(guild, 'text_channels'):
                    import discord
                    channel = discord.utils.get(guild.text_channels, name=item)
                
                if channel:
                    channel_ids.append(channel.id)
        
        return channel_ids
