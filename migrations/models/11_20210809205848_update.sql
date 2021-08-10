-- upgrade --
CREATE TABLE IF NOT EXISTS `racetimekonotgame` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `category_slug` VARCHAR(50) NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
CREATE TABLE IF NOT EXISTS `racetimekonotsegment` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `racetime_room` VARCHAR(200) NOT NULL,
    `segment_number` INT NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `game_id` INT NOT NULL,
    CONSTRAINT `fk_racetime_racetime_282bffe9` FOREIGN KEY (`game_id`) REFERENCES `racetimekonotgame` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;;
-- downgrade --
DROP TABLE IF EXISTS `racetimekonotsegment`;
DROP TABLE IF EXISTS `racetimekonotgame`;
