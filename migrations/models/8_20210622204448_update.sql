-- upgrade --
ALTER TABLE `tournaments` ADD `has_submission` BOOL;
-- downgrade --
ALTER TABLE `tournaments` DROP COLUMN `has_submission`;
