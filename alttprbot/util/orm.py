import asyncio
import os

import aiomysql
from aiomysql.sa import create_engine

__pool = None


async def create_pool(loop):
    print('creating connection pool')
    global __pool
    __pool = await create_engine(
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


async def select(sql, args=[], size=None):
    global __pool
    if __pool is None:
        loop = asyncio.get_event_loop()
        await create_pool(loop)
    with (await __pool) as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                return await cur.fecthmany(size)
            else:
                return await cur.fetchall()


async def execute(sql, args=[]):
    global __pool
    if __pool is None:
        loop = asyncio.get_event_loop()
        await create_pool(loop)
    with (await __pool) as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql.replace('?', '%s'), args)
            return cur.rowcount

