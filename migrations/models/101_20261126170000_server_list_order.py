from tortoise import BaseDBAsyncClient

# The server directory's servers get an order (`DiscordServerLists.order`), so the
# website can reorder them. Existing rows keep their id order: order starts at 0 for
# all of them, and ties are broken by id. Written by hand, like 98 to 100.


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `discord_server_lists` ADD `order` INT NOT NULL DEFAULT 0;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `discord_server_lists` DROP COLUMN `order`;"""
