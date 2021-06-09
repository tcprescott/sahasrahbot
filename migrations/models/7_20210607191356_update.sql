-- upgrade --
CREATE TABLE IF NOT EXISTS `rtggwatcher` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guild_id` BIGINT NOT NULL,
    `channel_id` BIGINT NOT NULL,
    `category` VARCHAR(50) NOT NULL
) CHARACTER SET utf8mb4;;
CREATE TABLE IF NOT EXISTS `rtggwatcherplayer` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `racetime_id` VARCHAR(50) NOT NULL,
    `racetime_name` VARCHAR(200) NOT NULL,
    `rtgg_watcher_id` INT NOT NULL,
    CONSTRAINT `fk_rtggwatc_rtggwatc_1031bb95` FOREIGN KEY (`rtgg_watcher_id`) REFERENCES `rtggwatcher` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;;
-- downgrade --
DROP TABLE IF EXISTS `rtggwatcher`;
DROP TABLE IF EXISTS `rtggwatcherplayer`;
