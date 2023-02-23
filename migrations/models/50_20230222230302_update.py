from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `asynctournamentwhitelist` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `discord_user_id` BIGINT NOT NULL,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `updated` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `tournament_id` INT NOT NULL,
    CONSTRAINT `fk_asynctou_asynctou_dbcd135c` FOREIGN KEY (`tournament_id`) REFERENCES `asynctournament` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `asynctournamentwhitelist`;"""
