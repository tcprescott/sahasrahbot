from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` ALTER COLUMN `score` SET DEFAULT 0;
        UPDATE `asynctournamentrace` SET `score`=0 where `score` is null;
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `score` DOUBLE NOT NULL  DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `score` DOUBLE;
        ALTER TABLE `asynctournamentrace` ALTER COLUMN `score` DROP DEFAULT;"""
