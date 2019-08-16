from ..util import orm

async def get_seed_preset(name):
    result = await orm.select(
        'SELECT * FROM seed_presets WHERE name=%s;',
        [name]
    )
    return result[0]

async def put_seed_preset(name, randomizer, settings):
    await orm.execute(
        'INSERT INTO seed_presets (`name`,`randomizer`,`settings`) values (%s, %s, %s) ON DUPLICATE KEY UPDATE settings = %s',
        [name, randomizer, settings, settings]
    )

# async def set_new_daily(hash):
#     await orm.execute(
#         'INSERT INTO daily (`hash`) values (%s)',
#         [hash]
#     )