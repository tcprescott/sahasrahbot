-- upgrade --
CREATE TABLE IF NOT EXISTS `rtggannouncers` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `category` VARCHAR(50) NOT NULL,
    `guild_id` BIGINT NOT NULL,
    `channel_id` BIGINT NOT NULL
) CHARACTER SET utf8mb4;;
CREATE TABLE IF NOT EXISTS `rtggannouncermessages` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `message_id` BIGINT NOT NULL,
    `room_name` VARCHAR(50) NOT NULL,
    `announcer_id` INT NOT NULL,
    CONSTRAINT `fk_rtgganno_rtgganno_595434ba` FOREIGN KEY (`announcer_id`) REFERENCES `rtggannouncers` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;;
ALTER TABLE `rtggwatcher` ADD `notify_on_new_player` BOOL NOT NULL  DEFAULT 0;
ALTER TABLE `rtggwatcherplayer` DROP COLUMN `racetime_name`;
-- downgrade --
ALTER TABLE `rtggwatcher` DROP COLUMN `notify_on_new_player`;
ALTER TABLE `rtggwatcherplayer` ADD `racetime_name` VARCHAR(200) NOT NULL;
DROP TABLE IF EXISTS `rtggannouncermessages`;
DROP TABLE IF EXISTS `rtggannouncers`;
