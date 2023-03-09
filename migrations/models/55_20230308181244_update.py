from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` ADD `reviewed_by` BIGINT;
        ALTER TABLE `asynctournamentrace` ADD `reviewed_at` DATETIME(6);
        CREATE TABLE IF NOT EXISTS `users` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `discord_user_id` BIGINT  UNIQUE,
    `twitch_name` VARCHAR(200),
    `display_name` VARCHAR(200),
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_users_twitch__3f4891` (`twitch_name`),
    KEY `idx_users_display_f54130` (`display_name`)
) CHARACTER SET utf8mb4;;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentrace` DROP COLUMN `reviewed_by`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `reviewed_at`;
        DROP TABLE IF EXISTS `users`;"""
