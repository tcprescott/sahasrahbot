-- upgrade --
CREATE TABLE IF NOT EXISTS `multiworld` (
    `message_id` BIGINT NOT NULL  PRIMARY KEY,
    `owner_id` BIGINT,
    `randomizer` VARCHAR(45),
    `preset` VARCHAR(45),
    `status` VARCHAR(20)
) CHARACTER SET utf8mb4;;
CREATE TABLE IF NOT EXISTS `multiworldentrant` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `discord_user_id` BIGINT,
    `multiworld_id` BIGINT NOT NULL,
    CONSTRAINT `fk_multiwor_multiwor_3a24fc55` FOREIGN KEY (`multiworld_id`) REFERENCES `multiworld` (`message_id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;-- downgrade --
DROP TABLE IF EXISTS `multiworld`;
DROP TABLE IF EXISTS `multiworldentrant`;
