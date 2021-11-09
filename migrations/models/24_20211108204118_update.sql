-- upgrade --
ALTER TABLE `tournament_games` MODIFY COLUMN `preset` VARCHAR(100);
ALTER TABLE `tournament_games` MODIFY COLUMN `notes` LONGTEXT;
-- downgrade --
ALTER TABLE `tournament_games` MODIFY COLUMN `preset` VARCHAR(100) NOT NULL;
ALTER TABLE `tournament_games` MODIFY COLUMN `notes` LONGTEXT NOT NULL;
