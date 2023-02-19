from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `asynctournament` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(45) NOT NULL,
    `description` VARCHAR(2000) NOT NULL,
    `guild_id` BIGINT NOT NULL,
    `channel_id` BIGINT NOT NULL UNIQUE,
    `report_channel_id` BIGINT NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `active` BOOL NOT NULL  DEFAULT 1
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `asynctournamentpermalinkpool` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(45) NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `tournament_id` INT NOT NULL,
    CONSTRAINT `fk_asynctou_asynctou_fcfa7dda` FOREIGN KEY (`tournament_id`) REFERENCES `asynctournament` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `asynctournamentpermalink` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `permalink` VARCHAR(200) NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `pool_id` INT NOT NULL,
    CONSTRAINT `fk_asynctou_asynctou_156ebe55` FOREIGN KEY (`pool_id`) REFERENCES `asynctournamentpermalinkpool` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `asynctournamentrace` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `discord_user_id` BIGINT NOT NULL,
    `thread_id` BIGINT NOT NULL,
    `start_time` DATETIME(6),
    `end_time` DATETIME(6),
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `permalink_id` INT NOT NULL,
    `pool_id` INT NOT NULL,
    `tournament_id` INT NOT NULL,
    CONSTRAINT `fk_asynctou_asynctou_10537e98` FOREIGN KEY (`permalink_id`) REFERENCES `asynctournamentpermalink` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_asynctou_asynctou_3705b7e2` FOREIGN KEY (`pool_id`) REFERENCES `asynctournamentpermalinkpool` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_asynctou_asynctou_652b97e9` FOREIGN KEY (`tournament_id`) REFERENCES `asynctournament` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `asynctournament`;
        DROP TABLE IF EXISTS `asynctournamentpermalink`;
        DROP TABLE IF EXISTS `asynctournamentpermalinkpool`;
        DROP TABLE IF EXISTS `asynctournamentrace`;"""
