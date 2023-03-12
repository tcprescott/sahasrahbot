from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentauditlog` DROP COLUMN `discord_user_id`;
        CREATE TABLE IF NOT EXISTS `asynctournamentliverace` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `racetime_slug` VARCHAR(200)  UNIQUE,
    `episode_id` INT  UNIQUE,
    `match_title` VARCHAR(200),
    `status` VARCHAR(45) NOT NULL  DEFAULT 'scheduled',
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `permalink_id` INT,
    `pool_id` INT NOT NULL,
    `tournament_id` INT NOT NULL,
    CONSTRAINT `fk_asynctou_asynctou_b38c783e` FOREIGN KEY (`permalink_id`) REFERENCES `asynctournamentpermalink` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_asynctou_asynctou_331f22e7` FOREIGN KEY (`pool_id`) REFERENCES `asynctournamentpermalinkpool` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_asynctou_asynctou_7eb2f298` FOREIGN KEY (`tournament_id`) REFERENCES `asynctournament` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        ALTER TABLE `asynctournamentpermalink` DROP COLUMN `racetime_slug`;
        ALTER TABLE `asynctournamentpermalinkpool` ADD `preset` VARCHAR(45);
        ALTER TABLE `asynctournamentrace` ADD `live_race_id` INT;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `discord_user_id`;
        ALTER TABLE `asynctournamentrace` DROP COLUMN `racetime_slug`;
        ALTER TABLE `asynctournamentpermalinkpool` ADD UNIQUE INDEX `uid_asynctourna_tournam_f7028a` (`tournament_id`, `name`);
        ALTER TABLE `asynctournamentrace` ADD CONSTRAINT `fk_asynctou_asynctou_d1ab3397` FOREIGN KEY (`live_race_id`) REFERENCES `asynctournamentliverace` (`id`) ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournamentpermalinkpool` DROP INDEX `uid_asynctourna_tournam_f7028a`;
        ALTER TABLE `asynctournamentrace` DROP FOREIGN KEY `fk_asynctou_asynctou_d1ab3397`;
        ALTER TABLE `asynctournamentrace` ADD `discord_user_id` BIGINT;
        ALTER TABLE `asynctournamentrace` ADD `racetime_slug` VARCHAR(200);
        ALTER TABLE `asynctournamentrace` DROP COLUMN `live_race_id`;
        ALTER TABLE `asynctournamentauditlog` ADD `discord_user_id` BIGINT;
        ALTER TABLE `asynctournamentpermalink` ADD `racetime_slug` VARCHAR(200);
        ALTER TABLE `asynctournamentpermalinkpool` DROP COLUMN `preset`;
        DROP TABLE IF EXISTS `asynctournamentliverace`;"""
