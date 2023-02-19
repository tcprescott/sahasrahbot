from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` ADD `status` VARCHAR(45) NOT NULL  DEFAULT 'pending';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` DROP COLUMN `status`;"""
