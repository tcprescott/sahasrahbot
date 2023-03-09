from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `discord_user_id` BIGINT;
        ALTER TABLE `asynctournamentwhitelist` MODIFY COLUMN `discord_user_id` BIGINT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` MODIFY COLUMN `discord_user_id` BIGINT NOT NULL;
        ALTER TABLE `asynctournamentwhitelist` MODIFY COLUMN `discord_user_id` BIGINT NOT NULL;"""
