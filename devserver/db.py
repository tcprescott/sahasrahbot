"""The dev database: a local MariaDB (see docker-compose.dev.yml).

SahasrahBot's schema and queries are MySQL-flavoured, so the dev server uses
MariaDB rather than SQLite. The schema comes from the current models
(``generate_schemas``), not from replaying ``migrations/``.
"""
import logging
import os
import urllib.parse

from tortoise import Tortoise, connections

logger = logging.getLogger("devserver.db")

DEFAULT_DB_URL = "mysql://sahasrahbot:sahasrahbot@127.0.0.1:3307/sahasrahbot_dev"


def db_url() -> str:
    return os.environ.get("DEV_DB_URL", DEFAULT_DB_URL)


def describe(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.hostname}:{parts.port}{parts.path}"


async def init():
    await Tortoise.init(
        db_url=db_url(),
        modules={"models": ["alttprbot.models"]},
        use_tz=True,
        timezone="UTC",
        _enable_global_fallback=True,
    )


async def _tables(conn):
    _, rows = await conn.execute_query("SHOW TABLES")
    return [list(r.values())[0] for r in rows]


async def reset():
    """Drop every table in the dev database."""
    conn = connections.get("default")
    tables = await _tables(conn)
    if tables:
        await conn.execute_script(
            "SET FOREIGN_KEY_CHECKS = 0;\n"
            + "".join(f"DROP TABLE IF EXISTS `{t}`;\n" for t in tables)
            + "SET FOREIGN_KEY_CHECKS = 1;"
        )
    logger.info("Dropped %d tables", len(tables))


async def prepare(reset_first: bool = False, seed: bool = True):
    from alttprbot import models
    from devserver import fixtures

    await init()
    if reset_first:
        await reset()
    await Tortoise.generate_schemas(safe=True)
    if seed and not await models.Users.exists():
        await fixtures.seed_database()
        logger.info("Seeded the dev database")
