import aiocache
import tortoise.exceptions
from discord.guild import Guild

from alttprbot import models

CACHE = aiocache.Cache(aiocache.SimpleMemoryCache)

async def config_set(self, parameter, value):
    await models.Config.update_or_create(guild_id=self.id, parameter=parameter, defaults={'value': value})
    await CACHE.delete(f'{parameter}_{self.id}_config')
    await CACHE.delete(f'{self.id}_guildconfig')

async def config_get(self, parameter, default=None):
    if await CACHE.exists(f'{parameter}_{self.id}_config'):
        value = await CACHE.get(f'{parameter}_{self.id}_config')
        return value

    try:
        result = await models.Config.get(guild_id=self.id, parameter=parameter)
        await CACHE.set(f'{parameter}_{self.id}_config', result.value)
        await CACHE.delete(f'{self.id}_guildconfig')
        return result.value
    except tortoise.exceptions.DoesNotExist:
        await CACHE.set(f'{parameter}_{self.id}_config', default)
        await CACHE.delete(f'{self.id}_guildconfig')
        return default

async def config_delete(self, parameter):
    await models.Config.filter(guild_id=self.id, parameter=parameter).delete()
    await CACHE.delete(f'{parameter}_{self.id}_config')
    await CACHE.delete(f'{self.id}_guildconfig')

async def config_list(self):
    if await CACHE.exists(f'{self.id}_guildconfig'):
        values = await CACHE.get(f'{self.id}_guildconfig')
        return values

    values = await models.Config.filter(guild_id=self.id).values()
    await CACHE.set(f'{self.id}_guildconfig', values)
    return values

def init():
    Guild.config_set = config_set
    Guild.config_get = config_get
    Guild.config_delete = config_delete
    Guild.config_list = config_list
