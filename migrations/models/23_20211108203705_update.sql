-- upgrade --
ALTER TABLE `tournament_games` ADD `notes` LONGTEXT NOT NULL;
ALTER TABLE `tournament_games` ADD `preset` VARCHAR(100) NOT NULL;
-- downgrade --
ALTER TABLE `tournament_games` DROP COLUMN `notes`;
ALTER TABLE `tournament_games` DROP COLUMN `preset`;
