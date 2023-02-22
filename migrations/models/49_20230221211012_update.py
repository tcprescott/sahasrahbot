from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `presetnamespacecollaborators` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `discord_user_id` BIGINT NOT NULL,
    `namespace_id` INT NOT NULL,
    UNIQUE KEY `uid_presetnames_namespa_3c3b20` (`namespace_id`, `discord_user_id`),
    CONSTRAINT `fk_presetna_presetna_3df99947` FOREIGN KEY (`namespace_id`) REFERENCES `presetnamespaces` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `presetnamespacecollaborators`;"""
