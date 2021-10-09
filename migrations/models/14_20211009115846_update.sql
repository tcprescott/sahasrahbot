-- upgrade --
ALTER TABLE `tournament_results` MODIFY COLUMN `permalink` VARCHAR(1000);
-- downgrade --
ALTER TABLE `tournament_results` MODIFY COLUMN `permalink` VARCHAR(200);
