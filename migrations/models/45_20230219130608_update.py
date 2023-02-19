from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` ADD `owner_id` BIGINT NOT NULL;
        ALTER TABLE `asynctournamentrace` ADD `thread_open_time` DATETIME(6);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` DROP COLUMN `owner_id`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `thread_open_time`;"""
