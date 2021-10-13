-- upgrade --
CREATE TABLE IF NOT EXISTS `rtggunlistedrooms` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `room_name` VARCHAR(200) NOT NULL,
    `category` VARCHAR(50) NOT NULL
) CHARACTER SET utf8mb4;
-- downgrade --
DROP TABLE IF EXISTS `rtggunlistedrooms`;
