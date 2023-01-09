from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ranked_choice_election` ADD `private` BOOL NOT NULL  DEFAULT 0;
        DROP TABLE IF EXISTS `twitch_channels`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ranked_choice_election` DROP COLUMN `private`;"""
