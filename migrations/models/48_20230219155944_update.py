from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` MODIFY COLUMN `report_channel_id` BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` MODIFY COLUMN `report_channel_id` BIGINT NOT NULL;"""
