import aiocache

from ..util import orm


@aiocache.cached(ttl=300, cache=aiocache.SimpleMemoryCache, namespace="config")
async def get_parameter(guild_id, parameter):
    result = await orm.select(
        'SELECT * from config WHERE guild_id=%s AND parameter=%s;',
        [guild_id, parameter]
    )
    if len(result) == 0:
        return None
    else:
        return result[0]


@aiocache.cached(ttl=300, cache=aiocache.SimpleMemoryCache, namespace="config")
async def get_all_parameters_by_name(parameter):
    result = await orm.select(
        'SELECT * from config WHERE parameter=%s;',
        [parameter]
    )
    return result


@aiocache.cached(ttl=300, cache=aiocache.SimpleMemoryCache, namespace="config")
async def get_parameters_by_guild(guild_id):
    result = await orm.select(
        'SELECT * from config WHERE guild_id=%s;',
        [guild_id]
    )
    return result


async def set_parameter(guild_id, parameter, value):
    await delete_parameter(guild_id, parameter)
    await orm.execute(
        'INSERT INTO config (`guild_id`,`parameter`,`value`) values (%s, %s, %s)',
        [guild_id, parameter, value]
    )
    await aiocache.SimpleMemoryCache().clear(namespace="config")


async def delete_parameter(guild_id, parameter):
    await orm.execute(
        'DELETE FROM config WHERE guild_id=%s AND parameter=%s',
        [guild_id, parameter]
    )
    await aiocache.SimpleMemoryCache().clear(namespace="config")

async def get(guild_id, parameter):
    parameter = await get_parameter(guild_id, parameter)
    if parameter is None:
        return False

    return parameter['value']