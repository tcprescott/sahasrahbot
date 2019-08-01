from ..util import orm

async def get_seed_preset(name):
    result = await orm.select(
        'SELECT * FROM seed_presets WHERE name=%s;',
        [name]
    )
    return result[0]

# async def set_new_daily(hash):
#     await orm.execute(
#         'INSERT INTO daily (`hash`) values (%s)',
#         [hash]
#     )