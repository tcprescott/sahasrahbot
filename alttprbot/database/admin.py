from ..util import orm

async def get_permissions_by_role(guild_id, role_id):
    permissions = await orm.select(
        'SELECT * from permissions WHERE guild_id=%s AND role_id=%s;',
        [guild_id, role_id]
    )
    return permissions

async def set_permission_by_role(guild_id, role_id, permission):
    await delete_permission(guild_id, role_id, permission)
    await orm.execute(
        'INSERT INTO permissions (`guild_id`,`role_id`,`permission`) values (%s, %s, %s)',
        [guild_id,role_id,permission]
    )

async def delete_permission(guild_id, role_id, permission):
    await orm.execute(
        'DELETE FROM permissions WHERE guild_id=%s AND role_id=%s AND permission=%s',
        [guild_id,role_id,permission]
    )



async def get_parameter(guild_id, parameter):
    permissions = await orm.select(
        'SELECT * from config WHERE guild_id=%s AND parameter=%s;',
        [guild_id, parameter]
    )
    return permissions

async def set_parameter(guild_id, parameter, value):
    await delete_parameter(guild_id, parameter, value)
    await orm.execute(
        'INSERT INTO config (`guild_id`,`parameter`,`value`) values (%s, %s, %s)',
        [guild_id,parameter,value]
    )

async def delete_parameter(guild_id, parameter, value):
    await orm.execute(
        'DELETE FROM config WHERE guild_id=%s AND role_id=%s AND permission=%s',
        [guild_id,parameter,value]
    )