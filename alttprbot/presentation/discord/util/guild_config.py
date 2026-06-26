"""Legacy ``Guild.config_*`` monkey-patch — now a thin shim over GuildConfigService.

The four methods are still attached to ``discord.Guild`` for the many existing
callers, but all storage now flows through the canonical GuildConfigService
(Tier 2) + GuildConfigRepository (Tier 3). Slated for removal once the remaining
callers (audit/misc/tournament) call the service directly (Phase 10).

``CACHE`` is re-exported as the service's shared cache so the legacy
``alttprbot.database.config`` module stays cache-coherent with the service.
"""

from discord.guild import Guild

from alttprbot.services import GuildConfigService
from alttprbot.services.guild_config_service import GUILD_CONFIG_CACHE

CACHE = GUILD_CONFIG_CACHE


async def config_set(self, parameter, value):
    await GuildConfigService().set(self.id, parameter, value)


async def config_get(self, parameter, default=None):
    return await GuildConfigService().get(self.id, parameter, default)


async def config_delete(self, parameter):
    await GuildConfigService().delete(self.id, parameter)


async def config_list(self):
    return await GuildConfigService().list(self.id)


def init():
    Guild.config_set = config_set
    Guild.config_get = config_get
    Guild.config_delete = config_delete
    Guild.config_list = config_list
