-- upgrade --
ALTER TABLE `triforcetexts` MODIFY COLUMN `discord_user_id` BIGINT;
-- downgrade --
ALTER TABLE `triforcetexts` MODIFY COLUMN `discord_user_id` BIGINT NOT NULL;
