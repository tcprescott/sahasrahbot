from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `racerverification` ADD `reverify_period_days` INT;
        ALTER TABLE `racerverification` ADD `channel_id` BIGINT;
        ALTER TABLE `racerverification` ADD `audit_channel_id` BIGINT;
        ALTER TABLE `racerverification` ADD `revoke_ineligible` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `racerverification` ADD `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        CREATE TABLE IF NOT EXISTS `verifiedracer` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `estimated_count` INT,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `last_verified` DATETIME(6),
    `racer_verification_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_verified_racerver_82fe307a` FOREIGN KEY (`racer_verification_id`) REFERENCES `racerverification` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_verified_users_ea937e10` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `racerverification` DROP COLUMN `reverify_period_days`;
        ALTER TABLE `racerverification` DROP COLUMN `channel_id`;
        ALTER TABLE `racerverification` DROP COLUMN `audit_channel_id`;
        ALTER TABLE `racerverification` DROP COLUMN `revoke_ineligible`;
        ALTER TABLE `racerverification` DROP COLUMN `updated`;
        DROP TABLE IF EXISTS `verifiedracer`;"""
