from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP INDEX `idx_users_twitch__3f4891`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` ADD INDEX `idx_users_twitch__3f4891` (`twitch_name`);"""
