from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` CHANGE allowed_rerolls allowed_reattempts SMALLINT;
        CREATE TABLE IF NOT EXISTS `asynctournamentauditlog` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `discord_user_id` BIGINT,
    `action` VARCHAR(45) NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `details` LONGTEXT,
    `tournament_id` INT NOT NULL,
    CONSTRAINT `fk_asynctou_asynctou_07157358` FOREIGN KEY (`tournament_id`) REFERENCES `asynctournament` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        ALTER TABLE `asynctournamentrace` CHANGE reroll reattempted BOOL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `asynctournament` CHANGE allowed_reattempts allowed_rerolls SMALLINT;
        ALTER TABLE `asynctournamentrace` CHANGE reattempted reroll BOOL;
        DROP TABLE IF EXISTS `asynctournamentauditlog`;"""
