-- upgrade --
ALTER TABLE `presetnamespaces` ADD UNIQUE INDEX `uid_presetnames_discord_601a6a` (`discord_user_id`);
ALTER TABLE `presetnamespaces` ADD UNIQUE INDEX `uid_presetnames_name_46f871` (`name`);
ALTER TABLE `presets` ADD UNIQUE INDEX `uid_presets_preset__289d46` (`preset_name`, `namespace_id`);
-- downgrade --
ALTER TABLE `presetnamespaces` DROP INDEX `idx_presetnames_name_46f871`;
ALTER TABLE `presetnamespaces` DROP INDEX `idx_presetnames_discord_601a6a`;
ALTER TABLE `presets` DROP INDEX `uid_presets_preset__289d46`;
