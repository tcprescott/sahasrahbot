-- upgrade --
ALTER TABLE `ranked_choice_election` ADD `results` LONGTEXT;
-- downgrade --
ALTER TABLE `ranked_choice_election` DROP COLUMN `results`;
