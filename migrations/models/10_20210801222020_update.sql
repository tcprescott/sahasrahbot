-- upgrade --
ALTER TABLE `tournament_results` ADD `bingosync_room` VARCHAR(200);
ALTER TABLE `tournament_results` ADD `bingosync_password` VARCHAR(40);
-- downgrade --
ALTER TABLE `tournament_results` DROP COLUMN `bingosync_room`;
ALTER TABLE `tournament_results` DROP COLUMN `bingosync_password`;
