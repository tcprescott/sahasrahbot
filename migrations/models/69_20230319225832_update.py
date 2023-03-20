from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` DROP COLUMN `score`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `score_updated_at`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` ADD `score` DOUBLE;
        ALTER TABLE `asynctournamentrace` ADD `score_updated_at` DATETIME(6);"""
