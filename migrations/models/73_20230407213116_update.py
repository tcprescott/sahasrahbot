from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `asynctournamentreviewnotes` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `created` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `note` LONGTEXT NOT NULL,
    `author_id` INT NOT NULL,
    `race_id` INT NOT NULL,
    CONSTRAINT `fk_asynctou_users_4f203cf2` FOREIGN KEY (`author_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `fk_asynctou_asynctou_98fa4948` FOREIGN KEY (`race_id`) REFERENCES `asynctournamentrace` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `asynctournamentreviewnotes`;"""
