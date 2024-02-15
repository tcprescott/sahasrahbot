from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `scheduleaudit` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `action` LONGTEXT NOT NULL,
    `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `episode_id` INT,
    `event_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_schedule_schedule_5ae919b2` FOREIGN KEY (`episode_id`) REFERENCES `scheduleepisode` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_schedule_schedule_ff8dd064` FOREIGN KEY (`event_id`) REFERENCES `scheduleevent` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_schedule_users_fe8e7d0f` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `schedulebroadcastchannels` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `channel_type` VARCHAR(200) NOT NULL  DEFAULT 'twitch',
    `channel_name` VARCHAR(200) NOT NULL,
    `display_name` VARCHAR(200) NOT NULL,
    `event_id` INT NOT NULL,
    CONSTRAINT `fk_schedule_schedule_b11b2a07` FOREIGN KEY (`event_id`) REFERENCES `scheduleevent` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE `scheduleepisode_schedulebroadcastchannels` (
    `scheduleepisode_id` INT NOT NULL REFERENCES `scheduleepisode` (`id`) ON DELETE CASCADE,
    `schedulebroadcastchannels_id` INT NOT NULL REFERENCES `schedulebroadcastchannels` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `scheduleepisode_schedulebroadcastchannels`;
        DROP TABLE IF EXISTS `scheduleaudit`;
        DROP TABLE IF EXISTS `schedulebroadcastchannels`;"""
