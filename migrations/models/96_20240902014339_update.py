from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` ADD `runs_per_pool` SMALLINT NOT NULL  DEFAULT 1;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` DROP COLUMN `runs_per_pool`;"""
