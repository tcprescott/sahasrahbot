from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `scheduleepisode` DROP COLUMN `episode_number`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `scheduleepisode` ADD `episode_number` INT NOT NULL;"""
