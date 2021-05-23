-- upgrade --
ALTER TABLE `daily` ADD INDEX `idx_daily_hash_f4a034` (`hash`);
ALTER TABLE `daily` MODIFY COLUMN `hash` VARCHAR(45) NOT NULL;
-- downgrade --
ALTER TABLE `daily` MODIFY COLUMN `hash` VARCHAR(45);
ALTER TABLE `daily` DROP INDEX `idx_daily_hash_f4a034`;