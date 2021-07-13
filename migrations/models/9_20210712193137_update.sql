-- upgrade --
ALTER TABLE `tournaments` ADD `coop` BOOL;
-- downgrade --
ALTER TABLE `tournaments` DROP COLUMN `coop`;
