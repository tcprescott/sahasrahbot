-- upgrade --
ALTER TABLE `presets` DROP INDEX `uid_presets_preset__289d46`;
ALTER TABLE `presets` ADD `randomizer` VARCHAR(50) NOT NULL;
ALTER TABLE `presets` ADD UNIQUE INDEX `uid_presets_randomi_02e1e0` (`randomizer`, `preset_name`, `namespace_id`);
-- downgrade --
ALTER TABLE `presets` DROP INDEX `uid_presets_randomi_02e1e0`;
ALTER TABLE `presets` DROP COLUMN `randomizer`;
ALTER TABLE `presets` ADD UNIQUE INDEX `uid_presets_preset__289d46` (`preset_name`, `namespace_id`);
