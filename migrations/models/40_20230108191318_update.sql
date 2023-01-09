-- upgrade --
ALTER TABLE `ranked_choice_candidate` ADD `winner` BOOL;
-- downgrade --
ALTER TABLE `ranked_choice_candidate` DROP COLUMN `winner`;
