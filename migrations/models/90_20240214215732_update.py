from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `scheduleepisode_schedulebroadcastchannels`;
        ALTER TABLE `scheduleepisode` ADD `approved` BOOL NOT NULL  DEFAULT 0;
        ALTER TABLE `scheduleepisode` ADD `approved_at` DATETIME(6);
        ALTER TABLE `scheduleepisode` ADD `approved_by_id` INT;
        ALTER TABLE `scheduleepisode` ADD `channel_id` INT;
        ALTER TABLE `scheduleepisodecommentator` ADD `approved_at` DATETIME(6);
        ALTER TABLE `scheduleepisodecommentator` ADD `approved_by_id` INT;
        ALTER TABLE `scheduleepisoderestreamer` ADD `approved_at` DATETIME(6);
        ALTER TABLE `scheduleepisoderestreamer` ADD `approved_by_id` INT;
        ALTER TABLE `scheduleepisodetracker` ADD `approved_at` DATETIME(6);
        ALTER TABLE `scheduleepisodetracker` ADD `approved_by_id` INT;
        ALTER TABLE `scheduleepisode` ADD CONSTRAINT `fk_schedule_schedule_d1480866` FOREIGN KEY (`channel_id`) REFERENCES `schedulebroadcastchannels` (`id`) ON DELETE CASCADE;
        ALTER TABLE `scheduleepisode` ADD CONSTRAINT `fk_schedule_users_d8e820d4` FOREIGN KEY (`approved_by_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT;
        ALTER TABLE `scheduleepisodecommentator` ADD CONSTRAINT `fk_schedule_users_117371e6` FOREIGN KEY (`approved_by_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT;
        ALTER TABLE `scheduleepisoderestreamer` ADD CONSTRAINT `fk_schedule_users_bb286c2c` FOREIGN KEY (`approved_by_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT;
        ALTER TABLE `scheduleepisodetracker` ADD CONSTRAINT `fk_schedule_users_3d3b9c8a` FOREIGN KEY (`approved_by_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `scheduleepisodecommentator` DROP FOREIGN KEY `fk_schedule_users_117371e6`;
        ALTER TABLE `scheduleepisoderestreamer` DROP FOREIGN KEY `fk_schedule_users_bb286c2c`;
        ALTER TABLE `scheduleepisodetracker` DROP FOREIGN KEY `fk_schedule_users_3d3b9c8a`;
        ALTER TABLE `scheduleepisode` DROP FOREIGN KEY `fk_schedule_users_d8e820d4`;
        ALTER TABLE `scheduleepisode` DROP FOREIGN KEY `fk_schedule_schedule_d1480866`;
        ALTER TABLE `scheduleepisode` DROP COLUMN `approved`;
        ALTER TABLE `scheduleepisode` DROP COLUMN `approved_at`;
        ALTER TABLE `scheduleepisode` DROP COLUMN `approved_by_id`;
        ALTER TABLE `scheduleepisode` DROP COLUMN `channel_id`;
        ALTER TABLE `scheduleepisodetracker` DROP COLUMN `approved_at`;
        ALTER TABLE `scheduleepisodetracker` DROP COLUMN `approved_by_id`;
        ALTER TABLE `scheduleepisoderestreamer` DROP COLUMN `approved_at`;
        ALTER TABLE `scheduleepisoderestreamer` DROP COLUMN `approved_by_id`;
        ALTER TABLE `scheduleepisodecommentator` DROP COLUMN `approved_at`;
        ALTER TABLE `scheduleepisodecommentator` DROP COLUMN `approved_by_id`;
        CREATE TABLE `scheduleepisode_schedulebroadcastchannels` (
    `scheduleepisode_id` INT NOT NULL REFERENCES `scheduleepisode` (`id`) ON DELETE CASCADE,
    `schedulebroadcastchannels_id` INT NOT NULL REFERENCES `schedulebroadcastchannels` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""
