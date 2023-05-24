from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` ADD `customization` VARCHAR(45) NOT NULL  DEFAULT 'default';
        ALTER TABLE `asynctournamentrace` ADD `run_collection_rate` VARCHAR(100);
        ALTER TABLE `asynctournamentrace` ADD `run_igt` VARCHAR(100);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` DROP COLUMN `customization`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `run_collection_rate`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `run_igt`;"""
