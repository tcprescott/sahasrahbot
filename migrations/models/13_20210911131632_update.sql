-- upgrade --
CREATE TABLE IF NOT EXISTS `triforcetexts` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `pool_name` VARCHAR(45) NOT NULL,
    `text` VARCHAR(200) NOT NULL,
    `author` VARCHAR(200),
    `author_credit` VARCHAR(200),
    `broadcasted` BOOL NOT NULL  DEFAULT 0
) CHARACTER SET utf8mb4;
-- downgrade --
DROP TABLE IF EXISTS `triforcetexts`;
