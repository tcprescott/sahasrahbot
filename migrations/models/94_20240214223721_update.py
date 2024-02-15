from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `scheduleepisodecommentatorpreferredpartner` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `episode_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    CONSTRAINT `fk_schedule_schedule_ed6a869b` FOREIGN KEY (`episode_id`) REFERENCES `scheduleepisode` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_schedule_users_65c209a0` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `scheduleepisodecommentatorpreferredpartner`;"""
