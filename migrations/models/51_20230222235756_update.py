from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentpermalink` ADD `racetime_slug` VARCHAR(200);
        ALTER TABLE `asynctournamentpermalink` ADD `live_race` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `asynctournamentrace` ADD `racetime_slug` VARCHAR(200);
        ALTER TABLE `asynctournamentrace` ADD `thread_timeout_time` DATETIME(6);
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `thread_id` BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` DROP COLUMN `racetime_slug`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `thread_timeout_time`;
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `thread_id` BIGINT NOT NULL;
        ALTER TABLE `asynctournamentpermalink` DROP COLUMN `racetime_slug`;
        ALTER TABLE `asynctournamentpermalink` DROP COLUMN `live_race`;"""
