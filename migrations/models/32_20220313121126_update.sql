-- upgrade --
CREATE TABLE IF NOT EXISTS `tournamentpresethistory` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `preset` VARCHAR(255) NOT NULL,
    `discord_user_id` BIGINT NOT NULL,
    `episode_id` INT NOT NULL,
    `event_slug` VARCHAR(255) NOT NULL,
    `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;;
ALTER TABLE `triforcetexts` ADD `approved` BOOL NOT NULL  DEFAULT 0;
ALTER TABLE `triforcetexts` ADD `discord_user_id` BIGINT NOT NULL;
ALTER TABLE `triforcetexts` ADD `timestamp` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
ALTER TABLE `triforcetexts` DROP COLUMN `author_credit`;
-- downgrade --
ALTER TABLE `triforcetexts` ADD `author_credit` VARCHAR(200);
ALTER TABLE `triforcetexts` DROP COLUMN `approved`;
ALTER TABLE `triforcetexts` DROP COLUMN `discord_user_id`;
ALTER TABLE `triforcetexts` DROP COLUMN `timestamp`;
DROP TABLE IF EXISTS `tournamentpresethistory`;
