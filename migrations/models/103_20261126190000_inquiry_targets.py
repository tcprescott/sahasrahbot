from tortoise import BaseDBAsyncClient

# Inquiry buttons remember their server, channel and when they were posted, so the
# website's Servers area can list them. Older rows keep NULLs (and keep working).
# Written by hand like 98-100. 101 (role menus) and 102 (server directory) are in
# their own PRs.


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `inquirymessageconfig` ADD `guild_id` BIGINT;
        ALTER TABLE `inquirymessageconfig` ADD `channel_id` BIGINT;
        ALTER TABLE `inquirymessageconfig` ADD `created` DATETIME(6);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `inquirymessageconfig` DROP COLUMN `created`;
        ALTER TABLE `inquirymessageconfig` DROP COLUMN `channel_id`;
        ALTER TABLE `inquirymessageconfig` DROP COLUMN `guild_id`;"""
