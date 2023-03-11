from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentpermalink` ADD `notes` VARCHAR(200);
        ALTER TABLE `asynctournamentpermalink` CHANGE permalink url VARCHAR(200);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentpermalink` CHANGE url permalink VARCHAR(200);
        ALTER TABLE `asynctournamentpermalink` DROP COLUMN `notes`;"""
