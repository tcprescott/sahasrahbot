-- upgrade --
CREATE TABLE IF NOT EXISTS `authorizationkeys` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `key` VARCHAR(200) NOT NULL UNIQUE,
    `name` VARCHAR(200) NOT NULL
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `authorizationkeypermissions` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `type` VARCHAR(45) NOT NULL,
    `subtype` LONGTEXT,
    `auth_key_id` INT NOT NULL,
    CONSTRAINT `fk_authoriz_authoriz_5e8595e4` FOREIGN KEY (`auth_key_id`) REFERENCES `authorizationkeys` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;;
-- downgrade --
DROP TABLE IF EXISTS `authorizationkeypermissions`;
DROP TABLE IF EXISTS `authorizationkeys`;
