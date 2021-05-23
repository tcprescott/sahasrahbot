-- upgrade --
ALTER TABLE `audit_messages` MODIFY COLUMN `attachment` VARCHAR(1000);
-- downgrade --
ALTER TABLE `audit_messages` MODIFY COLUMN `attachment` VARCHAR(2000);
