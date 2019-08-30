from ..util import orm


async def get_permissions_by_role(guild_id, role_id):
    permissions = await orm.select(
        'SELECT * from permissions WHERE guild_id=%s AND role_id=%s;',
        [guild_id, role_id]
    )
    return permissions


async def get_permission(guild_id, permission):
    permissions = await orm.select(
        'SELECT * from permissions WHERE guild_id=%s AND permission=%s;',
        [guild_id, permission]
    )
    return permissions


async def get_permissions_by_guild(guild_id):
    permissions = await orm.select(
        'SELECT * from permissions WHERE guild_id=%s;',
        [guild_id]
    )
    return permissions


async def set_permission(guild_id, role_id, permission):
    await delete_permission(guild_id, role_id, permission)
    await orm.execute(
        'INSERT INTO permissions (`guild_id`,`role_id`,`permission`) values (%s, %s, %s)',
        [guild_id, role_id, permission]
    )


async def delete_permission(guild_id, role_id, permission):
    await orm.execute(
        'DELETE FROM permissions WHERE guild_id=%s AND role_id=%s AND permission=%s',
        [guild_id, role_id, permission]
    )
