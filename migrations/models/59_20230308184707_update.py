from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` ADD `user_id` INT;
        ALTER TABLE `asynctournamentrace` ADD CONSTRAINT `fk_asynctou_users_306c561f` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` DROP FOREIGN KEY `fk_asynctou_users_306c561f`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `user_id`;"""
