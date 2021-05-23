import asyncio
from tortoise import Tortoise
from tortoise.utils import get_schema_sql
import os
import urllib.parse
from dotenv import load_dotenv
from alttprbot.models import Tournaments

load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_NAME = os.environ.get("DB_NAME", "sahasrahbot")
DB_USER = os.environ.get("DB_USER", "user")
DB_PASS = urllib.parse.quote_plus(os.environ.get("DB_PASS", "pass"))

async def init():
    await Tortoise.init(
        db_url=f'mysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}',
        modules={'models': ['alttprbot.models']}
    )
    sql = get_schema_sql(Tortoise.get_connection("default"), safe=False)
    print(sql)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(init())
    loop.run_forever()