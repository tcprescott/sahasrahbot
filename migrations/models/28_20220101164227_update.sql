-- upgrade --
ALTER TABLE `audit_generated_games` ADD `doors` BOOL NOT NULL  DEFAULT 0;
-- downgrade --
ALTER TABLE `audit_generated_games` DROP COLUMN `doors`;
