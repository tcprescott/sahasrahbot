-- upgrade --
ALTER TABLE `presets` ADD `generated_count` INT NOT NULL  DEFAULT 0;
ALTER TABLE `presets` ADD `modified` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
-- downgrade --
ALTER TABLE `presets` DROP COLUMN `generated_count`;
ALTER TABLE `presets` DROP COLUMN `modified`;
