from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` ALTER COLUMN `score` DROP DEFAULT;
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `score` DOUBLE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `score` DOUBLE NOT NULL  DEFAULT 0;
        ALTER TABLE `asynctournamentrace` ALTER COLUMN `score` SET DEFAULT 0;"""
