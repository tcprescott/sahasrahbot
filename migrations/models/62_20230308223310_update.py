from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` ADD `reviewed_by_id` INT;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `reviewed_by`;
        ALTER TABLE `asynctournamentrace` ADD CONSTRAINT `fk_asynctou_users_2566e29f` FOREIGN KEY (`reviewed_by_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` DROP FOREIGN KEY `fk_asynctou_users_2566e29f`;
        ALTER TABLE `asynctournamentrace` ADD `reviewed_by` BIGINT;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `reviewed_by_id`;"""
