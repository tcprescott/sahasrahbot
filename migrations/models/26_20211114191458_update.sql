-- upgrade --
ALTER TABLE `srlnick` DROP COLUMN `srl_nick`;
ALTER TABLE `srlnick` DROP COLUMN `srl_verified`;
ALTER TABLE `srlnick` MODIFY COLUMN `twitch_name` VARCHAR(200);
ALTER TABLE `srlnick` MODIFY COLUMN `rtgg_id` VARCHAR(200);
-- downgrade --
ALTER TABLE `srlnick` ADD `srl_nick` VARCHAR(200) NOT NULL;
ALTER TABLE `srlnick` ADD `srl_verified` SMALLINT;
ALTER TABLE `srlnick` MODIFY COLUMN `twitch_name` VARCHAR(200) NOT NULL;
ALTER TABLE `srlnick` MODIFY COLUMN `rtgg_id` VARCHAR(200) NOT NULL;
