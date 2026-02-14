from alttprbot_discord.util.guild_config import CACHE
from alttprbot.models import Config


async def get_parameter(guild_id, parameter):
    if await CACHE.exists(f'{parameter}_{guild_id}_config'):
        results = await CACHE.get(f'{parameter}_{guild_id}_config')
        return results[0] if len(results) > 0 else None

    results = await Config.filter(
        guild_id=guild_id,
        parameter=parameter
    ).values('id', 'guild_id', 'parameter', 'value')
    await CACHE.set(f'{parameter}_{guild_id}_config', results)
    return results[0] if len(results) > 0 else None


async def get_all_parameters_by_name(parameter):
    if await CACHE.exists(f'{parameter}_allconfig'):
        results = await CACHE.get(f'{parameter}_allconfig')
        return results

    results = await Config.filter(
        parameter=parameter
    ).values('id', 'guild_id', 'parameter', 'value')
    await CACHE.set(f'{parameter}_allconfig', results)
    return results


async def get_parameters_by_guild(guild_id):
    if await CACHE.exists(f'{guild_id}_guildconfig'):
        results = await CACHE.get(f'{guild_id}_guildconfig')
        return results

    results = await Config.filter(
        guild_id=guild_id
    ).values('id', 'guild_id', 'parameter', 'value')
    await CACHE.set(f'{guild_id}_guildconfig', results)
    return results


async def set_parameter(guild_id, parameter, value):
    await delete_parameter(guild_id, parameter)
    await Config.create(guild_id=guild_id, parameter=parameter, value=value)
    await CACHE.delete(f'{parameter}_{guild_id}_config')
    await CACHE.delete(f'{parameter}_allconfig')
    await CACHE.delete(f'{guild_id}_guildconfig')


async def delete_parameter(guild_id, parameter):
    await Config.filter(guild_id=guild_id, parameter=parameter).delete()
    await CACHE.delete(f'{parameter}_{guild_id}_config')
    await CACHE.delete(f'{parameter}_allconfig')
    await CACHE.delete(f'{guild_id}_guildconfig')


async def get(guild_id, parameter, default=False):
    parameter = await get_parameter(guild_id, parameter)
    if parameter is None:
        return default

    return parameter['value']
