from tortoise import Tortoise


async def select(sql, args=None):
    conn = Tortoise.get_connection("default")
    val = await conn.execute_query_dict(sql, args)
    return val


async def execute(sql, args=None):
    conn = Tortoise.get_connection("default")
    await conn.execute_query(sql, args)
