-- upgrade --
CREATE TABLE IF NOT EXISTS `presetnamespaces` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `namespace` VARCHAR(50) NOT NULL,
    `discord_user_id` BIGINT NOT NULL
) CHARACTER SET utf8mb4;;
CREATE TABLE IF NOT EXISTS `presets` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `preset_name` VARCHAR(50) NOT NULL,
    `content` LONGTEXT NOT NULL,
    `namespace_id` INT NOT NULL,
    CONSTRAINT `fk_presets_presetna_5e0ca128` FOREIGN KEY (`namespace_id`) REFERENCES `presetnamespaces` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;-- downgrade --
DROP TABLE IF EXISTS `presetnamespaces`;
DROP TABLE IF EXISTS `presets`;
