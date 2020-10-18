import asyncio
import os

import aiomysql

__pool = None


async def create_pool(loop):
    print('creating connection pool')
    global __pool
    __pool = await aiomysql.create_pool(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "user"),
        db=os.environ.get("DB_NAME", "sahasrahbot"),
        password=os.environ.get("DB_PASS", "pass"),
        program_name='alttprbot',
        charset='utf8mb4',
        autocommit=True,
        maxsize=10,
        minsize=1,
        loop=loop
    )


async def select(sql, args=None, size=None):
    global __pool
    if __pool is None:
        loop = asyncio.get_event_loop()
        await create_pool(loop)

    if args is None:
        args = []

    with (await __pool) as conn:
        cur = await conn.cursor(aiomysql.DictCursor)
        await cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = await cur.fecthmany(size)
        else:
            rs = await cur.fetchall()
        await cur.close()
        return rs


async def execute(sql, args=None):
    global __pool
    if __pool is None:
        loop = asyncio.get_event_loop()
        await create_pool(loop)

    if args is None:
        args = []

    with (await __pool) as conn:
        try:
            cur = await conn.cursor()
            await cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            await cur.close()
        except BaseException:
            raise
        return affected
