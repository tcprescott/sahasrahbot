from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentauditlog` ADD `user_id` INT;
        ALTER TABLE `asynctournamentwhitelist` ADD `user_id` INT NOT NULL;
        ALTER TABLE `users` CHANGE racetime_id rtgg_id VARCHAR(200);
        ALTER TABLE `asynctournamentauditlog` ADD CONSTRAINT `fk_asynctou_users_832328f7` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
        ALTER TABLE `asynctournamentwhitelist` ADD CONSTRAINT `fk_asynctou_users_7774d4d6` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentwhitelist` DROP FOREIGN KEY `fk_asynctou_users_7774d4d6`;
        ALTER TABLE `asynctournamentauditlog` DROP FOREIGN KEY `fk_asynctou_users_832328f7`;
        ALTER TABLE `users` CHANGE rtgg_id racetime_id VARCHAR(200);
        ALTER TABLE `asynctournamentauditlog` DROP COLUMN `user_id`;
        ALTER TABLE `asynctournamentwhitelist` DROP COLUMN `user_id`;"""
